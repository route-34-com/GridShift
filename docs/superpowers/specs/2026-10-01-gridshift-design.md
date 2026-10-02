# GridShift — Design Spec

**Date:** 2026-10-01
**Status:** Approved, implemented

## 1. Purpose

Win a German factory as a pilot client by showing a working system that cuts electricity cost and raises on-site renewable use. It runs on sample data now; each data source is a plug-in, so the client's real data can replace it later without touching the planning logic.

### Success criteria

- Produces an hourly 7-day plan: which flexible machines run when, and battery charge/discharge.
- Shows € and % savings against a naive baseline on the sample factory.
- Sends a daily email plan and alerts.
- Dashboard presentable in a client pitch.
- Swapping in client data means replacing config/CSV files or one source module.

### Out of scope (v1)

- Direct machine control (PLC/SCADA). v1 only recommends.
- Real-time intraday re-planning (phase 2, hybrid approach).
- Editing machines or site settings in the UI (they are read-only in v1).
- Multi-tenant support (one site per installation).

## 15. Addendum (2026-10-02): accounts, audit trail, exports

Patterned on the Jayamurugan Tex ERP access module.

- **Accounts:** email + password (scrypt), cookie sessions (14 days, HttpOnly, SameSite=Lax), first admin created on the server itself, 5 wrong attempts lock for 15 minutes.
- **Roles:** admin (everything), planner (view, re-plan, export), viewer (view, export). The last active admin cannot be demoted, switched off or removed.
- **Invites and resets:** single-use links (invite 7 days, reset 1 hour), token after `#` so it never reaches server logs, forgot-password answer never reveals whether an email has an account, password change emails a notice and signs out other sessions. If SMTP is missing or fails, the admin gets a copyable link.
- **Audit trail:** every sign-in (and failure with reason), sign-out, invite, reset, role/status change with before/after values, removal, planning run with figures, export, and email failure; each with time, user, IP, browser and outcome. Filterable, paged, exportable.
- **Exports:** CSV (UTF-8 with BOM, formula-injection safe) and Excel for the full plan report, daily summary, schedule, hourly data, machines, users and the filtered audit trail. Every download is audited.

## 2. Context

- Market: Germany. Grid price = hourly EPEX day-ahead, published ~12:45 CET for the next day.
- Factory operates 24/7; any hour is allowed.
- On-site solar, wind, and battery.
- Machine types: `always_on`, `daily_quota`, `deadline`.

## 3. Architecture

```
backend/
  sources/      price.py · weather.py · site.py · demand_history.py
  forecast/     renewables.py · demand.py · price_estimate.py
  planner/      model.py · optimizer.py · baseline.py · explain.py
  notify/       email.py · templates/
  api/          main.py · routes/
  store.py      SQLite persistence of runs
  jobs.py       daily planning run
frontend/       React + Vite + shadcn/ui + Recharts
data/sample/    site.yaml · machines.yaml · demand_history.csv · price_history.csv
tests/
```

Rules:
- Each source exposes one function returning a pandas DataFrame indexed by UTC hourly timestamps. Planner and forecasts depend only on that shape.
- Shared types (`Machine`, `Site`, `Battery`, `Plan`) live in `planner/model.py` as pydantic models.
- All times stored in UTC; displayed in Europe/Berlin.
- No code comments; docstrings are one line.

## 4. Configuration

### site.yaml
- `name`, `latitude`, `longitude`, `timezone`
- `solar`: `kwp`, `tilt`, `azimuth`, `performance_ratio`
- `wind`: `rated_kw`, `hub_height_m`, `power_curve` (list of `[wind_ms, kw]`)
- `battery`: `capacity_kwh`, `max_charge_kw`, `max_discharge_kw`, `efficiency`, `min_soc`, `initial_soc`
- `grid`: `max_import_kw`, `fee_eur_per_kwh` (grid fees + levies added on top of spot price), `export_price_eur_per_kwh`
- `email`: `recipients`

### machines.yaml
Each machine: `id`, `name`, `power_kw`, `type`, `min_run_hours` and type fields:
- `always_on`: no extra fields.
- `daily_quota`: `hours_per_day`.
- `deadline`: `total_hours`, `due` (ISO datetime), `earliest_start` (optional).

### Sample factory
3 always-on (compressor, cooling, lighting/HVAC), 3 quota (2 presses, 1 CNC line), 2 deadline (heat-treatment furnace, batch mixer). 500 kWp solar, 1 × 800 kW turbine, 1 MWh / 500 kW battery. Location: industrial area near Stuttgart.

## 5. Data Sources

| Source | Provider | Fallback |
|---|---|---|
| Day-ahead price | Energy-Charts API (`/price?bzn=DE-LU`) | Price estimate, flagged `estimate` |
| Weather (7 days hourly) | Open-Meteo: shortwave/direct/diffuse radiation, wind speed 100 m, temperature, cloud cover | Last stored forecast + warning |
| Demand history | `demand_history.csv` (hourly kW) | Required; fail fast if missing |
| Price history | `price_history.csv` (hourly €/MWh with weather features) | Required for estimator training |

## 6. Forecasts

All hourly over 168 hours from the next midnight (Europe/Berlin).

- **Solar kW** = `kwp × (POA irradiance / 1000) × performance_ratio × temperature derate`. POA via simple tilt/azimuth transposition (pvlib).
- **Wind kW** = interpolated power curve at hub-height wind speed (100 m from Open-Meteo, shear-adjusted to hub height).
- **Base demand kW** = mean of `demand_history` by (weekday, hour) over the last 8 weeks. Always-on machines are included in history, so they are not double-counted; the base load stands in for them.
- **Price** = actual for hours published; other hours use a gradient-boosting regressor trained on `price_history.csv` with features: hour, weekday, national wind and solar forecast proxy, temperature. Each value carries `source: actual | estimate`.

