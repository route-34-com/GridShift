<h1 align="center">GridShift — Smart Energy Scheduling for Industry</h1>
<br>
<p align="center">
  <img src="https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/HiGHS-1F4E79?style=for-the-badge&logoColor=white" alt="HiGHS">
  <img src="https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" alt="React">
  <img src="https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white" alt="Vite">
  <img src="https://img.shields.io/badge/Tailwind-0F172A?style=for-the-badge&logo=tailwindcss&logoColor=38BDF8" alt="Tailwind CSS">
  <img src="https://img.shields.io/badge/Recharts-22B5BF?style=for-the-badge&logoColor=white" alt="Recharts">
</p>
<br>

⚡ Cut factory energy costs by running the right machines at the right hour.

GridShift plans when a factory's heavy machines should run, when to charge or discharge the battery, and when to lean on on-site solar and wind — using hourly German day-ahead electricity prices and a 7-day weather outlook.

   💶 **Day-ahead prices** from the German power market to find cheap and expensive hours

   🌤️ **Weather forecasting** to predict solar and wind output for the coming week

   🏭 **Demand forecasting** to predict the factory's own base load hour by hour

   🔋 **Battery strategy** — charge on surplus solar or cheap hours, discharge at peaks

   🏔️ **Peak protection** — keeps grid draw under this year's record so the annual peak charge (Leistungspreis) doesn't go up

   🧮 **Optimizer** that finds the lowest-cost schedule while meeting every quota and deadline

   📧 **Daily email plan and alerts** plus a web dashboard showing the schedule and savings

## Features

- Hourly 7-day planning horizon, re-planned every day after day-ahead prices are published
- Three machine types: `always_on`, `daily_quota` and `deadline` jobs, with minimum run blocks
- Battery charge/discharge plan, with no simultaneous charging and discharging
- Peak charge awareness: a new yearly grid peak is priced at the full annual €/kW rate, so the planner only raises it when that is cheaper than staying under it
- Surplus solar and wind detection; flexible load moves onto clean energy
- Savings measured against a "run every machine as early as possible" baseline
- One-line explanation for every scheduled block ("avg €58/MWh vs day avg €141/MWh")
- Dashboard: overview, forecast charts, machine schedule (Gantt), email preview, site config; light and dark mode
- Swappable data sources: sample data now, the client's data later
- User accounts with roles, email invitations, forgot/reset password and account lockout
- Detailed audit trail: who did what, when, from which IP and browser, with before/after values
- CSV and Excel exports for plans, schedules, hourly data, users and the audit trail

## Users, Roles and Audit Trail

| Role | Can do |
|---|---|
| **Admin** | Everything: plans, re-plan, upload meter data, exports, invite and manage users, audit log |
| **Planner** | See plans, re-plan, upload meter data, export |
| **Viewer** | See plans, export |

- **First start:** open the app on the computer running GridShift and create the admin account.
- **Invite:** *Users → Invite user*. The person gets an email with a single-use link (valid 7 days) to set their password.
- **Forgot password:** *Sign in → Forgot password?* sends a reset link (valid 1 hour). The answer never reveals whether an email has an account.
- **Admin reset:** *Users → ⋯ → Send password reset link*. Role changes, switching an account off and password changes sign that person out everywhere.
- **Safety:** 5 wrong passwords lock that email for 15 minutes; the last active admin can't be demoted, switched off or removed.
- **No email set up?** Invites and reset links are shown to the admin to copy and send.
- **Audit log** (*Admin → Audit log*): sign-ins and failures (with reason), sign-outs, invitations, resets, role and status changes (before → after), removals, planning runs (with savings), exports and email failures. Each entry has time, user, IP address, browser and outcome. Filter by activity, user, outcome, dates or free text, and export the filtered list.

## Exports

Every export is a dated download and is recorded in the audit log.

| Page | Export | Formats |
|---|---|---|
| Overview | Full plan report: PDF with headline figures, daily cost chart, outlook, machines and schedule; Excel with Summary, Daily, Schedule, Machines and Hourly sheets | PDF, Excel |
| Overview | Daily summary, price paid per machine | PDF, Excel, CSV |
| Forecast | Hourly plan and hourly baseline (168 rows, including site weather) | PDF, Excel, CSV |
| Schedule | GridShift schedule and run-as-needed schedule | PDF, Excel, CSV |
| Users | User list | PDF, Excel, CSV |
| Audit log | Matching entries (respects the filters) | PDF, Excel, CSV |

