"""Pull SPX OptionMetrics data from WRDS in restartable yearly chunks.

The raw SPX option panel is large, so the production pipeline writes one
Parquet partition per requested calendar year and records the active files in
a manifest.  This makes the 1996-present pull restartable and avoids holding
three decades of option quotes in memory at once.

SPX is OptionMetrics secid 108105.  Raw licensed data remain under DATA_DIR and
must not be committed to Git.
"""

from __future__ import annotations

import os
import re
from datetime import date
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from martin_spec import MAX_DTE
from settings import config
from wrds_helpers import connect_wrds, get_table_columns, save_parquet

DATA_DIR = Path(config("DATA_DIR"))
OPTION_LIBRARY = os.getenv("P06_OPTION_LIBRARY", "optionm_all")
SPX_SECID = int(os.getenv("P06_SPX_SECID", "108105"))

# Preferred source-specific variables; old P06_START/END are retained for the
# small-sample workflow already used in this project.
START_DATE = os.getenv(
    "P06_OPTION_START_DATE", os.getenv("P06_START_DATE", "1996-01-01")
)
END_DATE = os.getenv(
    "P06_OPTION_END_DATE", os.getenv("P06_END_DATE", date.today().isoformat())
)
MAX_DAYS_TO_EXPIRY = int(os.getenv("P06_MAX_DTE", str(MAX_DTE)))
FORCE_REPULL = os.getenv("P06_FORCE_REPULL", "0").strip().lower() in {"1", "true", "yes", "y"}

RAW_DIR = DATA_DIR / "optionmetrics_raw"
MANIFEST_OUT = DATA_DIR / "optionmetrics_spx_raw_manifest.csv"
UNDERLYING_OUT = DATA_DIR / "optionmetrics_spx_underlying_raw.parquet"

OPTION_REQUIRED = (
    "secid",
    "date",
    "exdate",
    "cp_flag",
    "strike_price",
    "best_bid",
    "best_offer",
)
OPTION_OPTIONAL = (
    "optionid",
    "symbol",
    "symbol_flag",
    "last_date",
    "volume",
    "open_interest",
    "impl_volatility",
    "delta",
    "gamma",
    "vega",
    "theta",
    "cfadj",
    "am_settlement",
    "ss_flag",
    "contract_size",
    "forward_price",
    "expiry_indicator",
    "root",
    "suffix",
)


def requested_years(start_date: str = START_DATE, end_date: str = END_DATE) -> list[int]:
    start_year = pd.Timestamp(start_date).year
    end_year = pd.Timestamp(end_date).year
    if end_year < start_year:
        raise ValueError("P06 option end date precedes start date.")
    return list(range(start_year, end_year + 1))


def _available_tables(db, library: str) -> dict[str, str]:
    return {t.lower(): t for t in db.list_tables(library=library)}


def tables_for_prefix(
    db,
    prefix: str,
    start_date: str = START_DATE,
    end_date: str = END_DATE,
) -> list[str]:
    """Find a consolidated table or all year partitions needed for a range."""
    available = _available_tables(db, OPTION_LIBRARY)
    if prefix.lower() in available:
        return [available[prefix.lower()]]

    years = requested_years(start_date, end_date)
    selected: list[str] = []
    for year in years:
        for candidate in (f"{prefix}{year}", f"{prefix}_{year}", f"{prefix}-{year}"):
            if candidate.lower() in available:
                selected.append(available[candidate.lower()])
                break

    if selected:
        return selected

    pattern = re.compile(rf"^{re.escape(prefix.lower())}[_-]?(\d{{4}})$")
    by_year = {}
    for lower, actual in available.items():
        match = pattern.match(lower)
        if match:
            by_year[int(match.group(1))] = actual
    selected = [by_year[y] for y in years if y in by_year]
    if selected:
        return selected

    similar = [actual for lower, actual in available.items() if lower.startswith(prefix.lower())]
    raise RuntimeError(
        f"Could not find {prefix!r} tables in {OPTION_LIBRARY!r} for "
        f"{start_date} through {end_date}. Similar tables: {similar[:30]}"
    )


def _table_window(table: str) -> tuple[str, str]:
    """Clip the requested window to a four-digit year suffix when present."""
    match = re.search(r"(\d{4})$", table)
    if not match:
        return START_DATE, END_DATE
    year = int(match.group(1))
    start = max(pd.Timestamp(START_DATE), pd.Timestamp(f"{year}-01-01"))
    end = min(pd.Timestamp(END_DATE), pd.Timestamp(f"{year}-12-31"))
    return start.date().isoformat(), end.date().isoformat()


def _partition_path(table: str, start_date: str, end_date: str) -> Path:
    safe_table = re.sub(r"[^A-Za-z0-9_.-]+", "_", table)
    return RAW_DIR / f"spx_{safe_table}_{start_date}_{end_date}.parquet"


def pull_option_partition(db, table: str, start_date: str, end_date: str) -> pd.DataFrame:
    columns = set(get_table_columns(db, OPTION_LIBRARY, table))
    missing = set(OPTION_REQUIRED) - columns
    if missing:
        raise RuntimeError(
            f"{OPTION_LIBRARY}.{table} is missing required columns {sorted(missing)}"
        )
    optional = [c for c in OPTION_OPTIONAL if c in columns]
    select_cols = list(OPTION_REQUIRED) + optional

    sql = f"""
        SELECT {', '.join(select_cols)}
        FROM {OPTION_LIBRARY}.{table}
        WHERE secid = %(secid)s
          AND date BETWEEN %(start_date)s AND %(end_date)s
          AND exdate > date
          AND (exdate::date - date::date) < %(max_dte)s
        ORDER BY date, exdate, strike_price, cp_flag
    """
    return db.raw_sql(
        sql,
        params={
            "secid": SPX_SECID,
            "start_date": start_date,
            "end_date": end_date,
            "max_dte": MAX_DAYS_TO_EXPIRY,
        },
        date_cols=[c for c in ("date", "exdate", "last_date") if c in select_cols],
    )


