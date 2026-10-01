"""Generate a synthetic hourly base-load history for the sample factory."""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parents[1] / "data" / "sample" / "demand_history.csv"


def build(end: str, weeks: int, seed: int) -> pd.DataFrame:
    """Return a base-load frame with timestamp and load_kw columns."""
    rng = np.random.default_rng(seed)
    local = pd.date_range(end=pd.Timestamp(end, tz="Europe/Berlin"), periods=weeks * 7 * 24, freq="h")
    hour = local.hour.to_numpy()
    weekday = local.weekday.to_numpy()
    workday = weekday < 5
    daylight = np.clip(np.sin((hour - 6) / 14 * np.pi), 0, None)
    compressor = 75 + 15 * workday + rng.normal(0, 4, len(local))
    cooling = 110 + 35 * daylight + rng.normal(0, 6, len(local))
    hvac = 45 + np.where(workday, 85, 30) * ((hour >= 6) & (hour < 20)) + rng.normal(0, 5, len(local))
    load = np.clip(compressor + cooling + hvac, 120, None).round(1)
    return pd.DataFrame({"timestamp": local.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ"), "load_kw": load})


def main() -> None:
    """Write the demand history CSV."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--end", default="2026-09-30 23:00")
    parser.add_argument("--weeks", type=int, default=12)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    build(args.end, args.weeks, args.seed).to_csv(OUT, index=False)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
