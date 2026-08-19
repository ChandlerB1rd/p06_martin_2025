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


def _sp500_candidates(db) -> list[tuple[str, str]]:
    """Return (table, date column) pairs that can supply S&P 500 total returns."""
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
    # dedicated S&P 500 index files rather than the broad CRSP market-index
    # file, because VWRETD has a different universe in DSI.
    candidates = []
    for table in sorted(grouped.index):
        if not table.startswith("dsp500"):
            continue
        columns = grouped.loc[table]
        if "vwretd" not in columns:
            continue
        for date_col in ("caldt", "dlycaldt", "indexdate", "date"):
            if date_col in columns:
                candidates.append((table, date_col))
                break
    return candidates


def find_crsp_sp500_table(db) -> tuple[str, str]:
    """Select the S&P 500 index file with the most recent coverage.

    CRSP froze the legacy ``dsp500`` file when it migrated to the ``_v2`` index
    files, so name-ordered discovery silently returns a series that ends in
    December 2024. Table 1's dependent variable is a realized forward return, so
    a stale return file truncates the update sample by a year and materially
    changes the post-2022 slopes. Choosing on observed coverage rather than on a
    hardcoded name order keeps this correct across future CRSP migrations.
    """
    candidates = _sp500_candidates(db)
    if not candidates:
        raise RuntimeError("Could not locate CRSP DSP500 with VWRETD and a date field.")

    coverage = []
    for table, date_col in candidates:
        probe = db.raw_sql(
            f"SELECT max({date_col}) AS last_date FROM {CRSP_LIBRARY}.{table}"
        )
        last_date = pd.to_datetime(probe["last_date"].iloc[0], errors="coerce")
        if pd.isna(last_date):
            continue
        coverage.append((last_date, table, date_col))

    if not coverage:
        raise RuntimeError("No CRSP S&P 500 candidate table returned a usable date range.")

    coverage.sort(reverse=True)
    for last_date, table, _ in coverage:
        print(f"CRSP candidate {CRSP_LIBRARY}.{table}: last observation {last_date.date()}")
    _, best_table, best_date_col = coverage[0]
    return best_table, best_date_col


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
