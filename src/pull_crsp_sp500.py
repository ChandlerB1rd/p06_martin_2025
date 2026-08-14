"""Pull CRSP daily S&P Composite Index total returns from WRDS."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pandas as pd

from settings import config
from wrds_helpers import connect_wrds, save_parquet

DATA_DIR = Path(config("DATA_DIR"))
CRSP_LIBRARY = os.getenv("P06_CRSP_LIBRARY", "crsp")
START_DATE = os.getenv(
    "P06_CRSP_START_DATE", os.getenv("P06_START_DATE", "1996-01-01")
)
END_DATE = os.getenv(
    "P06_CRSP_END_DATE", os.getenv("P06_END_DATE", date.today().isoformat())
)
OUT = DATA_DIR / "crsp_sp500_daily_raw.parquet"


def find_crsp_sp500_table(db) -> tuple[str, str]:
    sql = """
        SELECT lower(table_name) AS table_name,
               lower(column_name) AS column_name
        FROM information_schema.columns
        WHERE lower(table_schema) = %(library)s
          AND lower(column_name) IN
              ('vwretd', 'caldt', 'date', 'dlycaldt', 'indexdate')
    """
    cols = db.raw_sql(sql, params={"library": CRSP_LIBRARY.lower()})
    if cols.empty:
        raise RuntimeError("Could not inspect CRSP index columns.")
    grouped = cols.groupby("table_name")["column_name"].agg(set)
    # Table 1 requires S&P 500 total returns. Restrict discovery to the
    # dedicated S&P 500 index file rather than the broad CRSP market-index
    # file, because VWRETD has a different universe in DSI.
    preferred = ("dsp500", "dsp500_v2")
    candidates = list(preferred) + [t for t in grouped.index if t not in preferred]
    for table in candidates:
        if table not in grouped.index or "vwretd" not in grouped.loc[table]:
            continue
        columns = grouped.loc[table]
        for date_col in ("caldt", "dlycaldt", "indexdate", "date"):
            if date_col in columns:
                return table, date_col
    raise RuntimeError(
        "Could not locate CRSP DSP500 with VWRETD and a date field."
    )


def pull_crsp_sp500(db) -> pd.DataFrame:
    table, date_col = find_crsp_sp500_table(db)
    print(f"CRSP source selected: {CRSP_LIBRARY}.{table} ({date_col})")
    sql = f"""
        SELECT {date_col} AS date, vwretd AS ret
        FROM {CRSP_LIBRARY}.{table}
        WHERE {date_col} BETWEEN %(start_date)s AND %(end_date)s
        ORDER BY {date_col}
    """
    return db.raw_sql(
        sql,
        params={"start_date": START_DATE, "end_date": END_DATE},
        date_cols=["date"],
    )


def load_crsp_sp500(data_dir=DATA_DIR) -> pd.DataFrame:
    return pd.read_parquet(Path(data_dir) / OUT.name)


if __name__ == "__main__":
    db = connect_wrds()
    try:
        crsp = pull_crsp_sp500(db)
    finally:
        db.close()
    if crsp.empty:
        raise RuntimeError("CRSP S&P 500 return pull returned zero rows.")
    save_parquet(crsp, OUT)
    print(f"Saved {len(crsp):,} CRSP daily rows -> {OUT}")