## 7. Planner

MILP solved with HiGHS through its own Python API (`highspy`); PuLP 4 replaced its modelling API, so HiGHS is used directly. Horizon T = 168 hourly steps.

### Variables
- `on[m,t]` binary, for each flexible machine m
- `start[m,t]` binary, run-block start indicator
- `charge[t]`, `discharge[t]` ≥ 0 kW; `soc[t]` kWh
- `grid_import[t]`, `grid_export[t]` ≥ 0 kW
- `curtail[t]` ≥ 0 kW

### Constraints
- **Energy balance:** `solar + wind + discharge + grid_import = base_demand + Σ power_m·on[m,t] + charge + grid_export + curtail`.
- **Battery:** `soc[t] = soc[t-1] + η·charge − discharge/η`; `min_soc·cap ≤ soc ≤ cap`; charge/discharge limits; terminal `soc[T] ≥ initial_soc` so value isn't drained into the horizon end.
- **Grid limit:** `grid_import ≤ max_import_kw`.
- **Daily quota:** `Σ_{t in day d} on[m,t] = hours_per_day` per day.
- **Deadline:** `Σ_{earliest_start ≤ t < due} on[m,t] = total_hours`.
- **Min run block:** `start[m,t] ≥ on[m,t] − on[m,t-1]`; `on[m,t+k] ≥ start[m,t]` for k < `min_run_hours`.

### Objective
Minimise `Σ_t (price[t] + fee) · grid_import[t] − export_price · grid_export[t] + ε · curtail[t]`.

### Infeasibility
If unsolved, re-solve with slack on deadline/quota constraints penalised heavily; report which jobs fall short and raise an alert.

### Baseline
Same forecasts. Flexible machines run as early as allowed (quota from 06:00, deadline from earliest start). Battery charges only from surplus renewables and discharges when demand exceeds renewables. Savings = baseline cost − optimizer cost.

### Explanations
For each scheduled block, `explain.py` produces one line, e.g. `"Ran 02:00–05:00: avg €48/MWh vs day avg €112/MWh"` or `"Ran 11:00–14:00: covered 80% by solar surplus"`.

## 8. Daily Run (`jobs.py`)

1. ~13:30 Europe/Berlin: fetch prices and weather.
2. Build forecasts.
3. Solve optimizer and baseline.
4. Store run in SQLite (`runs`, `hourly`, `blocks`).
5. Compare day-1 plan with yesterday's day-2 preview.
6. Send email.

Triggered by the OS scheduler or `python -m backend.jobs`; the API also exposes `POST /runs` to trigger manually.

## 9. Notifications

- **Daily plan email** (HTML): tomorrow's machine blocks, battery plan, expected cost and savings, renewable share, outlook notes for days 2–7 (e.g. "Thu: low wind + cloud → deadline jobs moved earlier").
- **Alerts** (banner at the top of the daily email; subject prefixed with the alert count):
  - Deadline or quota cannot be met.
  - Day-1 plan differs from yesterday's preview by > 20% of flexible energy.
  - Price or weather source fell back.
- SMTP settings via `.env`.

## 10. API

| Method | Path | Returns |
|---|---|---|
| GET | `/runs/latest` | Run summary: cost, baseline cost, savings, renewable share, CO₂ avoided |
| GET | `/runs/latest/hourly` | 168 rows: price, price source, solar, wind, demand, import, export, soc |
| GET | `/runs/latest/blocks` | Machine blocks with explanation |
| GET | `/config` | Site and machines |
| POST | `/runs` | Trigger a new run |

CO₂ avoided uses a constant German grid factor (configurable, default 0.38 kg/kWh) × renewable kWh consumed on site.

## 11. Dashboard

Shared components: `StatCard`, `ChartCard`, `TimeSeriesChart`, `ScheduleGantt`, `PageLayout`, `SourceBadge`.

- **Overview:** stat cards (weekly savings €/%, renewable share, CO₂ avoided, next run time); price vs renewables chart.
- **Forecast:** 7-day timeline: price (actual vs estimate styled differently), solar, wind, demand, battery SoC.
- **Schedule:** Gantt of machine blocks by day; hover shows explanation.
- **Config:** read-only tables of site and machines.

Light and dark mode; responsive down to tablet width.

## 12. Error Handling

| Failure | Behaviour |
|---|---|
| Price API down/empty | All hours use estimate; alert email notes it |
| Weather API down | Use last stored forecast shifted to horizon; if none, abort run with alert |
| Solver infeasible | Slack re-solve; alert lists shortfalls |
| Solver timeout (60 s) | Use best feasible solution; note optimality gap |
| SMTP failure | Log error; run still stored and visible in dashboard |

## 13. Testing

- **Unit:** solar/wind conversion, demand profile, price estimator shape, config loading/validation.
- **Planner invariants:** energy balance holds every hour, SoC within bounds, quotas met per day, deadlines met, min run blocks respected, grid limit respected.
- **Scenarios:** sunny week → flexible load concentrates midday; dark windless week → load shifts to night/cheap hours and battery charges off-peak; infeasible deadline → slack + alert.
- **Savings:** optimizer cost ≤ baseline cost on all scenarios.
- **API:** endpoint responses match schemas using a fixture run.
- Sources mocked in tests; no network calls.

## 14. Client Data Needed (pitch ask)

- Machine list: power, run requirements, flexibility.
- Electricity contract: spot-indexed or fixed, grid fees, peak-demand charges.
- 12 months of 15-minute or hourly meter data.
- PV, wind and battery specifications.
- Who receives plans and alerts.
