"""German day-ahead electricity prices from Energy-Charts, with aWATTar as a backup."""

from datetime import datetime, timedelta

import httpx
import numpy as np
import pandas as pd

from backend.forecast.horizon import horizon_end
from backend.sources.http import SourceError, get_json

URL = "https://api.energy-charts.info/price"
AWATTAR_URL = "https://api.awattar.de/v1/marketdata"


def fetch_day_ahead(start: datetime, end: datetime, client: httpx.Client | None = None) -> pd.Series:
    """Return DE-LU day-ahead prices in EUR/MWh for [start, end) in UTC, at the market's own resolution (15 minutes)."""
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
    return _window(pd.Series(prices, index=pd.to_datetime(stamps, unit="s", utc=True), dtype="float64"), start, end)


def fetch_day_ahead_awattar(start: datetime, end: datetime, client: httpx.Client | None = None) -> pd.Series:
    """Return DE-LU day-ahead prices in EUR/MWh for [start, end) in UTC from aWATTar, at its own resolution."""
    params = {"start": int(start.timestamp() * 1000), "end": int(end.timestamp() * 1000)}
    data = get_json(AWATTAR_URL, params, client)
    rows = data.get("data") if isinstance(data, dict) else None
    if not isinstance(rows, list) or any(not isinstance(r, dict) or "start_timestamp" not in r or "marketprice" not in r for r in rows):
        raise SourceError("aWATTar price response is missing start_timestamp or marketprice")
    stamps = pd.to_datetime([r["start_timestamp"] for r in rows], unit="ms", utc=True)
    return _window(pd.Series([r["marketprice"] for r in rows], index=stamps, dtype="float64"), start, end)


def _window(raw: pd.Series, start: datetime, end: datetime) -> pd.Series:
    """Keep the prices that start inside [start, end)."""
    raw = raw.dropna().sort_index()
    raw = raw[~raw.index.duplicated(keep="last")]
    window = raw[(raw.index >= pd.Timestamp(start)) & (raw.index < pd.Timestamp(end))]
    return window.astype("float64").rename("price")


def to_steps(raw: pd.Series | None, index: pd.DatetimeIndex) -> pd.Series:
    """Return the average price inside each planning step; a 15-minute step uses its hour's price when only hourly prices exist."""
    out = pd.Series(np.nan, index=index, name="price")
    if raw is None or raw.empty or len(index) == 0:
        return out
    edges = np.append(index.as_unit("ns").asi8, horizon_end(index).as_unit("ns").value)
    position = np.searchsorted(edges, raw.index.as_unit("ns").asi8, side="right") - 1
    inside = (position >= 0) & (position < len(index))
    stepped = raw[inside].groupby(position[inside]).mean()
    out.iloc[stepped.index.to_numpy()] = stepped.to_numpy()
    hourly = raw.resample("h").mean()
    by_hour = pd.Series(hourly.reindex(index.floor("h")).to_numpy(), index=index)
    return out.fillna(by_hour).rename("price")
