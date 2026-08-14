"""Clean SPX OptionMetrics quotes for the Martin (2025) replication.

The cleaning rules are designed to reproduce the documented SVIX construction
as closely as practical while preserving modern SPX contract-series metadata.
In particular, AM- and PM-settled contracts sharing the same calendar expiry
are never collapsed into one surface.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from martin_spec import MAX_DTE, MIN_DTE
from option_surface import add_surface_key, quarterly_mask
from pull_optionmetrics import iter_raw_options, load_spx_underlying
from settings import config

DATA_DIR = Path(config("DATA_DIR"))
CLEAN_DIR = DATA_DIR / "optionmetrics_clean"
MANIFEST_OUT = DATA_DIR / "optionmetrics_spx_clean_manifest.csv"
DIAGNOSTICS_OUT = DATA_DIR / "optionmetrics_cleaning_diagnostics.csv"


def infer_strike_divisor(options: pd.DataFrame, underlying: pd.DataFrame) -> float:
    """Infer the OptionMetrics strike-price storage multiplier."""
    merged = options[["date", "strike_price"]].merge(
        underlying[["date", "close"]], on="date", how="inner"
    )
    merged["strike_price"] = pd.to_numeric(merged["strike_price"], errors="coerce")
    merged["close"] = pd.to_numeric(merged["close"], errors="coerce")
    merged = merged.dropna()
    if merged.empty:
        raise RuntimeError("Cannot infer strike scaling: no option/spot overlap.")
    ratio = np.nanmedian(merged["strike_price"] / merged["close"])
    return 1000.0 if ratio > 100.0 else 1.0


def _exact_and_contract_dedup(q: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    before = len(q)
    q = q.drop_duplicates().copy()
    if "optionid" in q.columns:
        oid = pd.to_numeric(q["optionid"], errors="coerce")
        with_id = q.loc[oid.notna()].copy()
        without_id = q.loc[oid.isna()].copy()
        if not with_id.empty:
            with_id = with_id.sort_values(["date", "optionid"]).drop_duplicates(
                ["date", "optionid"], keep="last"
            )
        q = pd.concat([with_id, without_id], ignore_index=True, sort=False)
    return q, before - len(q)


def clean_option_partition(
    options: pd.DataFrame,
    underlying: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Clean one raw option partition and return diagnostics."""
    raw_n = len(options)
    q = options.copy()
    u = underlying.copy()

    q["date"] = pd.to_datetime(q["date"], errors="coerce")
    q["exdate"] = pd.to_datetime(q["exdate"], errors="coerce")
    u["date"] = pd.to_datetime(u["date"], errors="coerce")

    for col in ("strike_price", "best_bid", "best_offer"):
        q[col] = pd.to_numeric(q[col], errors="coerce")
    u["close"] = pd.to_numeric(u["close"], errors="coerce")

    q["cp_flag"] = q["cp_flag"].astype("string").str.upper().str.strip()
    required = [
        "date",
        "exdate",
        "cp_flag",
        "strike_price",
        "best_bid",
        "best_offer",
    ]
    q = q.dropna(subset=required)
    after_missing = len(q)

    # Martin's appendix deletes replicated entries before quote construction.
    q, duplicate_rows_removed = _exact_and_contract_dedup(q)

    # Valid calls/puts, positive strike, nonnegative bid, and non-crossed
    # market. Zero bids are deliberately retained until the call/put lower-mid
    # selection step: Martin selects the lower-mid side first and then deletes
    # the selected option when its bid is zero.
    q = q[q["cp_flag"].isin(["C", "P"])]
    q = q[q["strike_price"] > 0]
    zero_bid_quotes = int((q["best_bid"] <= 0).sum())
    q = q[q["best_bid"] >= 0]
    q = q[q["best_offer"] >= q["best_bid"]]
    after_quote_filters = len(q)

    divisor = infer_strike_divisor(q, u)
    q["strike"] = q["strike_price"] / divisor
    q["mid"] = (q["best_bid"] + q["best_offer"]) / 2.0
    q["spread"] = q["best_offer"] - q["best_bid"]
    q["days_to_expiry"] = (q["exdate"] - q["date"]).dt.days

    q = q[
        (q["days_to_expiry"] >= MIN_DTE)
        & (q["days_to_expiry"] < MAX_DTE)
        & np.isfinite(q["mid"])
        & (q["mid"] > 0)
    ]
    after_maturity_filters = len(q)

    qmask = quarterly_mask(q)
    quarterly_removed = int(qmask.sum())
    q = q.loc[~qmask].copy()

    spot = (
        u[["date", "close"]]
        .dropna()
        .drop_duplicates("date", keep="last")
        .rename(columns={"close": "spot"})
    )
    q = q.merge(spot, on="date", how="left", validate="many_to_one")
    q = q.dropna(subset=["spot"])
    q = q[q["spot"] > 0]

    # Preserve modern contract-series distinctions (especially AM vs PM).
    q = add_surface_key(q)

    # Count date/expiration combinations for which multiple coherent surfaces
    # remain after cleaning.  Forward construction will select one surface;
    # it will never merge these quotes together.
    surface_counts = q.groupby(["date", "exdate"])["surface_key"].nunique()
    multi_surface_groups = int((surface_counts > 1).sum())

    first = [
        "date",
        "exdate",
        "surface_key",
        "days_to_expiry",
        "cp_flag",
        "strike",
        "best_bid",
        "best_offer",
        "mid",
        "spread",
        "spot",
    ]
    q = q[first + [c for c in q.columns if c not in first]]
    q = q.sort_values(
        ["date", "exdate", "surface_key", "strike", "cp_flag"]
    ).reset_index(drop=True)

    diagnostics = {
        "raw_rows": raw_n,
        "after_missing_filter": after_missing,
        "duplicate_rows_removed": duplicate_rows_removed,
        "zero_bid_quotes_retained_for_lower_mid_step": zero_bid_quotes,
        "after_quote_filters": after_quote_filters,
        "after_maturity_filters": after_maturity_filters,
        "quarterly_removed": quarterly_removed,
        "final_rows": len(q),
        "strike_divisor": divisor,
        "first_date": q["date"].min() if not q.empty else pd.NaT,
        "last_date": q["date"].max() if not q.empty else pd.NaT,
        "unique_dates": q["date"].nunique(),
        "multi_surface_date_expiry_groups": multi_surface_groups,
    }
    return q, diagnostics


