"""Clean OptionMetrics zero-coupon rates."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from settings import config
from pull_zero_curve import load_zero_curve

DATA_DIR = Path(config("DATA_DIR"))
OUT = DATA_DIR / "optionmetrics_zero_curve_clean.parquet"


def infer_rate_divisor(rate: pd.Series) -> float:
    """Infer whether rates are in percentage points or decimal units."""
    x = pd.to_numeric(rate, errors="coerce").dropna().abs()
    if x.empty:
        raise RuntimeError("Cannot infer zero-rate units from an empty series.")
    # A typical decimal rate is around 0.01-0.10; percentage-point storage is 1-10.
    return 100.0 if x.median() > 0.5 else 1.0


def clean_zero_curve(curve: pd.DataFrame) -> pd.DataFrame:
    """Return date, maturity_days, and decimal zero_rate."""
    out = curve.copy()
    out["date"] = pd.to_datetime(out["date"])
    out["days"] = pd.to_numeric(out["days"], errors="coerce")
    out["rate"] = pd.to_numeric(out["rate"], errors="coerce")
    out = out.dropna(subset=["date", "days", "rate"])
    out = out[(out["days"] > 0) & np.isfinite(out["rate"])]

    divisor = infer_rate_divisor(out["rate"])
    out["maturity_days"] = out["days"].round().astype(int)
    out["zero_rate"] = out["rate"] / divisor

    out = out[["date", "maturity_days", "zero_rate"]]
    out = out.sort_values(["date", "maturity_days"])
    out = out.drop_duplicates(["date", "maturity_days"], keep="last")
    return out.reset_index(drop=True)


def load_clean_zero_curve(data_dir=DATA_DIR) -> pd.DataFrame:
    """Load cleaned zero-curve data."""
    return pd.read_parquet(Path(data_dir) / OUT.name)


if __name__ == "__main__":
    clean = clean_zero_curve(load_zero_curve())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    clean.to_parquet(OUT, index=False)
    print(
        f"Saved {len(clean):,} zero-curve rows "
        f"({clean['date'].min().date()} to {clean['date'].max().date()}) -> {OUT}"
    )
