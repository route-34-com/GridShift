"""Download real day-ahead prices and national weather to train the price estimator."""

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from backend.sources.price import fetch_day_ahead
from backend.sources.weather import fetch_national_weather

DATA = Path(__file__).resolve().parents[1] / "data"
OUTS = [DATA / "sample" / "price_history.csv", DATA / "holcim" / "price_history.csv"]


def main() -> None:
    """Write the price history CSV."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=365)
    args = parser.parse_args()
    end = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    start = end - timedelta(days=args.days)
    prices = fetch_day_ahead(start, end).resample("h").mean()
    weather = fetch_national_weather(start, end, history=True)
    frame = weather.join(prices, how="inner").dropna()
    frame.index.name = "timestamp"
    for out in OUTS:
        frame.round(3).to_csv(out, date_format="%Y-%m-%dT%H:%M:%SZ")
        print(f"Wrote {len(frame)} rows to {out}")


if __name__ == "__main__":
    main()
