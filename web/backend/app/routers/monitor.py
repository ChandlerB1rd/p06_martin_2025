"""SVIX Monitor API — latest print, history, Table 1."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.services import monitor as mon

router = APIRouter(prefix="/api/monitor", tags=["monitor"])


@router.get("/snapshot")
def snapshot(
    horizon_m: int = Query(1, description="Primary horizon for the hero and regime"),
) -> dict:
    return mon.snapshot(horizon_m=horizon_m)


@router.get("/history")
def history(
    horizon_m: int | None = Query(None),
    metric: str = Query("ep_ann"),
) -> dict:
    return mon.history(horizon_m=horizon_m, metric=metric)


@router.get("/table1")
def table1() -> dict:
    return mon.table1()