def pull_spx_options(db) -> pd.DataFrame:
    """Pull/cache option partitions and return their manifest."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    tables = tables_for_prefix(db, "opprcd")
    print(f"Option price tables selected: {tables}")
    rows = []

    for table in tables:
        start_date, end_date = _table_window(table)
        if pd.Timestamp(start_date) > pd.Timestamp(end_date):
            continue
        path = _partition_path(table, start_date, end_date)
        print(
            f"[options] {OPTION_LIBRARY}.{table}: {start_date} to {end_date}"
        )

        # Full-history OptionMetrics pulls are large. Reuse a completed yearly
        # partition when the exact table/date-range file already exists. The
        # filename encodes the source table and requested window, so changing
        # the sample automatically produces a different cache key. Set
        # P06_FORCE_REPULL=1 to deliberately refresh existing partitions.
        if path.exists() and not FORCE_REPULL:
            try:
                cached_rows = int(pq.ParquetFile(path).metadata.num_rows)
            except Exception:
                cached_rows = 0
            if cached_rows > 0:
                print(f"[options] cache hit: {path} ({cached_rows:,} rows)")
                rows.append(
                    {
                        "table": table,
                        "start_date": start_date,
                        "end_date": end_date,
                        "rows": cached_rows,
                        "path": str(path),
                    }
                )
                continue

        frame = pull_option_partition(db, table, start_date, end_date)
        print(f"[options] {table}: {len(frame):,} rows")
        if frame.empty:
            raise RuntimeError(
                f"SPX option pull returned zero rows from {OPTION_LIBRARY}.{table} "
                f"for {start_date} through {end_date}."
            )
        save_parquet(frame, path)
        rows.append(
            {
                "table": table,
                "start_date": start_date,
                "end_date": end_date,
                "rows": len(frame),
                "path": str(path),
            }
        )

    manifest = pd.DataFrame(rows)
    if manifest.empty:
        raise RuntimeError("No SPX option partitions were produced.")
    MANIFEST_OUT.parent.mkdir(parents=True, exist_ok=True)
    manifest.to_csv(MANIFEST_OUT, index=False)
    return manifest


def pull_spx_underlying(db) -> pd.DataFrame:
    """Pull and combine daily SPX closing index levels."""
    frames = []
    tables = tables_for_prefix(db, "secprd")
    print(f"Underlying tables selected: {tables}")
    for table in tables:
        columns = set(get_table_columns(db, OPTION_LIBRARY, table))
        required = {"secid", "date", "close"}
        if not required.issubset(columns):
            raise RuntimeError(
                f"{OPTION_LIBRARY}.{table} is missing {sorted(required - columns)}"
            )
        start_date, end_date = _table_window(table)
        if pd.Timestamp(start_date) > pd.Timestamp(end_date):
            continue
        sql = f"""
            SELECT secid, date, close
            FROM {OPTION_LIBRARY}.{table}
            WHERE secid = %(secid)s
              AND date BETWEEN %(start_date)s AND %(end_date)s
            ORDER BY date
        """
        frame = db.raw_sql(
            sql,
            params={
                "secid": SPX_SECID,
                "start_date": start_date,
                "end_date": end_date,
            },
            date_cols=["date"],
        )
        print(f"[underlying] {table}: {len(frame):,} rows")
        if not frame.empty:
            frames.append(frame)
    if not frames:
        return pd.DataFrame()
    return (
        pd.concat(frames, ignore_index=True)
        .sort_values("date")
        .drop_duplicates(["secid", "date"], keep="last")
        .reset_index(drop=True)
    )


def load_raw_manifest(data_dir=DATA_DIR) -> pd.DataFrame:
    return pd.read_csv(Path(data_dir) / MANIFEST_OUT.name)


def iter_raw_options(data_dir=DATA_DIR):
    """Yield (manifest row, raw option partition) for the active pull."""
    manifest = load_raw_manifest(data_dir)
    for row in manifest.itertuples(index=False):
        yield row, pd.read_parquet(Path(row.path))


def load_spx_underlying(data_dir=DATA_DIR) -> pd.DataFrame:
    return pd.read_parquet(Path(data_dir) / UNDERLYING_OUT.name)


if __name__ == "__main__":
    print(
        f"Pulling OptionMetrics SPX secid={SPX_SECID}: "
        f"{START_DATE} through {END_DATE}"
    )
    db = connect_wrds()
    try:
        manifest = pull_spx_options(db)
        underlying = pull_spx_underlying(db)
    finally:
        db.close()

    if underlying.empty:
        raise RuntimeError("SPX underlying pull returned zero rows.")
    save_parquet(underlying, UNDERLYING_OUT)
    print(f"Saved raw manifest ({len(manifest)} partitions) -> {MANIFEST_OUT}")
    print(f"Saved {len(underlying):,} underlying rows -> {UNDERLYING_OUT}")