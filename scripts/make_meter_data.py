"""Generate a synthetic 15-minute grid import profile (RLM load profile) for the sample factory."""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parents[1] / "data" / "sample" / "meter_data.csv"
RECORD_AT = "2026-02-16 07:15"
RECORD_KW = 1248.0


def build(start: str, end: str, seed: int) -> pd.DataFrame:
    """Return a frame with timestamp and import_kw columns, including one start-up spike as the yearly record."""
    rng = np.random.default_rng(seed)
    local = pd.date_range(pd.Timestamp(start, tz="Europe/Berlin"), pd.Timestamp(end, tz="Europe/Berlin"), freq="15min")
    hour = (local.hour + local.minute / 60).to_numpy()
    workday = local.weekday.to_numpy() < 5
    shift = workday & (hour >= 6) & (hour < 22)
    day_of_year = local.dayofyear.to_numpy()
    season = 0.5 - 0.5 * np.cos((day_of_year - 15) / 365 * 2 * np.pi)
    sun = np.clip(np.sin((hour - 6) / 14 * np.pi), 0, None) * (300 + 700 * season) * rng.uniform(0.3, 1.0, len(local))
    machines = np.where(shift, rng.uniform(450, 750, len(local)), 0)
    startup = workday & (hour >= 6) & (hour < 8)
    base = 330 + rng.normal(0, 12, len(local))
    load = np.clip(base + machines + startup * rng.uniform(0, 180, len(local)) - sun, 80, RECORD_KW - 60)
    load[local == pd.Timestamp(RECORD_AT, tz="Europe/Berlin")] = RECORD_KW
    return pd.DataFrame({"timestamp": local.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ"), "import_kw": load.round(1)})


def main() -> None:
    """Write the meter data CSV."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2026-01-01 00:00")
    parser.add_argument("--end", default="2026-09-30 23:45")
    parser.add_argument("--seed", type=int, default=11)
    args = parser.parse_args()
    build(args.start, args.end, args.seed).to_csv(OUT, index=False)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
