<h1 align="center">GridShift — Smart Energy Scheduling for Industry</h1>
<br>
<p align="center">
  <img src="https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/HiGHS-1F4E79?style=for-the-badge&logoColor=white" alt="HiGHS">
  <img src="https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" alt="React">
  <img src="https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white" alt="Vite">
  <img src="https://img.shields.io/badge/shadcn%2Fui-000000?style=for-the-badge&logo=shadcnui&logoColor=white" alt="shadcn/ui">
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

- Hourly 7-day planning horizon with rolling daily re-plans
- Three machine types: always-on, daily quota, and deadline jobs
- Surplus solar detection and load shifting onto clean energy
- Savings report against a naive "run when needed" baseline
- Swappable data sources — sample data now, client data later
- Graceful fallbacks when price or weather APIs are unavailable

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

- [Python 3.11+](https://www.python.org/downloads/)
- [Node.js 20+](https://nodejs.org/) (for the dashboard)

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
```

## Configuration

### 1. Data Sources

GridShift uses free, key-less public APIs:

- [Energy-Charts](https://api.energy-charts.info/) — German day-ahead electricity prices
- [Open-Meteo](https://open-meteo.com/) — weather forecasts for solar and wind output

### 2. Environment Configuration

Copy `.env.example` to `.env` in the project root and fill in your email settings:

```env
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your_email_here
SMTP_PASSWORD=your_password_here
ALERT_RECIPIENTS=plant.manager@example.com
```

**Important:** Never commit your `.env` file. It is already listed in `.gitignore`.

### 3. Site and Machines

Describe the factory in `data/sample/`:

- `site.yaml` — location, solar kWp, wind turbine, battery, grid connection limit
- `machines.yaml` — each machine's power and type (`always_on`, `daily_quota`, `deadline`)
- `demand_history.csv` — past hourly base load used for demand forecasting

Replace these sample files with client data when available.

## Usage

### Running the Backend

1. Make sure your virtual environment is activated:
   ```bash
   myenv\Scripts\activate
   ```

2. Start the API server:
   ```bash
   uvicorn backend.api.main:app --reload
   ```

3. Run a plan manually:
   ```bash
   python -m backend.jobs
   ```

### Running the Dashboard

```bash
cd frontend
npm run dev
```

Open `http://localhost:5173` to see the 7-day schedule, forecasts, and savings.

### Running Tests

```bash
pytest
```

## Deactivating the Environment

When you're done working with the project, deactivate the virtual environment:

```bash
deactivate
```

## Troubleshooting

- Make sure your virtual environment is activated before running any scripts
- Check that all dependencies are installed with `pip list`
- Verify your internet connection for the price and weather APIs
- If the price API is down, GridShift falls back to estimated prices and flags them in the email
- If emails are not sent, verify the SMTP settings in your `.env` file

## Project Structure

```
GridShift/
├── backend/
│   ├── sources/            # Price, weather, machine and demand data plug-ins
│   ├── forecast/           # Renewable output, demand and price estimation
│   ├── planner/            # MILP optimizer and baseline schedule
│   ├── notify/             # Daily plan and alert emails
│   ├── api/                # REST endpoints for the dashboard
│   └── jobs.py             # Daily planning run
├── frontend/               # React + Vite + shadcn/ui dashboard
├── data/
│   └── sample/             # Sample site, machines and demand history
├── docs/                   # Design specs and plans
├── tests/                  # Unit and scenario tests
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
