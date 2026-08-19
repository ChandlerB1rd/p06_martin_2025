# SVIX Monitor

Local web UI for Martin's (2025) SVIX: today's option-implied equity premium,
its regime against the historical distribution, the full 1996-present history,
and the Table 1 forecasting regressions.

- **Backend:** FastAPI (`web/backend`) — read-only over `_data/` and `_output/`
- **Frontend:** Vite + React + TypeScript + Tailwind + Apache ECharts (`web/frontend`)

The app computes nothing new. Every number it shows is read from an artifact the
doit pipeline already writes, so the Monitor cannot drift from the replication.

## Data source

**OptionMetrics and CRSP via WRDS only.** There is no live or delayed market
feed, so the latest print is the last date in `_data/svix_daily.parquet` —
currently **2025-08-29**, the end of the WRDS OptionMetrics extract, not today.

## Prerequisites

1. Pipeline artifacts on disk. From the repo root:

```bash
doit svix future_returns table1
```

That produces the four files the API reads:

| File | Used for |
|------|----------|
| `_data/svix_daily.parquet` | Constant-maturity SVIX at 1/3/6/12m |
| `_data/future_sp500_returns.parquet` | Gross risk-free rate `rf_gross_{h}` |
| `_output/table1_replication.csv`, `table1_updated.csv`, `table1_post2022.csv` | Table 1 samples |
| `_output/table1_published_comparison.csv` | Published Martin (2025) values |

A missing file yields HTTP 503 naming the file and the task that builds it.

2. Python environment with the project requirements plus FastAPI:

```bash
pip install -r requirements.txt
pip install -r web/backend/requirements.txt
```

3. Node.js 20+ for the frontend.

## Run (two terminals)

**API** (port 8000), from the repo root:

```bash
PYTHONPATH=web/backend uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**UI** (port 5173; proxies `/api` to the backend):

```bash
cd web/frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). API docs are at
[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

If port 8000 is already taken, start the API elsewhere and point the dev server
at it:

```bash
PYTHONPATH=web/backend uvicorn app.main:app --port 8010
VITE_API_TARGET=http://127.0.0.1:8010 npm run dev -- --port 5174
```

## Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /api/health` | Liveness check |
| `GET /api/monitor/snapshot?horizon_m=1` | Latest print per horizon, percentiles, regime, regime timeline |
| `GET /api/monitor/history?horizon_m=` | Downsampled full history with crisis event windows |
| `GET /api/monitor/table1` | All four Table 1 samples, published comparison, best horizon per sample |

## Conventions worth knowing

**Annualization.** The hero shows $R_f \cdot \mathrm{SVIX}^2$ scaled by the
pipeline's `ANNUALIZATION_FACTOR` (12 / 4 / 2 / 1 for 1m / 3m / 6m / 12m) from
[`src/martin_spec.py`](../src/martin_spec.py), not by `365/target_days`. That is
the same factor Table 1 applies to both sides of its regressions, so the hero
print and the regression inputs stay on one convention.

**Wide vs long.** `svix_daily.parquet` stores one row per date with a column
block per horizon and carries no risk-free rate.
[`web/backend/app/adapters.py`](backend/app/adapters.py) melts it into
`(date, horizon_m)` rows and joins `rf_gross_{h}` from the future-returns file.

**Regime.** Calm / elevated / stress are the sub-median, sub-90th-percentile,
and top-decile buckets of annualized SVIX volatility over the full sample.

## Notes

- No auth; local development only.
- The only files read are the pipeline caches. No request touches WRDS.
- The brokerage ETF ticker **SVIX** is unrelated to Martin's index.
