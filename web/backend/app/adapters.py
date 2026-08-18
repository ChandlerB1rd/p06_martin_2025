"""Reshape the pipeline's wide artifacts into the row-per-(date, horizon) frames
the Monitor renders.

`svix_daily.parquet` stores one row per date with a column block per horizon
(`svix2_total_1m`, `svix_1m`, ...) and carries no risk-free rate, so the gross
rate is joined in from `future_sp500_returns.parquet`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.deps import (
    ANNUALIZATION_FACTOR,
    HORIZON_DAYS,
    HORIZON_MONTHS,
    HORIZONS,
    load_future_returns,
    load_published_comparison,
    load_svix_daily_wide,
    load_table1_csv,
)

# Sample name in the pipeline CSVs -> the label shown on the Table 1 toggle.
TABLE1_SOURCES = (
    ("table1_replication.csv", "January 1996-December 2022", "Full paper sample"),
    (
        "table1_replication.csv",
        "February 2012-December 2022",
        "Recent paper subsample",
    ),
    ("table1_updated.csv", "January 1996-latest usable", "Full sample to present"),
    (
        "table1_post2022.csv",
        "January 2023-latest usable",
        "Post-2022 out-of-sample",
    ),
)

# Published Martin (2025) values only exist for the two paper samples, and
# table1_published_comparison.csv suffixes them by sample window.
_PUBLISHED_SUFFIX = {
    "January 1996-December 2022": "1996_2022",
    "February 2012-December 2022": "2012_2022",
}


def svix_daily_long() -> pd.DataFrame:
    """Melt wide constant-maturity SVIX into (date, horizon_m) rows.

    Annualization follows the pipeline's own `ANNUALIZATION_FACTOR` (12/4/2/1)
    rather than 365/target_days, so the hero print stays consistent with the
    Table 1 regressions, which use that same factor on both sides.
    """
    wide = load_svix_daily_wide()
    rates = load_future_returns()
    rate_cols = [f"rf_gross_{h}" for h in HORIZONS if f"rf_gross_{h}" in rates.columns]
    rf = rates[["date", *rate_cols]]
    wide = wide.merge(rf, on="date", how="left")

    frames = []
    for label in HORIZONS:
        months = HORIZON_MONTHS[label]
        factor = ANNUALIZATION_FACTOR[label]
        target_days = float(HORIZON_DAYS[label])
        svix2 = wide[f"svix2_total_{label}"].astype(float)
        gross_rf = (
            wide[f"rf_gross_{label}"].astype(float)
            if f"rf_gross_{label}" in wide.columns
            else pd.Series(np.nan, index=wide.index)
        )
        frames.append(
            pd.DataFrame(
                {
                    "date": wide["date"],
                    "horizon_m": months,
                    "target_days": wide.get(f"target_days_{label}", target_days),
                    "svix2": svix2,
                    "svix": np.sqrt(svix2),
                    "Rf": gross_rf,
                    "tau": target_days / 365.0,
                    # Martin (2025): E_t R - R_f = R_f * SVIX^2, annualized.
                    "ep_ann": gross_rf * svix2 * factor,
                    # svix_{label} is already the annualized SVIX volatility.
                    "ann_vol": wide[f"svix_{label}"].astype(float) * 100.0,
                    "extrapolated": wide[f"extrapolated_{label}"],
                }
            )
        )

    out = pd.concat(frames, ignore_index=True)
    return out.sort_values(["date", "horizon_m"]).reset_index(drop=True)


def _published_for(sample: str, horizon_label: str) -> dict[str, float | None]:
    suffix = _PUBLISHED_SUFFIX.get(sample)
    if suffix is None:
        return {"pub_alpha": None, "pub_beta": None, "pub_r2": None}
    pub = load_published_comparison()
    row = pub.loc[pub["horizon"] == horizon_label]
    if row.empty:
        return {"pub_alpha": None, "pub_beta": None, "pub_r2": None}
    r = row.iloc[0]

    def get(metric: str, scale: float = 1.0) -> float | None:
        col = f"{metric}_pub_{suffix}"
        if col not in row.columns or pd.isna(r[col]):
            return None
        return float(r[col]) * scale

    return {
        "pub_alpha": get("alpha"),
        "pub_beta": get("beta"),
        "pub_r2": get("r2", 100.0),
    }


def _num(value, scale: float = 1.0) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value) * scale


def table1_rows() -> tuple[list[dict], list[str], dict[str, str]]:
    """Normalize the pipeline's Table 1 CSVs into one list of API rows."""
    rows: list[dict] = []
    samples: list[str] = []
    labels: dict[str, str] = {}

    for filename, sample, label in TABLE1_SOURCES:
        df = load_table1_csv(filename)
        subset = df.loc[df["sample"] == sample]
        if subset.empty:
            continue
        samples.append(sample)
        labels[sample] = label
        for r in subset.itertuples(index=False):
            horizon_label = str(r.horizon)
            months = HORIZON_MONTHS.get(horizon_label)
            if months is None:
                continue
            rows.append(
                {
                    "sample": sample,
                    "horizon_m": months,
                    "start": str(pd.Timestamp(r.start).date()),
                    "end": str(pd.Timestamp(r.last_usable_date).date())
                    if pd.notna(r.last_usable_date)
                    else "",
                    "alpha": _num(r.alpha),
                    "alpha_se": _num(r.alpha_se_nw),
                    "beta": _num(r.beta),
                    "beta_se": _num(r.beta_se_nw),
                    "beta_t": _num(r.beta_t_nw),
                    "r2_pct": _num(r.r2, 100.0),
                    "nobs": int(r.nobs),
                    **_published_for(sample, horizon_label),
                }
            )

    return rows, samples, labels
