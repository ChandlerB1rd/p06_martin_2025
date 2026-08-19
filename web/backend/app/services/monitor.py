"""SVIX Monitor computations: latest print, regime, history, Table 1."""

from __future__ import annotations

import functools

import numpy as np
import pandas as pd
from fastapi import HTTPException

from app.adapters import svix_daily_long, table1_rows

# Named market events used as history markers.
CRISIS_WINDOWS = [
    {
        "id": "gfc",
        "label": "GFC",
        "start": "2008-09-01",
        "end": "2009-03-31",
        "kind": "crisis",
    },
    {
        "id": "covid",
        "label": "COVID",
        "start": "2020-02-15",
        "end": "2020-04-30",
        "kind": "crisis",
    },
    {
        "id": "banks_2023",
        "label": "Regional banks 2023",
        "start": "2023-03-08",
        "end": "2023-03-24",
        "kind": "post2022",
    },
    {
        "id": "aug_2024",
        "label": "Aug 2024 vol spike",
        "start": "2024-08-01",
        "end": "2024-08-08",
        "kind": "post2022",
    },
    {
        "id": "tariffs_2025",
        "label": "Apr 2025 tariffs",
        "start": "2025-04-02",
        "end": "2025-04-21",
        "kind": "post2022",
    },
]

# The UI prefixes these with the capitalized regime name, so they read as
# continuations rather than repeating it.
REGIME_LABELS = {
    "calm": "option-implied premium below the historical median.",
    "elevated": "above the median but short of crisis territory.",
    "stress": "top-decile SVIX; crisis-like expected excess returns.",
}


@functools.lru_cache(maxsize=1)
def _cm() -> pd.DataFrame:
    return svix_daily_long()


def _percentile(series: pd.Series, value: float) -> float | None:
    s = series.dropna()
    if len(s) == 0 or not np.isfinite(value):
        return None
    return float((s <= value).mean() * 100.0)


def _regime_from_pct(pct: float | None) -> str:
    if pct is None:
        return "elevated"
    if pct < 50:
        return "calm"
    if pct < 90:
        return "elevated"
    return "stress"


def _opt(value) -> float | None:
    return float(value) if pd.notna(value) else None


def snapshot(horizon_m: int = 1) -> dict:
    cm = _cm()
    horizons = sorted(cm["horizon_m"].unique().tolist())
    by_h = {}
    for h in horizons:
        g = cm.loc[cm["horizon_m"] == h].sort_values("date")
        if g.empty:
            continue
        last = g.iloc[-1]
        ep = _opt(last["ep_ann"])
        av = _opt(last["ann_vol"])
        # Regime is scored on annualized SVIX vol percentiles (full sample).
        pct_full = _percentile(g["ann_vol"], av) if av is not None else None
        five_y = g.loc[g["date"] >= (last["date"] - pd.DateOffset(years=5))]
        pct_5y = _percentile(five_y["ann_vol"], av) if av is not None else None
        regime = _regime_from_pct(pct_full)
        by_h[int(h)] = {
            "date": last["date"].strftime("%Y-%m-%d"),
            "horizon_m": int(h),
            "svix2": float(last["svix2"]),
            "svix": _opt(last["svix"]),
            "ep_ann": ep,
            "ep_ann_pct": ep * 100.0 if ep is not None else None,
            "ann_vol": av,
            "Rf": _opt(last["Rf"]),
            "percentile_full": pct_full,
            "percentile_5y": pct_5y,
            "regime": regime,
            "regime_blurb": REGIME_LABELS[regime],
            "quantiles_ann_vol": {
                "p50": float(g["ann_vol"].quantile(0.5)),
                "p75": float(g["ann_vol"].quantile(0.75)),
                "p90": float(g["ann_vol"].quantile(0.9)),
            },
        }

    primary = by_h.get(horizon_m) or next(iter(by_h.values()), None)
    if primary is None:
        raise HTTPException(status_code=503, detail="No SVIX daily rows available.")

    # Regime timeline for the primary horizon, downsampled for the strip.
    g1 = cm.loc[cm["horizon_m"] == primary["horizon_m"]].sort_values("date")
    p50 = float(g1["ann_vol"].quantile(0.5))
    p90 = float(g1["ann_vol"].quantile(0.9))
    step = max(1, len(g1) // 400)
    timeline = []
    for r in g1.iloc[::step].itertuples(index=False):
        av = _opt(r.ann_vol)
        if av is None:
            continue
        if av < p50:
            reg = "calm"
        elif av < p90:
            reg = "elevated"
        else:
            reg = "stress"
        timeline.append(
            {"date": r.date.strftime("%Y-%m-%d"), "regime": reg, "ann_vol": av}
        )

    return {
        "as_of": primary["date"],
        "horizon_m": primary["horizon_m"],
        "primary": primary,
        "by_horizon": by_h,
        "regime_timeline": timeline,
        "events": CRISIS_WINDOWS,
        "sample_start": g1["date"].min().strftime("%Y-%m-%d"),
        "sample_end": g1["date"].max().strftime("%Y-%m-%d"),
    }


def history(horizon_m: int | None = None, metric: str = "ep_ann") -> dict:
    cm = _cm().sort_values("date")
    if horizon_m is not None:
        cm = cm.loc[cm["horizon_m"] == horizon_m]

    frames = []
    for _, g in cm.groupby("horizon_m"):
        g = g.sort_values("date")
        step = max(1, len(g) // 2500)
        frames.append(g.iloc[::step])
    slim = pd.concat(frames, ignore_index=True) if frames else cm

    rows = []
    for r in slim.itertuples(index=False):
        ep = _opt(r.ep_ann)
        rows.append(
            {
                "date": r.date.strftime("%Y-%m-%d"),
                "horizon_m": int(r.horizon_m),
                "svix2": float(r.svix2),
                "ep_ann": ep,
                "ep_ann_pct": ep * 100.0 if ep is not None else None,
                "ann_vol": _opt(r.ann_vol),
            }
        )
    return {
        "metric": metric,
        "n": len(rows),
        "rows": rows,
        "events": CRISIS_WINDOWS,
    }


def table1() -> dict:
    rows, samples, labels = table1_rows()
    if not rows:
        raise HTTPException(status_code=503, detail="No Table 1 results available.")

    # Best horizon per sample by R².
    winners: dict[str, dict] = {}
    for row in rows:
        s = row["sample"]
        r2 = row["r2_pct"]
        if r2 is None:
            continue
        if s not in winners or r2 > winners[s]["r2_pct"]:
            winners[s] = row

    return {
        "rows": rows,
        "samples": samples,
        "winners": winners,
        "labels": labels,
    }
