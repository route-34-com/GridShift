# GridShift Implementation Plan

> Executed natively in one session at the user's request (end-to-end build, report at the end).

**Goal:** Working pilot of GridShift: forecasts, MILP planner, SQLite store, email, FastAPI, React dashboard.

**Architecture:** Python package `backend` with pluggable `sources`, pure `forecast` functions, `planner` (optimizer + baseline + explain + metrics), `pipeline` orchestrating a run with fallbacks, `store` persisting runs as JSON, `api` exposing them. React + Vite + Tailwind + shadcn-style components + Recharts dashboard consumes `/api`.

**Tech Stack:** Python 3.13, FastAPI, pydantic v2, pandas, scikit-learn, PuLP + HiGHS (highspy), httpx, Jinja2, pytest; React 18, TypeScript, Vite, Tailwind v4, Radix, Recharts.

**Spec:** `docs/superpowers/specs/2026-10-01-gridshift-design.md`

## Global Constraints

- No code comments; docstrings one line.
- Human-style commit messages, no AI attribution.
- All timestamps UTC internally; display Europe/Berlin.
- Horizon: 168 hourly steps from next local midnight (DST days have 23/25 hours; days grouped by local date).
- Tests never hit the network.

## Review Focus

- DST transition inside horizon: daily quotas grouped by local date, horizon length stays 168 hours.
- Negative day-ahead prices: planner may import and charge; no simultaneous charge/discharge or import/export.
- Deadline already overdue, due beyond horizon, or longer than its window: skip with warning, pro-rate, or slack + alert.
- Price published for only part of the horizon (run before 13:00): remaining hours estimated and flagged.
- Invalid site/machine config (missing fields, quota > 24 h, both/neither due fields): clear validation error naming the machine.

---

### Task 1: Scaffold + config models
Files: `pyproject.toml`, `requirements.txt`, `.env.example`, `backend/planner/model.py`, `backend/sources/site.py`, `data/sample/site.yaml`, `data/sample/machines.yaml`, `tests/test_site.py`.
Produces: `Site`, `Machine`, `load_site(path) -> Site`, `load_machines(path) -> list[Machine]`.

### Task 2: Sample data generators
Files: `scripts/make_demand_history.py`, `scripts/make_price_history.py`, `data/sample/demand_history.csv`, `data/sample/price_history.csv`.

### Task 3: Sources
Files: `backend/sources/http.py`, `price.py`, `weather.py`, `demand_history.py`, tests with mocked httpx transport.
Produces: `fetch_day_ahead(start, end) -> pd.Series`, `fetch_site_weather(site, index) -> pd.DataFrame`, `fetch_national_weather(index) -> pd.DataFrame`, `load_demand_history(path) -> pd.Series`.

### Task 4: Forecasts
Files: `backend/forecast/horizon.py`, `renewables.py`, `demand.py`, `price_estimate.py`, tests.
Produces: `horizon_index(now) -> DatetimeIndex`, `solar_kw`, `wind_kw`, `base_demand`, `price_forecast(actual, features, history) -> DataFrame[price, source]`.

### Task 5: Planner
Files: `backend/planner/inputs.py`, `requirements.py`, `optimizer.py`, `baseline.py`, `metrics.py`, `explain.py`, tests for invariants + scenarios + DST + negative prices + infeasible.
Produces: `PlanInputs`, `optimize(inputs, site, machines) -> PlanResult`, `baseline(inputs, site, machines) -> PlanResult`, `summarize(...)`, `explain_blocks(...)`.

### Task 6: Pipeline, store, email, jobs
Files: `backend/store.py`, `backend/pipeline.py`, `backend/notify/email.py`, `backend/notify/templates/*.html`, `backend/jobs.py`, `backend/settings.py`, tests with fake sources.

### Task 7: API
Files: `backend/api/main.py`, `backend/api/routes/*.py`, tests with TestClient.

### Task 8: Dashboard
Files: `frontend/**`. Pages: Overview, Forecast, Schedule, Email, Config. Shared: `StatCard`, `ChartCard`, `TimeSeriesChart`, `ScheduleGantt`, `PageLayout`, `SourceBadge`, `EmptyState`, `ErrorState`. Loading/empty/error states; light/dark.

### Task 9: End-to-end verification
Real run against live APIs, dashboard checked in browser via Playwright, README updated, push.
