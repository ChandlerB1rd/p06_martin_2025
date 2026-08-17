"""Construct maturity-matched rates and coherent SPX forward-price surfaces."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from clean_optionmetrics import iter_clean_options
from clean_zero_curve import load_clean_zero_curve
from martin_spec import YEAR_DAYS
from settings import config

DATA_DIR = Path(config("DATA_DIR"))
OUT = DATA_DIR / "option_expiration_inputs.parquet"
DIAGNOSTICS_OUT = DATA_DIR / "forward_surface_diagnostics.csv"


def interpolate_zero_rate(day_curve: pd.DataFrame, maturity_days: float) -> float:
    """Linearly interpolate the zero rate in calendar maturity days."""
    g = day_curve.sort_values("maturity_days").drop_duplicates("maturity_days")
    x = g["maturity_days"].to_numpy(dtype=float)
    y = g["zero_rate"].to_numpy(dtype=float)
    if len(x) < 2 or maturity_days < x.min() or maturity_days > x.max():
        return np.nan
    return float(np.interp(maturity_days, x, y))


def estimate_forward(options: pd.DataFrame, rf_gross: float) -> tuple[float, float, int, str]:
    """Estimate the forward where call and put prices are equal.

    The preferred estimate linearly interpolates a sign crossing of C-P across
    paired strikes.  Under put-call parity C-P is linear in strike and its zero
    occurs at the forward.  If no crossing is observed, use the paired strike
    with the smallest |C-P| and the parity identity F = K + Rf(C-P).
    """
    q = options.copy()
    if "best_bid" in q.columns:
        q = q[pd.to_numeric(q["best_bid"], errors="coerce") > 0]
    wide = q.pivot_table(
        index="strike", columns="cp_flag", values="mid", aggfunc="min"
    )
    if "C" not in wide or "P" not in wide:
        return np.nan, np.nan, 0, "no_pairs"
    pairs = wide[["C", "P"]].dropna().sort_index()
    n_pairs = len(pairs)
    if n_pairs == 0:
        return np.nan, np.nan, 0, "no_pairs"

    diff = pairs["C"] - pairs["P"]
    k = pairs.index.to_numpy(dtype=float)
    d = diff.to_numpy(dtype=float)

    exact = np.flatnonzero(np.isclose(d, 0.0))
    if len(exact):
        idx = exact[np.argmin(np.abs(k[exact] - np.median(k)))]
        return float(k[idx]), 0.0, n_pairs, "exact_cp_equal"

    crossings = []
    for i in range(len(k) - 1):
        if d[i] * d[i + 1] < 0:
            forward = k[i] + (0.0 - d[i]) * (k[i + 1] - k[i]) / (d[i + 1] - d[i])
            local_gap = min(abs(d[i]), abs(d[i + 1]))
            crossings.append((local_gap, forward))
    if crossings:
        _, forward = min(crossings, key=lambda x: x[0])
        return float(forward), float(min(np.abs(d))), n_pairs, "cp_crossing"

    idx = int(np.argmin(np.abs(d)))
    forward = k[idx] + rf_gross * d[idx]
    return float(forward), float(abs(d[idx])), n_pairs, "parity_nearest"


def _surface_record(
    group: pd.DataFrame,
    zero_rate: float,
    rf_gross: float,
) -> dict[str, object]:
    forward, gap, n_pairs, method = estimate_forward(group, rf_gross)
    metadata = {}
    for col in ("root", "suffix", "am_settlement", "ss_flag", "contract_size", "expiry_indicator"):
        if col in group.columns:
            vals = group[col].dropna()
            metadata[col] = vals.iloc[0] if len(vals) else np.nan
    return {
        "date": group["date"].iloc[0],
        "exdate": group["exdate"].iloc[0],
        "surface_key": group["surface_key"].iloc[0],
        "days_to_expiry": int(group["days_to_expiry"].iloc[0]),
        "spot": float(group["spot"].iloc[0]),
        "zero_rate": zero_rate,
        "rf_gross": rf_gross,
        "forward": forward,
        "parity_abs_cp_diff": gap,
        "paired_strikes": n_pairs,
        "surface_quote_rows": len(group),
        "median_spread": float(group["spread"].median()),
        "forward_method": method,
        **metadata,
    }


def build_expiration_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    curve = load_clean_zero_curve()
    curves = {d: g for d, g in curve.groupby("date", sort=False)}
    candidate_records = []

    for meta, options in iter_clean_options():
        print(f"[forward] {meta.start_date} to {meta.end_date}")
        for (obs_date, exdate, surface_key), g in options.groupby(
            ["date", "exdate", "surface_key"], sort=False
        ):
            day_curve = curves.get(obs_date)
            if day_curve is None:
                continue
            dte = int(g["days_to_expiry"].iloc[0])
            zero_rate = interpolate_zero_rate(day_curve, dte)
            if not np.isfinite(zero_rate):
                continue
            # OptionMetrics zero rates are treated as continuously compounded;
            # preserve the gross factor explicitly for auditability.
            rf_gross = float(np.exp(zero_rate * dte / YEAR_DAYS))
            rec = _surface_record(g, zero_rate, rf_gross)
            if np.isfinite(rec["forward"]) and rec["paired_strikes"] >= 2:
                candidate_records.append(rec)

    candidates = pd.DataFrame(candidate_records)
    if candidates.empty:
        raise RuntimeError("No usable forward-price surfaces were constructed.")

    candidates["candidate_surfaces"] = candidates.groupby(
        ["date", "exdate"]
    )["surface_key"].transform("nunique")

    # One coherent surface per date/expiration.  Prefer maximum paired-strike
    # coverage, then smaller parity gap and narrower median spread.  This is a
    # transparent adaptation for modern data where AM and PM SPX series can
    # share a calendar expiration; quotes are never mixed across those series.
    selected = (
        candidates.sort_values(
            [
                "date",
                "exdate",
                "paired_strikes",
                "parity_abs_cp_diff",
                "median_spread",
            ],
            ascending=[True, True, False, True, True],
        )
        .drop_duplicates(["date", "exdate"], keep="first")
        .sort_values(["date", "exdate"])
        .reset_index(drop=True)
    )

    diagnostics = (
        candidates.groupby(["date", "exdate"], as_index=False)
        .agg(
            candidate_surfaces=("surface_key", "nunique"),
            best_paired_strikes=("paired_strikes", "max"),
            min_parity_gap=("parity_abs_cp_diff", "min"),
        )
    )
    diagnostics = diagnostics[diagnostics["candidate_surfaces"] > 1]
    return selected, diagnostics


def load_expiration_inputs(data_dir=DATA_DIR) -> pd.DataFrame:
    return pd.read_parquet(Path(data_dir) / OUT.name)


if __name__ == "__main__":
    result, diagnostics = build_expiration_inputs()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(OUT, index=False)
    diagnostics.to_csv(DIAGNOSTICS_OUT, index=False)
    print(f"Saved {len(result):,} selected expiration inputs -> {OUT}")
    print(
        f"Multi-surface date/expiration groups documented: {len(diagnostics):,} "
        f"-> {DIAGNOSTICS_OUT}"
    )
