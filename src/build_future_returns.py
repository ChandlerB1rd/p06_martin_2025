"""Construct fixed-horizon future S&P 500 total and excess returns."""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

from clean_crsp_sp500 import load_clean_crsp_sp500
from clean_zero_curve import load_clean_zero_curve
from forward_prices import interpolate_zero_rate
from martin_spec import ANNUALIZATION_FACTOR, HORIZON_DAYS, HORIZONS, YEAR_DAYS
from settings import config

DATA_DIR = Path(config("DATA_DIR"))
OUT = DATA_DIR / "future_sp500_returns.parquet"

# CRSP publishes on a slower cadence than OptionMetrics, so a modest lag is
# normal. A gap beyond this many days indicates a stale source table rather than
# a publication lag, which would silently truncate the update sample.
MAX_RETURN_LAG_DAYS = int(os.getenv("P06_MAX_RETURN_LAG_DAYS", "180"))


def check_return_coverage(
    crsp: pd.DataFrame,
    zero_curve: pd.DataFrame,
    max_lag_days: int = MAX_RETURN_LAG_DAYS,
) -> int:
    """Fail when the return series ends far behind the option-derived series.

    Table 1's dependent variable is a realized forward return, so the update
    sample can only run as far as CRSP does. A stale return file therefore
    truncates the sample without any visible error, and at the 6- and 12-month
    horizons that truncation is large enough to change the sign of the slope.
    """
    crsp_end = pd.to_datetime(crsp["date"]).max()
    option_end = pd.to_datetime(zero_curve["date"]).max()
    lag_days = int((option_end - crsp_end).days)

    print(
        f"Return coverage: CRSP to {crsp_end.date()}, option data to "
        f"{option_end.date()} ({lag_days} day gap)"
    )
    if lag_days > max_lag_days:
        raise RuntimeError(
            f"CRSP returns end {lag_days} days before the option data "
            f"({crsp_end.date()} vs {option_end.date()}), which exceeds the "
            f"{max_lag_days}-day tolerance. This usually means a frozen CRSP "
            "index file was selected; see find_crsp_sp500_table. Set "
            "P06_MAX_RETURN_LAG_DAYS to override."
        )
    return lag_days


def future_return_to_day_target(
    daily: pd.DataFrame,
    target_days: int,
) -> tuple[pd.Series, pd.Series]:
    """Compound returns to first CRSP trading day on/after t + target_days.

    The return printed for predictor date t itself is excluded.  Returns from
    the next CRSP observation through the target observation are compounded.
    """
    d = daily.sort_values("date").reset_index(drop=True)
    dates = d["date"].to_numpy(dtype="datetime64[ns]")
    gross = 1.0 + d["ret"].to_numpy(dtype=float)
    if np.any(gross <= 0):
        raise ValueError("Daily gross returns must be positive.")

    log_gross = np.log(gross)
    csum = np.concatenate(([0.0], np.cumsum(log_gross)))
    values = np.full(len(d), np.nan)
    target_dates = np.full(len(d), np.datetime64("NaT"), dtype="datetime64[ns]")

    for i, dt in enumerate(pd.to_datetime(d["date"])):
        target = dt + pd.Timedelta(days=int(target_days))
        j = int(np.searchsorted(dates, np.datetime64(target), side="left"))
        if j >= len(d) or j <= i:
            continue
        log_total = csum[j + 1] - csum[i + 1]
        values[i] = np.exp(log_total) - 1.0
        target_dates[i] = dates[j]

    return pd.Series(values, index=d.index), pd.Series(target_dates, index=d.index)


def build_future_returns(
    crsp: pd.DataFrame,
    zero_curve: pd.DataFrame,
) -> pd.DataFrame:
    """Build period-total and paper-style annualized return targets."""
    check_return_coverage(crsp, zero_curve)
    out = crsp.sort_values("date").reset_index(drop=True).copy()
    curves = {pd.Timestamp(dt): g for dt, g in zero_curve.groupby("date", sort=False)}

    for h in HORIZONS:
        days = HORIZON_DAYS[h]
        factor = ANNUALIZATION_FACTOR[h]
        market, realized_target = future_return_to_day_target(out, days)
        out[f"realized_target_date_{h}"] = realized_target
        out[f"market_fwd_{h}"] = market
        out[f"market_fwd_ann_{h}"] = factor * market

        rf_values = []
        for dt in pd.to_datetime(out["date"]):
            curve = curves.get(pd.Timestamp(dt))
            if curve is None:
                rf_values.append(np.nan)
                continue
            zero_rate = interpolate_zero_rate(curve, days)
            if not np.isfinite(zero_rate):
                rf_values.append(np.nan)
                continue
            rf_values.append(float(np.exp(zero_rate * days / YEAR_DAYS)))

        out[f"rf_gross_{h}"] = rf_values
        market_gross = 1.0 + out[f"market_fwd_{h}"]
        total_excess = market_gross / out[f"rf_gross_{h}"] - 1.0
        out[f"excess_total_{h}"] = total_excess
        # Primary Table 1 dependent variable. Martin's earlier implementation
        # annualizes by dividing by horizon length; for the fixed monthly
        # horizons this corresponds to 12/4/2/1.
        out[f"excess_fwd_{h}"] = factor * total_excess

    return out


def load_future_returns(data_dir=DATA_DIR) -> pd.DataFrame:
    return pd.read_parquet(Path(data_dir) / OUT.name)


if __name__ == "__main__":
    result = build_future_returns(load_clean_crsp_sp500(), load_clean_zero_curve())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(OUT, index=False)
    print(f"Saved {len(result):,} future-return rows -> {OUT}")
