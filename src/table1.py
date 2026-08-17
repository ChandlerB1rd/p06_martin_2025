"""Replicate and update Martin (2025) Table 1 forecasting regressions."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

from build_future_returns import load_future_returns
from martin_spec import (
    HORIZON_DAYS,
    HORIZONS,
    NW_LAGS,
    ORIGINAL_SAMPLE_END,
    ORIGINAL_SAMPLE_START,
    POST_2022_START,
    RECENT_SAMPLE_START,
)
from settings import config
from svix import load_svix_daily

DATA_DIR = Path(config("DATA_DIR"))
OUTPUT_DIR = Path(config("OUTPUT_DIR"))

OUT = OUTPUT_DIR / "table1_replication.csv"
COMPARISON_OUT = OUTPUT_DIR / "table1_published_comparison.csv"
UPDATED_OUT = OUTPUT_DIR / "table1_updated.csv"
POST_2022_OUT = OUTPUT_DIR / "table1_post2022.csv"

PUBLISHED = pd.DataFrame(
    {
        "horizon": list(HORIZONS),
        "alpha_1996_2022": [0.014, 0.015, -0.025, 0.003],
        "alpha_se_1996_2022": [0.041, 0.051, 0.037, 0.043],
        "beta_1996_2022": [1.569, 1.439, 2.418, 1.858],
        "beta_se_1996_2022": [1.024, 1.269, 0.806, 0.824],
        "r2_1996_2022": [0.01302, 0.02201, 0.06840, 0.04727],
        "alpha_2012_2022": [-0.015, -0.008, 0.011, 0.008],
        "alpha_se_2012_2022": [0.035, 0.041, 0.053, 0.070],
        "beta_2012_2022": [4.280, 3.620, 3.007, 3.188],
        "beta_se_2012_2022": [0.822, 0.997, 1.633, 2.368],
        "r2_2012_2022": [0.07809, 0.12334, 0.11454, 0.11316],
    }
)


def load_table1_data() -> pd.DataFrame:
    ret = load_future_returns()
    svix = load_svix_daily()
    ret["date"] = pd.to_datetime(ret["date"])
    svix["date"] = pd.to_datetime(svix["date"])
    return ret.merge(svix, on="date", how="inner", validate="one_to_one")


def run_regression(
    df: pd.DataFrame,
    horizon: str,
    start: str | pd.Timestamp,
    end: str | pd.Timestamp | None,
    sample_name: str,
    require_full_hac: bool = True,
) -> dict[str, object]:
    """Run the paper regression with horizon-specific Newey-West SEs."""
    y = f"excess_fwd_{horizon}"
    x = f"svix2_{horizon}"
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end) if end is not None else df["date"].max()
    sample = df.loc[df["date"].between(start_ts, end_ts), ["date", y, x]].dropna()

    min_obs = NW_LAGS[horizon] + 5 if require_full_hac else 10
    if len(sample) <= min_obs:
        return {
            "sample": sample_name,
            "horizon": horizon,
            "start": start_ts,
            "end_requested": end_ts,
            "last_usable_date": sample["date"].max() if len(sample) else pd.NaT,
            "nobs": len(sample),
            "alpha": np.nan,
            "alpha_se_nw": np.nan,
            "alpha_t_nw": np.nan,
            "beta": np.nan,
            "beta_se_nw": np.nan,
            "beta_t_nw": np.nan,
            "r2": np.nan,
            "nw_lags": NW_LAGS[horizon],
        }

    X = sm.add_constant(sample[x], has_constant="add")
    maxlags = min(NW_LAGS[horizon], len(sample) - 2)
    fit = sm.OLS(sample[y], X).fit(
        cov_type="HAC", cov_kwds={"maxlags": maxlags}
    )
    return {
        "sample": sample_name,
        "horizon": horizon,
        "start": start_ts,
        "end_requested": end_ts,
        "last_usable_date": sample["date"].max(),
        "nobs": int(fit.nobs),
        "alpha": float(fit.params["const"]),
        "alpha_se_nw": float(fit.bse["const"]),
        "alpha_t_nw": float(fit.tvalues["const"]),
        "beta": float(fit.params[x]),
        "beta_se_nw": float(fit.bse[x]),
        "beta_t_nw": float(fit.tvalues[x]),
        "r2": float(fit.rsquared),
        "nw_lags": maxlags,
    }


def _validate_replication_coverage(df: pd.DataFrame) -> None:
    """Fail loudly when the nominal paper sample is not actually available.

    This prevents a regression using (for example) only 2010-2022 observations
    from being labeled as the January 1996-December 2022 replication.
    """
    for h in HORIZONS:
        y = f"excess_fwd_{h}"
        x = f"svix2_{h}"
        sample = df.loc[
            df["date"].between(
                pd.Timestamp(ORIGINAL_SAMPLE_START),
                pd.Timestamp(ORIGINAL_SAMPLE_END),
            ),
            ["date", y, x],
        ].dropna()

        if sample.empty:
            raise RuntimeError(
                f"No usable {h} observations for the published replication sample."
            )

        first = sample["date"].min()
        last = sample["date"].max()

        # Allow a small startup/end buffer for trading calendars, but never a
        # multi-year truncation masquerading as the full paper sample.
        if first > pd.Timestamp(ORIGINAL_SAMPLE_START) + pd.Timedelta(days=31):
            raise RuntimeError(
                f"{h} replication coverage begins {first.date()}, not near "
                f"{pd.Timestamp(ORIGINAL_SAMPLE_START).date()}. "
                "Refusing to label this as the 1996-2022 sample."
            )
        if last < pd.Timestamp(ORIGINAL_SAMPLE_END) - pd.Timedelta(days=31):
            raise RuntimeError(
                f"{h} replication coverage ends {last.date()}, not near "
                f"{pd.Timestamp(ORIGINAL_SAMPLE_END).date()}. "
                "Check forward returns / source-data horizon coverage."
            )


def replicate_table1(df: pd.DataFrame) -> pd.DataFrame:
    _validate_replication_coverage(df)
    rows = []
    for h in HORIZONS:
        rows.append(
            run_regression(
                df,
                h,
                ORIGINAL_SAMPLE_START,
                ORIGINAL_SAMPLE_END,
                "January 1996-December 2022",
            )
        )
    for h in HORIZONS:
        rows.append(
            run_regression(
                df,
                h,
                RECENT_SAMPLE_START,
                ORIGINAL_SAMPLE_END,
                "February 2012-December 2022",
            )
        )
    return pd.DataFrame(rows)


def build_published_comparison(result: pd.DataFrame) -> pd.DataFrame:
    pub = PUBLISHED.set_index("horizon")
    full = result[result["sample"] == "January 1996-December 2022"].set_index("horizon")
    recent = result[result["sample"] == "February 2012-December 2022"].set_index("horizon")
    rows = []
    for h in HORIZONS:
        row = {"horizon": h}
        for label, rep, suffix in (
            ("1996_2022", full.loc[h], "1996_2022"),
            ("2012_2022", recent.loc[h], "2012_2022"),
        ):
            for metric, rep_col, pub_col in (
                ("alpha", "alpha", f"alpha_{suffix}"),
                ("alpha_se", "alpha_se_nw", f"alpha_se_{suffix}"),
                ("beta", "beta", f"beta_{suffix}"),
                ("beta_se", "beta_se_nw", f"beta_se_{suffix}"),
                ("r2", "r2", f"r2_{suffix}"),
            ):
                rv = float(rep[rep_col])
                pv = float(pub.loc[h, pub_col])
                row[f"{metric}_rep_{label}"] = rv
                row[f"{metric}_pub_{label}"] = pv
                row[f"{metric}_abs_diff_{label}"] = abs(rv - pv)
        rows.append(row)
    return pd.DataFrame(rows)


def updated_table(df: pd.DataFrame) -> pd.DataFrame:
    """Re-estimate from 1996 through the latest realized target per horizon."""
    return pd.DataFrame(
        [
            run_regression(
                df,
                h,
                ORIGINAL_SAMPLE_START,
                None,
                "January 1996-latest usable",
            )
            for h in HORIZONS
        ]
    )


def post_2022_table(df: pd.DataFrame) -> pd.DataFrame:
    """Fresh post-paper sample beginning January 2023.

    This sample is short relative to the horizons being forecast, so the
    reported standard errors should not be read the way the full-sample ones
    are. Two columns make that explicit: ``hac_lag_share`` is the Newey-West lag
    length as a fraction of the sample, and ``independent_periods`` counts how
    many non-overlapping horizon returns the window actually contains. When the
    lag length approaches the sample size, or the window holds only one or two
    independent periods, the slope is not identified in any useful sense.
    """
    result = pd.DataFrame(
        [
            run_regression(
                df,
                h,
                POST_2022_START,
                None,
                "January 2023-latest usable",
                require_full_hac=False,
            )
            for h in HORIZONS
        ]
    )
    horizon_days = result["horizon"].map(HORIZON_DAYS).astype(float)
    span_days = (
        pd.to_datetime(result["last_usable_date"]) - pd.Timestamp(POST_2022_START)
    ).dt.days
    result["hac_lag_share"] = result["nw_lags"] / result["nobs"].replace(0, np.nan)
    result["independent_periods"] = (span_days / horizon_days).round(2)
    result["inference_reliable"] = (
        (result["hac_lag_share"] < 0.25) & (result["independent_periods"] >= 5)
    )
    return result


if __name__ == "__main__":
    data = load_table1_data()
    replication = replicate_table1(data)
    comparison = build_published_comparison(replication)
    updated = updated_table(data)
    post = post_2022_table(data)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    replication.to_csv(OUT, index=False)
    comparison.to_csv(COMPARISON_OUT, index=False)
    updated.to_csv(UPDATED_OUT, index=False)
    post.to_csv(POST_2022_OUT, index=False)

    print(replication.to_string(index=False))
    print(f"\nSaved Table 1 replication -> {OUT}")
    print(f"Saved published comparison -> {COMPARISON_OUT}")
    print(f"Saved full updated regressions -> {UPDATED_OUT}")
    print(f"Saved post-2022 regressions -> {POST_2022_OUT}")
