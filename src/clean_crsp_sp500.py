"""Clean CRSP's daily S&P 500 total-return series."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from settings import config
from pull_crsp_sp500 import load_crsp_sp500

DATA_DIR = Path(config("DATA_DIR"))
OUT = DATA_DIR / "crsp_sp500_daily_clean.parquet"


def clean_crsp_sp500(df: pd.DataFrame) -> pd.DataFrame:
    """Return unique, ordered daily S&P 500 simple total returns."""
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"])
    out["ret"] = pd.to_numeric(out["ret"], errors="coerce")
    out = out.dropna(subset=["date", "ret"])
    out = out[out["ret"] > -1.0]
    out = out[["date", "ret"]]
    return (
        out.sort_values("date")
        .drop_duplicates("date", keep="last")
        .reset_index(drop=True)
    )


def load_clean_crsp_sp500(data_dir=DATA_DIR) -> pd.DataFrame:
    """Load cleaned CRSP S&P 500 daily returns."""
    return pd.read_parquet(Path(data_dir) / OUT.name)


if __name__ == "__main__":
    clean = clean_crsp_sp500(load_crsp_sp500())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    clean.to_parquet(OUT, index=False)
    print(
        f"Saved {len(clean):,} CRSP rows "
        f"({clean['date'].min().date()} to {clean['date'].max().date()}) -> {OUT}"
    )