def _clean_path(raw_path: str | Path) -> Path:
    name = Path(raw_path).stem.replace("spx_", "spx_clean_", 1) + ".parquet"
    return CLEAN_DIR / name


def clean_all_partitions() -> tuple[pd.DataFrame, pd.DataFrame]:
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    underlying = load_spx_underlying()
    manifest_rows = []
    diag_rows = []

    for raw_meta, raw in iter_raw_options():
        clean, diag = clean_option_partition(raw, underlying)
        if clean.empty:
            raise RuntimeError(f"Cleaning produced zero rows for {raw_meta.path}")
        out = _clean_path(raw_meta.path)
        clean.to_parquet(out, index=False)
        manifest_rows.append(
            {
                "source_table": raw_meta.table,
                "start_date": raw_meta.start_date,
                "end_date": raw_meta.end_date,
                "raw_rows": raw_meta.rows,
                "clean_rows": len(clean),
                "path": str(out),
            }
        )
        diag_rows.append(
            {
                "source_table": raw_meta.table,
                "partition_start": raw_meta.start_date,
                "partition_end": raw_meta.end_date,
                **diag,
            }
        )
        print(
            f"[clean] {raw_meta.start_date} to {raw_meta.end_date}: "
            f"{len(raw):,} -> {len(clean):,} rows"
        )

    manifest = pd.DataFrame(manifest_rows)
    diagnostics = pd.DataFrame(diag_rows)
    manifest.to_csv(MANIFEST_OUT, index=False)
    diagnostics.to_csv(DIAGNOSTICS_OUT, index=False)
    return manifest, diagnostics


def load_clean_manifest(data_dir=DATA_DIR) -> pd.DataFrame:
    return pd.read_csv(Path(data_dir) / MANIFEST_OUT.name)


def iter_clean_options(data_dir=DATA_DIR):
    manifest = load_clean_manifest(data_dir)
    for row in manifest.itertuples(index=False):
        yield row, pd.read_parquet(Path(row.path))


def load_clean_options(data_dir=DATA_DIR) -> pd.DataFrame:
    """Convenience loader; use iter_clean_options for the full 30-year panel."""
    return pd.concat(
        [frame for _, frame in iter_clean_options(data_dir)], ignore_index=True
    )


if __name__ == "__main__":
    manifest, diagnostics = clean_all_partitions()
    print(f"Saved clean manifest ({len(manifest)} partitions) -> {MANIFEST_OUT}")
    print(f"Saved cleaning diagnostics -> {DIAGNOSTICS_OUT}")
    print(diagnostics.to_string(index=False))
