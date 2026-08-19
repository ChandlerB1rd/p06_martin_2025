"""Path setup and cached loaders for the SVIX Monitor API.

Every loader reads an artifact the doit pipeline already produces. Nothing here
pulls from WRDS or recomputes SVIX; a missing artifact is reported as a 503 that
names the file and the task that builds it.
"""

from __future__ import annotations

import functools
import sys
from pathlib import Path

import pandas as pd
from fastapi import HTTPException

# Repo layout: web/backend/app/deps.py -> parents[3] = repo root
REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from martin_spec import (  # noqa: E402
    ANNUALIZATION_FACTOR,
    HORIZON_DAYS,
    HORIZONS,
)
from settings import config  # noqa: E402

DATA_DIR = Path(config("DATA_DIR"))
OUTPUT_DIR = Path(config("OUTPUT_DIR"))

# "1m" -> 1, ... The API speaks integer months; the pipeline speaks labels.
HORIZON_MONTHS = {"1m": 1, "3m": 3, "6m": 6, "12m": 12}
MONTHS_TO_LABEL = {v: k for k, v in HORIZON_MONTHS.items()}

__all__ = [
    "ANNUALIZATION_FACTOR",
    "DATA_DIR",
    "HORIZONS",
    "HORIZON_DAYS",
    "HORIZON_MONTHS",
    "MONTHS_TO_LABEL",
    "OUTPUT_DIR",
    "REPO_ROOT",
    "load_future_returns",
    "load_published_comparison",
    "load_svix_daily_wide",
    "load_table1_csv",
    "require_path",
]

# Artifact -> the doit task that writes it, for actionable 503s.
_BUILT_BY = {
    "svix_daily.parquet": "doit svix",
    "future_sp500_returns.parquet": "doit future_returns",
    "table1_replication.csv": "doit table1",
    "table1_updated.csv": "doit table1",
    "table1_post2022.csv": "doit table1",
    "table1_published_comparison.csv": "doit table1",
}


def require_path(path: Path) -> Path:
    if not path.exists():
        task = _BUILT_BY.get(path.name, "doit")
        raise HTTPException(
            status_code=503,
            detail=f"Missing {path.name}. Run the project pipeline first (`{task}`).",
        )
    return path


@functools.lru_cache(maxsize=1)
def load_svix_daily_wide() -> pd.DataFrame:
    """Constant-maturity SVIX, one row per date with per-horizon columns."""
    df = pd.read_parquet(require_path(DATA_DIR / "svix_daily.parquet"))
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


@functools.lru_cache(maxsize=1)
def load_future_returns() -> pd.DataFrame:
    """Realized forward returns; the Monitor only needs its gross risk-free legs."""
    df = pd.read_parquet(require_path(DATA_DIR / "future_sp500_returns.parquet"))
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


@functools.lru_cache(maxsize=8)
def load_table1_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(require_path(OUTPUT_DIR / name))


@functools.lru_cache(maxsize=1)
def load_published_comparison() -> pd.DataFrame:
    return load_table1_csv("table1_published_comparison.csv")
