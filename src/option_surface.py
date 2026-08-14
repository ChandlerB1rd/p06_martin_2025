"""Helpers for SPX option surfaces and Martin/CBOE strike discretization."""

from __future__ import annotations

import numpy as np
import pandas as pd

# These fields describe economically distinct expiration series.  Do NOT use
# root/suffix here: in pre-2010 OptionMetrics data they are contract-symbol
# components that can vary by strike and call/put side.  Including them in a
# date/expiration surface key fragments one valid chain into one-row "surfaces"
# and destroys put-call pairs.
SURFACE_METADATA = (
    "am_settlement",
    "ss_flag",
    "contract_size",
    "expiry_indicator",
)


def add_surface_key(df: pd.DataFrame) -> pd.DataFrame:
    """Keep economically distinct expiration series (notably AM vs PM) apart.

    Root and suffix are intentionally excluded.  They are contract-level symbol
    components in historical OptionMetrics data, not expiration-surface IDs.
    """
    out = df.copy()
    parts = []
    for col in SURFACE_METADATA:
        if col in out.columns:
            s = out[col].astype("string").fillna("").str.strip()
        else:
            s = pd.Series("", index=out.index, dtype="string")
        parts.append(col + "=" + s)
    key = parts[0]
    for part in parts[1:]:
        key = key + "|" + part
    out["surface_key"] = key
    return out


def quarterly_mask(df: pd.DataFrame) -> pd.Series:
    """Flag rows explicitly identified as Quarterly options."""
    mask = pd.Series(False, index=df.index)
    if "expiry_indicator" in df.columns:
        s = df["expiry_indicator"].astype("string").fillna("").str.upper().str.strip()
        mask |= s.eq("Q") | s.str.startswith("QTR") | s.str.contains("QUART", regex=False)
    if "root" in df.columns:
        root = df["root"].astype("string").fillna("").str.upper().str.strip()
        mask |= root.str.fullmatch(r"SPXQ.*", na=False)
    if "suffix" in df.columns:
        suffix = df["suffix"].astype("string").fillna("").str.upper().str.strip()
        mask |= suffix.eq("Q") | suffix.str.startswith("QTR")
    return mask


def delta_k_weights(strikes: np.ndarray) -> np.ndarray:
    """CBOE/Martin discrete-strike weights Delta K_i."""
    k = np.asarray(strikes, dtype=float)
    if len(k) < 2:
        return np.full(len(k), np.nan)
    if np.any(np.diff(k) <= 0):
        raise ValueError("Strikes must be strictly increasing and unique.")
    w = np.empty(len(k), dtype=float)
    w[0] = k[1] - k[0]
    w[-1] = k[-1] - k[-2]
    if len(k) > 2:
        w[1:-1] = (k[2:] - k[:-2]) / 2.0
    return w


def lower_mid_surface(options: pd.DataFrame, boundary: float) -> pd.DataFrame:
    """Construct Martin's one-option-per-strike integration surface.

    Martin (2017) first selects the call or put with the lower midpoint at each
    strike and then deletes the selected option if its closing bid is zero.
    This ordering matters: a zero-bid OTM option is not replaced by the more
    expensive ITM side.  When only one side is present, retain it only if it is
    the OTM side relative to the supplied boundary and has a positive bid.
    """
    cols = ["strike", "cp_flag", "mid"]
    has_bid = "best_bid" in options.columns
    if has_bid:
        cols.append("best_bid")
    q = options[cols].dropna(subset=["strike", "cp_flag", "mid"]).copy()
    if q.empty:
        return pd.DataFrame(
            columns=["strike", "mid", "selected_cp", "selected_bid", "delta_k"]
        )

    mid = q.pivot_table(index="strike", columns="cp_flag", values="mid", aggfunc="min")
    if has_bid:
        # Pick the bid associated with the minimum midpoint quote for each side.
        q2 = q.sort_values("mid").drop_duplicates(["strike", "cp_flag"], keep="first")
        bid = q2.pivot(index="strike", columns="cp_flag", values="best_bid")
    else:
        bid = pd.DataFrame(index=mid.index)

    rows = []
    for strike, r in mid.sort_index().iterrows():
        c = r.get("C", np.nan)
        p = r.get("P", np.nan)

        # Pandas nullable dtypes can return ``pd.NA`` here.  In particular,
        # ``np.isfinite(pd.NA)`` also returns ``pd.NA`` and Python cannot use
        # that value in an ``if`` statement ("boolean value of NA is
        # ambiguous").  Convert only genuinely present scalar values to
        # floats before applying the finite check.
        def _is_finite_scalar(value) -> bool:
            if pd.isna(value):
                return False
            try:
                return bool(np.isfinite(float(value)))
            except (TypeError, ValueError):
                return False

        c_ok = _is_finite_scalar(c)
        p_ok = _is_finite_scalar(p)
        c_bid = float(bid.loc[strike, "C"]) if has_bid and "C" in bid.columns and strike in bid.index and pd.notna(bid.loc[strike, "C"]) else np.inf
        p_bid = float(bid.loc[strike, "P"]) if has_bid and "P" in bid.columns and strike in bid.index and pd.notna(bid.loc[strike, "P"]) else np.inf

        if c_ok and p_ok:
            if p <= c:
                price, cp, selected_bid = float(p), "P", p_bid
            else:
                price, cp, selected_bid = float(c), "C", c_bid
            # Exact Martin ordering: delete the selected option if bid == 0.
            if selected_bid <= 0:
                continue
        elif p_ok and strike < boundary and p_bid > 0:
            price, cp, selected_bid = float(p), "P", p_bid
        elif c_ok and strike >= boundary and c_bid > 0:
            price, cp, selected_bid = float(c), "C", c_bid
        else:
            continue
        rows.append(
            {
                "strike": float(strike),
                "mid": price,
                "selected_cp": cp,
                "selected_bid": selected_bid,
            }
        )

    out = pd.DataFrame(rows)
    if out.empty:
        return pd.DataFrame(
            columns=["strike", "mid", "selected_cp", "selected_bid", "delta_k"]
        )
    out = out.sort_values("strike").reset_index(drop=True)
    out["delta_k"] = (
        delta_k_weights(out["strike"].to_numpy()) if len(out) >= 2 else np.nan
    )
    return out


def option_sum(
    options: pd.DataFrame,
    boundary: float,
    strike_power: float = 0.0,
) -> dict[str, float | int]:
    """Compute sum K^p Omega(K) DeltaK, with put/call contributions."""
    surface = lower_mid_surface(options, boundary)
    if len(surface) < 2:
        return {
            "put_sum": np.nan,
            "call_sum": np.nan,
            "total_sum": np.nan,
            "n_options": len(surface),
        }
    weight = np.power(surface["strike"].to_numpy(dtype=float), strike_power)
    contrib = weight * surface["mid"].to_numpy(dtype=float) * surface["delta_k"].to_numpy(dtype=float)
    is_put = surface["strike"].to_numpy(dtype=float) < float(boundary)
    put_sum = float(np.sum(contrib[is_put])) if np.any(is_put) else 0.0
    call_sum = float(np.sum(contrib[~is_put])) if np.any(~is_put) else 0.0
    return {
        "put_sum": put_sum,
        "call_sum": call_sum,
        "total_sum": put_sum + call_sum,
        "n_options": int(len(surface)),
    }
