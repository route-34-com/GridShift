"""German day-ahead electricity prices from Energy-Charts."""

from datetime import datetime, timedelta

import httpx
import pandas as pd

from backend.sources.http import SourceError, get_json

URL = "https://api.energy-charts.info/price"


def fetch_day_ahead(start: datetime, end: datetime, client: httpx.Client | None = None) -> pd.Series:
    """Return hourly DE-LU day-ahead prices in EUR/MWh for [start, end) in UTC."""
    params = {
        "bzn": "DE-LU",
        "start": (start - timedelta(days=1)).date().isoformat(),
        "end": (end + timedelta(days=1)).date().isoformat(),
    }
    data = get_json(URL, params, client)
    if not isinstance(data, dict) or "unix_seconds" not in data or "price" not in data:
        raise SourceError("Energy-Charts price response is missing unix_seconds or price")
    stamps, prices = data["unix_seconds"] or [], data["price"] or []
    if len(stamps) != len(prices):
        raise SourceError("Energy-Charts price response has mismatched lengths")
    raw = pd.Series(prices, index=pd.to_datetime(stamps, unit="s", utc=True), dtype="float64").dropna()
    if raw.empty:
        return pd.Series(dtype="float64", index=pd.DatetimeIndex([], tz="UTC"), name="price")
    hourly = raw.resample("h").mean().dropna()
    window = hourly[(hourly.index >= pd.Timestamp(start)) & (hourly.index < pd.Timestamp(end))]
    return window.rename("price")