PDFs are landscape A4 with a GridShift header and page numbers. CSV files are UTF-8 with a BOM so Excel shows € and umlauts correctly, and cells starting with `=`, `+`, `-` or `@` are neutralised so a spreadsheet never runs them as formulas.

## Results on Sample Data

Live run on 1 Oct 2026 for the sample factory near Stuttgart (1.5 MWp solar, 800 kW wind, 1 MWh battery, 8 machines):

| | Run-as-needed | GridShift |
|---|---|---|
| Energy cost (7 days) | €18,833 | **€15,128** |
| Savings | | **€3,705 (19.7%)** |
| Heat-treatment furnace, avg price paid | €195/MWh | **€81/MWh** |
| Batch mixer, avg price paid | €191/MWh | **€52/MWh** |

## How It Works

```
Weather forecast (7d) ─┬→ Solar / wind output forecast
                       └→ Price estimate (days 2–7)
Day-ahead price (24h) ──→ Price (actual)
Demand history ─────────→ Factory base load forecast
                          ↓
            Optimizer (machines + battery, 7-day horizon)
                          ↓
          Schedule · Email alerts · Savings report
```

1. **Prices**: published DE-LU day-ahead prices from Energy-Charts for tomorrow. Later days are estimated by a gradient-boosting model trained on 180 days of real prices and Germany-wide wind, solar and temperature.
2. **Weather**: Open-Meteo tilted irradiance and 100 m wind speed at the site, converted to kW with a PV temperature model and the turbine power curve. The Forecast page shows the weather itself: sunlight on the panels (W/m²) with cloud cover, and wind speed at hub height with the turbine's start, full-power and storm shut-off speeds. Every hourly row and the hourly export carry sunlight, cloud cover, wind speed and temperature. Each run also stores today's published prices and weather (best effort, not used for planning) so the Forecast charts start at today's midnight, grey out hours already past and mark the current German time with a "Now" line.
3. **Demand**: base load as the weekday × hour average of the last 8 weeks of meter data.
4. **Optimizer**: a mixed-integer program solved with HiGHS. It minimises grid cost while meeting every quota, deadline, minimum run block, battery limit and grid connection limit.
5. **Output**: run stored in SQLite, daily email sent, dashboard updated.

## Edge Cases Handled

| Situation | Behaviour |
|---|---|
| Run before prices are published (~12:45) | Missing hours estimated and flagged `partial` |
| Price API down | All hours estimated; alert in email and dashboard |
| Weather API down | Last stored forecast reused; run fails cleanly only if none exists |
| Negative prices | Planner pulls load and battery charging into those hours |
| Staying under the yearly peak record is impossible | Peak raised as little as possible; alert shows the extra annual charge |
| No peak record (no meter data, `peak_so_far_kw` not set) | Warning; the week's highest hour is treated as a new yearly peak |
| Meter data unreadable or from last year | Warning; the peak from `site.yaml` is used |
| Bad meter upload (wrong columns, daily readings, not a CSV) | Rejected with a clear message; the previous file is kept |
| DST change inside the week | Quotas counted per local calendar day (23 h / 25 h days) |
| Deadline impossible in its window | Best partial schedule plus a shortfall alert |
| Deadline beyond the horizon | Only the hours that cannot fit later are required this week |
| Deadline already overdue | Skipped with a warning |
| Demand above grid connection | Reported as unmet energy instead of crashing |
| Plan changes a lot vs yesterday's preview | Info alert (> 20% of flexible energy moved) |
| Invalid YAML / unknown fields / duplicate ids | Clear error naming the file and field |
| Two re-plans at once | Second request rejected with 409 |
| SMTP not configured or failing | Run still stored; email status shown in dashboard |

## Installation

### Step 1: Clone the Repository

