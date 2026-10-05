"""Generate the Holcim sample: hourly base-load history and a 15-minute grid meter profile for a cement plant.

Illustrative numbers only, sized like a 1.5 Mt/year cement works; not Holcim's real data.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parents[1] / "data" / "holcim"
BASE_KW = 11_150  # kiln line, coal mill, clinker transport, utilities
MILLS_KW = (4200, 4500, 3800, 1100)
RECORD_AT = "2026-02-10 07:30"
RECORD_KW = 26_180.0


def base_load(local: pd.DatetimeIndex, rng: np.random.Generator) -> np.ndarray:
    """Always-on load: steady kiln with small swings, lighter utilities at weekends, short kiln stops."""
    weekend = local.weekday.to_numpy() >= 5
    load = BASE_KW + rng.normal(0, 180, len(local)) - weekend * 250
    hours = (local.hour + local.minute / 60).to_numpy()
    load += 120 * np.sin((hours - 14) / 24 * 2 * np.pi)  # cooling fans work harder in the afternoon
    stops = rng.random(len(local)) < 0.0015
    load[np.convolve(stops, np.ones(6), mode="same") > 0] -= 6500  # brief kiln upsets drop the fans and drive
    return load


def history(end: str, weeks: int, seed: int) -> pd.DataFrame:
    """Hourly base load for the weeks before the plan."""
    rng = np.random.default_rng(seed)
    local = pd.date_range(end=pd.Timestamp(end, tz="Europe/Berlin"), periods=weeks * 7 * 24, freq="h")
    return pd.DataFrame({"timestamp": local.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ"), "load_kw": base_load(local, rng).round(1)})


def meter(start: str, end: str, seed: int) -> pd.DataFrame:
    """15-minute grid import: base load plus mills (mostly at night and weekends) minus solar and wind."""
    rng = np.random.default_rng(seed)
    local = pd.date_range(pd.Timestamp(start, tz="Europe/Berlin"), pd.Timestamp(end, tz="Europe/Berlin"), freq="15min")
    hours = (local.hour + local.minute / 60).to_numpy()
    weekend = local.weekday.to_numpy() >= 5
    cheap = (hours < 6) | (hours >= 22) | weekend
    load = base_load(local, rng)
    for kw in MILLS_KW:
        chance = np.where(cheap, 0.92, 0.45)
        load += kw * (rng.random(len(local)) < chance)
    season = 0.5 - 0.5 * np.cos((local.dayofyear.to_numpy() - 15) / 365 * 2 * np.pi)
    sun = np.clip(np.sin((hours - 6) / 14 * np.pi), 0, None) * (1500 + 3500 * season) * rng.uniform(0.2, 1.0, len(local))
    wind = 4200 * np.clip(rng.gamma(2.0, 0.22, len(local)), 0, 1)
    imported = np.clip(load - sun - wind, 2000, RECORD_KW - 400)
    imported[local == pd.Timestamp(RECORD_AT, tz="Europe/Berlin")] = RECORD_KW
    return pd.DataFrame({"timestamp": local.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ"), "import_kw": imported.round(1)})


def main() -> None:
    """Write demand_history.csv and meter_data.csv into data/holcim."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history-end", default="2026-10-04 23:00")
    parser.add_argument("--meter-start", default="2026-01-01 00:00")
    parser.add_argument("--meter-end", default="2026-10-04 23:45")
    parser.add_argument("--seed", type=int, default=34)
    args = parser.parse_args()
    history(args.history_end, 12, args.seed).to_csv(OUT / "demand_history.csv", index=False)
    meter(args.meter_start, args.meter_end, args.seed + 1).to_csv(OUT / "meter_data.csv", index=False)
    print(f"Wrote {OUT / 'demand_history.csv'} and {OUT / 'meter_data.csv'}")


if __name__ == "__main__":
    main()
