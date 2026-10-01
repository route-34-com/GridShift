"""Download real day-ahead prices and national weather to train the price estimator."""

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from backend.sources.price import fetch_day_ahead
from backend.sources.weather import fetch_national_weather

OUT = Path(__file__).resolve().parents[1] / "data" / "sample" / "price_history.csv"


def main() -> None:
    """Write the price history CSV."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=180)
    args = parser.parse_args()
    end = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    start = end - timedelta(days=args.days)
    prices = fetch_day_ahead(start, end)
    weather = fetch_national_weather(start, end, history=True)
    frame = weather.join(prices, how="inner").dropna()
    frame.index.name = "timestamp"
    frame.round(3).to_csv(OUT, date_format="%Y-%m-%dT%H:%M:%SZ")
    print(f"Wrote {len(frame)} rows to {OUT}")


if __name__ == "__main__":
    main()
