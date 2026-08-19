"""Construct expiration-level and fixed-horizon SVIX from SPX options.

Equation (19) in Martin (2025) is evaluated using the documented discrete
strike construction from Martin (2017): one lower-mid option per strike and
CBOE-style Delta-K weights.  Fixed horizons are 30/90/180/360 calendar days.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from clean_optionmetrics import iter_clean_options
from forward_prices import load_expiration_inputs
from martin_spec import ANNUALIZATION_FACTOR, HORIZON_DAYS, HORIZONS
from option_surface import option_sum
from settings import config

DATA_DIR = Path(config("DATA_DIR"))
EXPIRATION_OUT = DATA_DIR / "svix_by_expiration.parquet"
DAILY_OUT = DATA_DIR / "svix_daily.parquet"


def compute_svix_for_expiration(
    options: pd.DataFrame,
    forward: float,
    rf_gross: float,
    spot: float,
    annualization_factor: float | None = None,
) -> dict[str, float | int]:
    """Compute Equation (19) for one date/expiration surface.

    ``svix2_total`` is the variance for the option's actual horizon.  If an
    annualization factor is supplied, ``svix2`` is the corresponding annualized
    quantity; expiration-level production uses 365/DTE as a diagnostic only.
    Fixed-horizon output later uses the paper's 12/4/2/1 factors exactly.
    """
    sums = option_sum(options, boundary=forward, strike_power=0.0)
    total = float(sums["total_sum"])
    if not np.isfinite(total) or total < 0 or rf_gross <= 0 or spot <= 0:
        return {
            **sums,
            "svix2_total": np.nan,
            "svix_total": np.nan,
            "svix2": np.nan,
            "svix": np.nan,
        }

    svix2_total = 2.0 * total / (rf_gross * spot**2)
    factor = 1.0 if annualization_factor is None else float(annualization_factor)
    svix2 = svix2_total * factor
    return {
        **sums,
        "svix2_total": float(svix2_total),
        "svix_total": float(np.sqrt(max(svix2_total, 0.0))),
        "svix2": float(svix2),
        "svix": float(np.sqrt(max(svix2, 0.0))),
    }


def build_svix_by_expiration(inputs: pd.DataFrame | None = None) -> pd.DataFrame:
    """Compute SVIX per date/expiration surface.

    ``inputs`` defaults to the production expiration inputs. Passing an
    alternative table allows the same construction to be re-run under a
    different forward-price convention without duplicating this loop.
    """
    if inputs is None:
        inputs = load_expiration_inputs()
    records = []

    for meta, options in iter_clean_options():
        start = pd.Timestamp(meta.start_date)
        end = pd.Timestamp(meta.end_date)
        inp = inputs[(inputs["date"] >= start) & (inputs["date"] <= end)].copy()
        if inp.empty:
            continue
        keep = inp[
            [
                "date",
                "exdate",
                "surface_key",
                "days_to_expiry",
                "spot",
                "zero_rate",
                "rf_gross",
                "forward",
                "paired_strikes",
                "candidate_surfaces",
            ]
        ]
        merged = options.merge(
            keep,
            on=["date", "exdate", "surface_key"],
            how="inner",
            suffixes=("", "_input"),
        )
        print(f"[svix] {meta.start_date} to {meta.end_date}: {len(merged):,} selected quotes")

        for (obs_date, exdate, surface_key), g in merged.groupby(
            ["date", "exdate", "surface_key"], sort=False
        ):
            dte = int(g["days_to_expiry_input"].iloc[0]) if "days_to_expiry_input" in g else int(g["days_to_expiry"].iloc[0])
            # Diagnostic annualization at the exact listed maturity. Fixed
            # horizon series below use the paper-style 12/4/2/1 factors.
            out = compute_svix_for_expiration(
                g,
                forward=float(g["forward"].iloc[0]),
                rf_gross=float(g["rf_gross"].iloc[0]),
                spot=float(g["spot_input"].iloc[0] if "spot_input" in g else g["spot"].iloc[0]),
                annualization_factor=365.0 / dte,
            )
            records.append(
                {
                    "date": obs_date,
                    "exdate": exdate,
                    "surface_key": surface_key,
                    "days_to_expiry": dte,
                    "spot": float(g["spot_input"].iloc[0] if "spot_input" in g else g["spot"].iloc[0]),
                    "zero_rate": float(g["zero_rate"].iloc[0]),
                    "rf_gross": float(g["rf_gross"].iloc[0]),
                    "forward": float(g["forward"].iloc[0]),
                    "put_contribution": out["put_sum"],
                    "call_contribution": out["call_sum"],
                    "total_option_sum": out["total_sum"],
                    "n_options": out["n_options"],
                    "svix2_total": out["svix2_total"],
                    "svix_total": out["svix_total"],
                    "svix2_ann_exact_dte": out["svix2"],
                    "svix_ann_exact_dte": out["svix"],
                }
            )

    out = pd.DataFrame(records)
    if out.empty:
        raise RuntimeError("SVIX construction produced zero expiration records.")
    return out.sort_values(["date", "days_to_expiry", "exdate"]).reset_index(drop=True)


def interpolate_fixed_maturity(
    expirations: pd.DataFrame,
    target_days: int,
    value_col: str,
) -> tuple[float, float, float, bool]:
    """Linearly interpolate/extrapolate one value to a fixed calendar maturity.

    Returns (value, left_dte, right_dte, extrapolated).  When the target is
    outside the available range, the nearest two eligible expirations are used,
    matching the documented short-maturity extrapolation logic.
    """
    g = (
        expirations[["days_to_expiry", value_col]]
        .dropna()
        .groupby("days_to_expiry", as_index=False)[value_col]
        .mean()
        .sort_values("days_to_expiry")
    )
    if len(g) < 2:
        return np.nan, np.nan, np.nan, False
    x = g["days_to_expiry"].to_numpy(dtype=float)
    y = g[value_col].to_numpy(dtype=float)

    exact = np.where(x == target_days)[0]
    if len(exact):
        i = int(exact[0])
        return float(y[i]), float(x[i]), float(x[i]), False

    if target_days < x[0]:
        i, j, extrapolated = 0, 1, True
    elif target_days > x[-1]:
        i, j, extrapolated = len(x) - 2, len(x) - 1, True
    else:
        j = int(np.searchsorted(x, target_days, side="right"))
        i, extrapolated = j - 1, False

    value = y[i] + (target_days - x[i]) * (y[j] - y[i]) / (x[j] - x[i])
    return float(value), float(x[i]), float(x[j]), extrapolated


def build_fixed_horizon_svix(expiration_svix: pd.DataFrame) -> pd.DataFrame:
    """Construct daily 30/90/180/360-day SVIX term structure."""
    rows = []
    for obs_date, g in expiration_svix.groupby("date", sort=True):
        row: dict[str, object] = {"date": obs_date}
        for h in HORIZONS:
            target = HORIZON_DAYS[h]
            # Martin (2017) first computes the annualized bound at listed
            # maturities, then linearly interpolates that bound to fixed T.
            ann_var, left, right, extrap = interpolate_fixed_maturity(
                g, target, "svix2_ann_exact_dte"
            )
            factor = ANNUALIZATION_FACTOR[h]
            total_var = ann_var / factor if np.isfinite(ann_var) else np.nan
            row[f"target_days_{h}"] = target
            row[f"svix2_total_{h}"] = total_var
            row[f"svix_total_{h}"] = np.sqrt(total_var) if total_var >= 0 else np.nan
            row[f"svix2_{h}"] = ann_var
            row[f"svix_{h}"] = np.sqrt(ann_var) if ann_var >= 0 else np.nan
            row[f"source_dte_left_{h}"] = left
            row[f"source_dte_right_{h}"] = right
            row[f"extrapolated_{h}"] = extrap
        rows.append(row)
    return pd.DataFrame(rows).sort_values("date").reset_index(drop=True)


def load_svix_by_expiration(data_dir=DATA_DIR) -> pd.DataFrame:
    return pd.read_parquet(Path(data_dir) / EXPIRATION_OUT.name)


def load_svix_daily(data_dir=DATA_DIR) -> pd.DataFrame:
    return pd.read_parquet(Path(data_dir) / DAILY_OUT.name)


if __name__ == "__main__":
    by_exp = build_svix_by_expiration()
    daily = build_fixed_horizon_svix(by_exp)
    EXPIRATION_OUT.parent.mkdir(parents=True, exist_ok=True)
    by_exp.to_parquet(EXPIRATION_OUT, index=False)
    daily.to_parquet(DAILY_OUT, index=False)
    print(f"Saved {len(by_exp):,} expiration-level SVIX rows -> {EXPIRATION_OUT}")
    print(f"Saved {len(daily):,} daily fixed-horizon SVIX rows -> {DAILY_OUT}")
