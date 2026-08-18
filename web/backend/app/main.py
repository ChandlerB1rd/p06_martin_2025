"""SVIX Monitor API.

Read-only viewer over the artifacts the doit pipeline writes to `_data/` and
`_output/`. No WRDS traffic happens inside a request.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import monitor

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="SVIX Monitor",
    description=(
        "Option-implied equity premium from Martin (2025) SVIX, served over the "
        "OptionMetrics/CRSP caches built by the p06 replication pipeline."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(monitor.router)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}
