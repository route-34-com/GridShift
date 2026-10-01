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

   🧮 **Optimizer** that finds the lowest-cost schedule while meeting every quota and deadline

   📧 **Daily email plan and alerts** plus a web dashboard showing the schedule and savings

## Features

- Hourly 7-day planning horizon, re-planned every day after day-ahead prices are published
- Three machine types: `always_on`, `daily_quota` and `deadline` jobs, with minimum run blocks
- Battery charge/discharge plan, with no simultaneous charging and discharging
- Surplus solar and wind detection; flexible load moves onto clean energy
- Savings measured against a "run every machine as early as possible" baseline
- One-line explanation for every scheduled block ("avg €58/MWh vs day avg €141/MWh")
- Dashboard: overview, forecast charts, machine schedule (Gantt), email preview, site config; light and dark mode
- Swappable data sources: sample data now, the client's data later

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
2. **Weather**: Open-Meteo tilted irradiance and 100 m wind speed at the site, converted to kW with a PV temperature model and the turbine power curve.
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

Copy `.env.example` to `.env` in the project root. Every setting is optional:

```env
GRIDSHIFT_DATA_DIR=data/sample
GRIDSHIFT_DB_PATH=data/gridshift.db
GRIDSHIFT_SOLVER_TIME_LIMIT=60

SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your_email_here
SMTP_PASSWORD=your_password_here
SMTP_FROM=gridshift@example.com
SMTP_STARTTLS=true
```

If `SMTP_HOST` is empty, emails are not sent. You can still preview them in the dashboard.

**Important:** Never commit your `.env` file. It is already listed in `.gitignore`.

### 3. Site and Machines

Describe the factory in the data folder (`data/sample/` by default):

- `site.yaml`: location, solar, wind turbine power curve, battery, grid limits and fees, email recipients
- `machines.yaml`: each machine's power, type and rules:
  - `always_on`: runs 24/7; part of the base load
  - `daily_quota`: `hours_per_day`, `min_run_hours`
  - `deadline`: `total_hours` plus `due` (date/time, Berlin time) or `due_in_hours`; optional `earliest_start` or `start_in_hours`
- `demand_history.csv`: hourly base load (`timestamp,load_kw`), at least one week
- `price_history.csv`: hourly prices with national weather, used to train the price estimator

To use a client's data, point `GRIDSHIFT_DATA_DIR` at a folder with the same four files. Sample history can be regenerated with:
```bash
python -m scripts.make_demand_history
python -m scripts.make_price_history
```

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

3. Open `http://127.0.0.1:8000` and click **Create first plan** (about 10 seconds).

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
- **Run failed: config not found**: check `GRIDSHIFT_DATA_DIR` points at a folder with `site.yaml` and `machines.yaml`
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
│   ├── pipeline.py         # One planning run with fallbacks and alerts
│   ├── jobs.py             # Daily job entry point
│   ├── store.py            # SQLite persistence
│   └── settings.py         # Environment settings
├── frontend/
│   └── src/
│       ├── components/     # Layout, cards, charts, schedule Gantt, state views
│       ├── pages/          # Overview, Forecast, Schedule, Email, Site
│       ├── hooks/          # Run context, async loader, theme
│       └── lib/            # API client, types, formatters
├── data/sample/            # Sample site, machines, demand and price history
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
