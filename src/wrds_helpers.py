"""Shared WRDS helpers for the Martin (2025) replication."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

import pandas as pd
import wrds

from settings import config


def get_wrds_username() -> str | None:
    """Return the configured WRDS username, if one is available."""
    username = os.getenv("WRDS_USERNAME")
    if username:
        return username
    try:
        return config("WRDS_USERNAME")
    except Exception:
        return None


def connect_wrds() -> wrds.Connection:
    """Open a WRDS connection using the project's configured username."""
    username = get_wrds_username()
    if username:
        return wrds.Connection(wrds_username=username)
    return wrds.Connection()


def get_table_columns(
    db: wrds.Connection,
    library: str,
    table: str,
) -> list[str]:
    """Return lowercase column names for one WRDS table."""
    sql = """
        SELECT lower(column_name) AS column_name
        FROM information_schema.columns
        WHERE lower(table_schema) = %(library)s
          AND lower(table_name) = %(table)s
        ORDER BY ordinal_position
    """
    result = db.raw_sql(
        sql,
        params={"library": library.lower(), "table": table.lower()},
    )
    return result["column_name"].tolist()


def find_table_by_columns(
    db: wrds.Connection,
    library: str,
    required_columns: Iterable[str],
    preferred_tables: Iterable[str] = (),
) -> str:
    """Find an accessible table containing all required columns.

    Preferred table names are checked first. If none match, information_schema
    is searched so the code can tolerate WRDS table-name changes.
    """
    required = {c.lower() for c in required_columns}
    available = {t.lower(): t for t in db.list_tables(library=library)}

    for preferred in preferred_tables:
        actual = available.get(preferred.lower())
        if actual is None:
            continue
        columns = set(get_table_columns(db, library, actual))
        if required.issubset(columns):
            return actual

    placeholders = ", ".join([f"%(c{i})s" for i in range(len(required))])
    params = {"library": library.lower()}
    for i, col in enumerate(sorted(required)):
        params[f"c{i}"] = col

    sql = f"""
        SELECT lower(table_name) AS table_name,
               lower(column_name) AS column_name
        FROM information_schema.columns
        WHERE lower(table_schema) = %(library)s
          AND lower(column_name) IN ({placeholders})
    """
    found = db.raw_sql(sql, params=params)

    if not found.empty:
        coverage = found.groupby("table_name")["column_name"].agg(set)
        for table_name, cols in coverage.items():
            if required.issubset(cols):
                return available.get(table_name, table_name)

    raise RuntimeError(
        f"No table in library={library!r} contains required columns "
        f"{sorted(required)!r}. Inspect the WRDS data dictionary and "
        "db.list_tables(library=...)."
    )


def save_parquet(df: pd.DataFrame, path: Path) -> None:
    """Save a DataFrame as Parquet, creating the parent directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
