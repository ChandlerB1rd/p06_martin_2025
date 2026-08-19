"""Pull OptionMetrics SPX forward prices (fwdprd) from WRDS.

The production pipeline infers the forward from put-call parity on the option
chain itself. OptionMetrics also publishes its own forward-price file, which is
built from the whole chain rather than from a single paired strike and therefore
behaves differently on thin long-dated expirations.

This puller exists so the two conventions can be compared directly; see
``forward_robustness.py``. It is small relative to the option pull, on the order
of a few megabytes for the whole history.
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pandas as pd

from pull_optionmetrics import SPX_SECID, tables_for_prefix
from settings import config
from wrds_helpers import connect_wrds, get_table_columns, save_parquet

DATA_DIR = Path(config("DATA_DIR"))
OPTION_LIBRARY = os.getenv("P06_OPTION_LIBRARY", "optionm_all")
START_DATE = os.getenv(
    "P06_OPTION_START_DATE", os.getenv("P06_START_DATE", "1996-01-01")
)
END_DATE = os.getenv(
    "P06_OPTION_END_DATE", os.getenv("P06_END_DATE", date.today().isoformat())
)
OUT = DATA_DIR / "optionmetrics_spx_forwards_raw.parquet"

REQUIRED = ("secid", "date", "expiration", "forwardprice")
OPTIONAL = ("amsettlement",)


def pull_spx_forwards(db) -> pd.DataFrame:
    """Pull and combine the SPX forward-price surface across year partitions."""
    frames = []
    tables = tables_for_prefix(db, "fwdprd", START_DATE, END_DATE)
    print(f"Forward-price tables selected: {tables}")

    for table in tables:
        columns = {c.lower() for c in get_table_columns(db, OPTION_LIBRARY, table)}
        # OptionMetrics has used both `expiration` and `exdate` for this column.
        expiry_col = "expiration" if "expiration" in columns else "exdate"
        required = {"secid", "date", expiry_col, "forwardprice"}
        if not required.issubset(columns):
            raise RuntimeError(
                f"{OPTION_LIBRARY}.{table} is missing {sorted(required - columns)}"
            )
        select = ["secid", "date", f"{expiry_col} AS exdate", "forwardprice"]
        select += [c for c in OPTIONAL if c in columns]

        sql = f"""
            SELECT {', '.join(select)}
            FROM {OPTION_LIBRARY}.{table}
            WHERE secid = %(secid)s
              AND date BETWEEN %(start_date)s AND %(end_date)s
            ORDER BY date, {expiry_col}
        """
        frame = db.raw_sql(
            sql,
            params={
                "secid": SPX_SECID,
                "start_date": START_DATE,
                "end_date": END_DATE,
            },
            date_cols=["date", "exdate"],
        )
        print(f"[forwards] {table}: {len(frame):,} rows")
        if not frame.empty:
            frames.append(frame)

    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    if "amsettlement" in combined.columns:
        # Prefer the AM-settled quote when a date/expiration carries both.
        combined = combined.sort_values(
            ["date", "exdate", "amsettlement"], ascending=[True, True, False]
        )
    return (
        combined.drop_duplicates(["date", "exdate"], keep="first")
        .sort_values(["date", "exdate"])
        .reset_index(drop=True)
    )


def load_spx_forwards(data_dir=DATA_DIR) -> pd.DataFrame:
    return pd.read_parquet(Path(data_dir) / OUT.name)


if __name__ == "__main__":
    db = connect_wrds()
    try:
        forwards = pull_spx_forwards(db)
    finally:
        db.close()
    if forwards.empty:
        raise RuntimeError("SPX forward-price pull returned zero rows.")
    save_parquet(forwards, OUT)
    print(f"Saved {len(forwards):,} forward-price rows -> {OUT}")
