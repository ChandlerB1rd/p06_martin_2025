"""Pull the OptionMetrics zero-coupon curve from WRDS."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pandas as pd

from settings import config
from wrds_helpers import connect_wrds, find_table_by_columns, save_parquet

DATA_DIR = Path(config("DATA_DIR"))
OPTION_LIBRARY = os.getenv("P06_OPTION_LIBRARY", "optionm_all")
START_DATE = os.getenv(
    "P06_OPTION_START_DATE", os.getenv("P06_START_DATE", "1996-01-01")
)
END_DATE = os.getenv(
    "P06_OPTION_END_DATE", os.getenv("P06_END_DATE", date.today().isoformat())
)
OUT = DATA_DIR / "optionmetrics_zero_curve_raw.parquet"


def pull_zero_curve(db) -> pd.DataFrame:
    table = find_table_by_columns(
        db,
        OPTION_LIBRARY,
        required_columns=("date", "days", "rate"),
        preferred_tables=("zerocd",),
    )
    sql = f"""
        SELECT date, days, rate
        FROM {OPTION_LIBRARY}.{table}
        WHERE date BETWEEN %(start_date)s AND %(end_date)s
        ORDER BY date, days
    """
    return db.raw_sql(
        sql,
        params={"start_date": START_DATE, "end_date": END_DATE},
        date_cols=["date"],
    )


def load_zero_curve(data_dir=DATA_DIR) -> pd.DataFrame:
    return pd.read_parquet(Path(data_dir) / OUT.name)


if __name__ == "__main__":
    db = connect_wrds()
    try:
        curve = pull_zero_curve(db)
    finally:
        db.close()
    if curve.empty:
        raise RuntimeError("OptionMetrics zero-curve pull returned zero rows.")
    save_parquet(curve, OUT)
    print(f"Saved {len(curve):,} zero-curve rows -> {OUT}")