**Option A: Using VS Code Terminal**
1. Open Visual Studio Code
2. Open a new terminal (Terminal → New Terminal or `` Ctrl+Shift+` ``)
3. Navigate to your desired directory:
   ```bash
   cd path/to/your/desired/folder
   ```
4. Clone the repository:
   ```bash
   git clone https://github.com/route-34-com/GridShift.git
   ```
5. Open the project folder:
   ```bash
   cd GridShift
   ```
6. Open the project in VS Code:
   ```bash
   code .
   ```

**Option B: Using VS Code Git Integration**
1. Open Visual Studio Code
2. Press `Ctrl+Shift+P` (Windows/Linux) or `Cmd+Shift+P` (Mac)
3. Type "Git: Clone" and select it
4. Paste the repository URL: `https://github.com/route-34-com/GridShift.git`
5. Choose a folder location and click "Select Repository Location"
6. Click "Open" when prompted

### Step 2: Install Prerequisites

- [Python 3.11+](https://www.python.org/downloads/) (tested on 3.13)
- [Node.js 20+](https://nodejs.org/) (tested on 22)

Verify the installation:
```bash
python --version
node --version
```

### Step 3: Create Virtual Environment

```bash
python -m venv myenv
```

### Step 4: Activate Virtual Environment

**For Windows:**
```bash
myenv\Scripts\activate
```

**For macOS/Linux:**
```bash
source myenv/bin/activate
```

After activation, you should see something like this in your terminal:
```
(myenv) PS C:\Users\username\path\to\GridShift>
```

### Step 5: Install Dependencies

**Backend:**
```bash
pip install -r requirements.txt
```

**Dashboard:**
```bash
cd frontend
npm install
npm run build
cd ..
```

## Configuration

### 1. Data Sources

GridShift uses free public APIs that need no key:

- [Energy-Charts](https://api.energy-charts.info/): German day-ahead electricity prices (Bundesnetzagentur | SMARD.de, CC BY 4.0)
- [Open-Meteo](https://open-meteo.com/): weather forecasts for solar and wind output

### 2. Environment Configuration

Copy `.env.example` to `.env` in the project root:

```env
GRIDSHIFT_DATA_DIR=data/live
GRIDSHIFT_SAMPLE_DIR=data/holcim
GRIDSHIFT_DB_PATH=data/gridshift.db
GRIDSHIFT_SOLVER_TIME_LIMIT=60
APP_URL=http://127.0.0.1:8000
TRUST_PROXY=false
GRIDSHIFT_ALLOW_SETUP=false

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_TLS=starttls
SMTP_USER=your-account@gmail.com
SMTP_PASSWORD=your-16-letter-app-password
SMTP_FROM=GridShift <your-account@gmail.com>
```

- `GRIDSHIFT_DATA_DIR` holds the company's own site data; `GRIDSHIFT_SAMPLE_DIR` the built-in sample (set `GRIDSHIFT_NO_SAMPLE=true` to remove the sample switch).
- `APP_URL` is the address put into invitation and reset links. Set it to the public address when hosted.
- `SMTP_TLS` is `starttls` (port 587), `ssl` (port 465) or `none`. For Gmail, use an [app password](https://myaccount.google.com/apppasswords).
- `TRUST_PROXY=true` only behind a reverse proxy (nginx), so the real client IP is logged.
- `GRIDSHIFT_REQUIRE_LOGIN` is on by default. Set it to `false` only on a single computer nobody else can reach: the dashboard then opens straight away and every action is logged as a built-in *Local admin*.
- `GRIDSHIFT_ALLOW_SETUP=true` allows creating the first admin from another computer.
- If `SMTP_HOST` is empty, nothing is emailed: the dashboard shows invite and reset links to copy, and the daily plan can still be previewed.
- After changing `.env`, restart the server. Inviting yourself or using *Forgot password?* confirms email works.

**Trying emails without a real mail account:** run the local mail catcher, which saves every email to `data/mail/`:
```bash
python -m scripts.mail_catcher --port 1025
```
and set `SMTP_HOST=127.0.0.1`, `SMTP_PORT=1025`, `SMTP_TLS=none`.

**Important:** Never commit your `.env` file. It is already listed in `.gitignore`.

### 3. Site and Machines

**Sample data vs real data.** The sidebar has a *Sample data* switch (admins only, audit-logged). On, every page, the daily run and meter uploads use the **Holcim sample** in `data/holcim/`: an illustrative cement plant sized like a Holcim works in northern Germany (kiln line about 11 MW always on; raw mill, two cement mills and the quarry crusher about 14 MW that can shift; 6 MWp solar, a 4.2 MW turbine, a 10 MWh battery; peak record 26,180 kW). The figures are made up for demonstrations, not Holcim's real data. Off, GridShift uses the company's own folder (`data/live/` by default) and says so if it isn't set up yet. Each data set keeps its own plans and weather cache; plans made before the switch existed are hidden from both.

**Setting up a company's own site.** Switch *Sample data* off and open *Site & machines*. A checklist shows the three things the planner needs, each with its own form or upload; admins and planners can edit, every change is audit-logged, and the files below are written for you:

1. **Site details**: location, grid connection, fees, peak charge and this year's record, solar, wind and battery.
2. **Machines**: add, edit or delete. *Always on*, *Hours every day* (with the shortest allowed run) or *Job with a deadline* (total hours, due date or hours after the plan starts, optional earliest start).
3. **Load history**: a CSV of at least one week of the hourly always-on load (`timestamp,load_kw`; comma or semicolon separated, decimal comma allowed).

*Start from the Holcim sample* copies the sample's site, machines and load history (and its peak record) as a starting point, never overwriting files that exist. German market price history is shared with the sample, so nothing needs uploading for prices. The sample itself is read-only on this page.

If a peak charge is set but this year's record is unknown, the checklist warns: every kW would count as a new peak, which makes the plan much harder to solve. Should the planner run out of time with peak protection on, it plans again without it and says so in an alert rather than producing no plan.

The same files can also be edited by hand. Describe the factory in the data folder (`data/live/` for real data):

- `site.yaml`: location, solar, wind turbine power curve, battery, grid limits and fees, email recipients
  - `grid.peak_charge_eur_per_kw_year`: the grid operator's annual demand charge (Leistungspreis) in €/kW; `0` turns peak protection off
  - `grid.peak_so_far_kw`: the highest 15-minute grid draw this calendar year from the latest bill. Optional once meter data is uploaded; the planner uses the higher of the two
- `machines.yaml`: each machine's power, type and rules:
  - `always_on`: runs 24/7; part of the base load
  - `daily_quota`: `hours_per_day`, `min_run_hours`
  - `deadline`: `total_hours` plus `due` (date/time, Berlin time) or `due_in_hours`; optional `earliest_start` or `start_in_hours`
- `demand_history.csv`: hourly base load (`timestamp,load_kw`), at least one week
- `price_history.csv`: hourly prices with national weather, used to train the price estimator
- `meter_data.csv` (optional): the site's 15-minute grid import (RLM load profile), usually uploaded from the dashboard's *Site* page. Columns `timestamp` and either `import_kw` (average kW) or `import_kwh` (kWh per interval); comma or semicolon separated, decimal comma allowed, times without a zone read as German time. GridShift takes this year's highest reading as the peak record and shows the peak charge per month (record kW × €/kW per year ÷ 12)

To use a client's data, point `GRIDSHIFT_DATA_DIR` at a folder with the same four files. Sample history can be regenerated with:
```bash
python -m scripts.make_demand_history
python -m scripts.make_price_history
python -m scripts.make_meter_data
python -m scripts.make_holcim_data   # Holcim sample: demand history and meter data
```

`data/sample/` is the small test factory the automated tests use.

## Usage

### Running the App

1. Make sure your virtual environment is activated:
   ```bash
   myenv\Scripts\activate
   ```

2. Start the server (API and dashboard on one port):
   ```bash
   uvicorn backend.api.main:app --port 8000
   ```

3. Open `http://127.0.0.1:8000`, create the admin account, then click **Create first plan** (about 10 seconds).

### Running the Daily Plan

Run one planning cycle from the command line. It stores the run and sends the email:
```bash
python -m backend.jobs
```

Schedule it daily at 13:30 Berlin time, after day-ahead prices are published:

**Windows (Task Scheduler):**
```bash
schtasks /create /tn GridShift /sc daily /st 13:30 /tr "C:\path\to\GridShift\myenv\Scripts\python.exe -m backend.jobs"
```

**macOS/Linux (cron):**
```bash
30 13 * * * cd /path/to/GridShift && myenv/bin/python -m backend.jobs
```

### Dashboard Development

Run the API on port 8000, then start Vite with hot reload (it forwards `/api` to the backend):
```bash
cd frontend
npm run dev
```

Open `http://localhost:5173`.

### Running Tests

```bash
pytest
cd frontend && npm test
```

Tests never call the network: price and weather sources are replaced with fakes.

## API

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Liveness |
| GET | `/api/status` | Run in progress, latest run, last failure |
| GET | `/api/runs` | Recent runs |
| POST | `/api/runs?email=false` | Run the planner now |
| GET | `/api/runs/latest` | Summary, daily breakdown, machines, alerts |
| GET | `/api/runs/latest/hourly` | 168 hourly rows for plan and baseline |
| GET | `/api/runs/latest/blocks` | Machine run blocks with explanations |
| GET | `/api/runs/latest/email` | Daily email as HTML |
| GET | `/api/config` | Site and machine configuration |
| GET/POST | `/api/auth/setup` | First admin status / create first admin |
| POST | `/api/auth/login`, `/api/auth/logout` | Sign in and out |
| GET | `/api/auth/me` | Signed-in user and permissions |
| POST | `/api/auth/forgot-password`, `/api/auth/reset-password` | Password reset by email |
| POST | `/api/auth/invite`, `/api/auth/accept-invite` | Invitation details / activate account |
| PUT/POST | `/api/auth/profile`, `/api/auth/password` | Own name / own password |
| GET/POST | `/api/users`, `/api/users/invite` | List users / invite (admin) |
| PUT/DELETE | `/api/users/{id}` | Change role or status / remove (admin) |
| POST | `/api/users/{id}/resend-invite`, `/api/users/{id}/reset-link` | Links (admin) |
| POST | `/api/users/test-email` | Send a test email (admin) |
| GET | `/api/audit` | Filtered, paged audit trail (admin) |
| GET | `/api/exports/run/{name}?format=pdf\|xlsx\|csv` | `report`, `summary`, `daily`, `schedule`, `baseline-schedule`, `hourly`, `baseline-hourly`, `machines` |
| GET | `/api/exports/users`, `/api/exports/audit` | User list and audit trail (admin) |
| GET | `/api/peak` | This year's peak record, its source, and the peak charge per month and year |
| POST | `/api/meter` | Upload meter data, admin or planner (CSV body, `content-type: text/csv`); returns the new peak record |

Every endpoint except health and the sign-in flow requires a session.

Interactive docs: `http://127.0.0.1:8000/docs`.

## Deactivating the Environment

When you're done working with the project, deactivate the virtual environment:

```bash
deactivate
```

## Troubleshooting

- Make sure your virtual environment is activated before running any scripts
- Check that all dependencies are installed with `pip list`
- Verify your internet connection for the price and weather APIs
- **Blank page at port 8000**: run `npm run build` in `frontend/` so `frontend/dist` exists
- **"No plan yet"**: click **Create first plan**, or run `python -m backend.jobs`
- **Run failed: config not found**: with sample data off, check `GRIDSHIFT_DATA_DIR` points at a folder with `site.yaml` and `machines.yaml`
- **Emails not sent**: check the SMTP settings in `.env`; the status badge on the *Daily email* page shows the reason

## Project Structure

```
GridShift/
├── backend/
│   ├── sources/            # Price, weather, site config and demand data plug-ins
│   ├── forecast/           # Horizon, solar/wind output, base load and price estimation
│   ├── planner/            # Models, requirements, MILP optimizer, baseline, metrics, explanations
│   ├── notify/             # Daily plan email (Jinja2 template + SMTP)
│   ├── api/                # FastAPI app and routes
│   ├── auth/               # Passwords, sessions, lockout, roles
│   ├── services/           # Users, invite/reset tokens, mailer, audit trail, exports
│   ├── database.py         # SQLite connection and schema
│   ├── pipeline.py         # One planning run with fallbacks and alerts
│   ├── jobs.py             # Daily job entry point
│   ├── store.py            # SQLite persistence
│   └── settings.py         # Environment settings
├── frontend/
│   └── src/
│       ├── components/     # Layout, cards, charts, schedule Gantt, state views
│       ├── pages/          # Overview, Forecast, Schedule, Email, Site, Users, Audit, Account, auth/
│       ├── hooks/          # Run context, async loader, theme
│       └── lib/            # API client, types, formatters
├── data/holcim/            # Holcim sample (illustrative cement plant) for the Sample data switch
├── data/sample/            # Small test factory used by the automated tests
├── scripts/                # Sample data generators
├── docs/superpowers/       # Design spec and implementation plan
├── tests/                  # Backend unit, scenario, pipeline and API tests
├── .env.example            # Environment variable template
├── requirements.txt        # Python dependencies
└── README.md               # This documentation
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

In case of any queries, please leave a message or contact me via the email provided in my profile.

<p align="center">
⭐ <strong>Star this repository if you found it helpful!</strong>
</p>
