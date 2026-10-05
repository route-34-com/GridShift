"""German day-ahead electricity prices from Energy-Charts, with aWATTar as a backup."""

from datetime import datetime, timedelta

import httpx
import pandas as pd

from backend.sources.http import SourceError, get_json

URL = "https://api.energy-charts.info/price"
AWATTAR_URL = "https://api.awattar.de/v1/marketdata"


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
    return _hourly(pd.Series(prices, index=pd.to_datetime(stamps, unit="s", utc=True), dtype="float64"), start, end)


def fetch_day_ahead_awattar(start: datetime, end: datetime, client: httpx.Client | None = None) -> pd.Series:
    """Return hourly DE-LU day-ahead prices in EUR/MWh for [start, end) in UTC from aWATTar."""
    params = {"start": int(start.timestamp() * 1000), "end": int(end.timestamp() * 1000)}
    data = get_json(AWATTAR_URL, params, client)
    rows = data.get("data") if isinstance(data, dict) else None
    if not isinstance(rows, list) or any(not isinstance(r, dict) or "start_timestamp" not in r or "marketprice" not in r for r in rows):
        raise SourceError("aWATTar price response is missing start_timestamp or marketprice")
    stamps = pd.to_datetime([r["start_timestamp"] for r in rows], unit="ms", utc=True)
    return _hourly(pd.Series([r["marketprice"] for r in rows], index=stamps, dtype="float64"), start, end)


def _hourly(raw: pd.Series, start: datetime, end: datetime) -> pd.Series:
    """Average 15-minute or hourly prices to hours inside [start, end)."""
    raw = raw.dropna()
    if raw.empty:
        return pd.Series(dtype="float64", index=pd.DatetimeIndex([], tz="UTC"), name="price")
    hourly = raw.resample("h").mean().dropna()
    window = hourly[(hourly.index >= pd.Timestamp(start)) & (hourly.index < pd.Timestamp(end))]
    return window.rename("price")
