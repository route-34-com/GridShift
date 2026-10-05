"""Hourly weather forecasts from Open-Meteo."""

from datetime import datetime

import httpx
import pandas as pd

from backend.planner.model import Site
from backend.sources.http import SourceError, get_json

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
HISTORY_URL = "https://historical-forecast-api.open-meteo.com/v1/forecast"

NATIONAL_POINTS = [
    (54.3, 8.6),
    (53.55, 9.99),
    (52.52, 13.40),
    (51.34, 12.37),
    (50.11, 8.68),
    (48.14, 11.58),
]


def _frame(block: dict, fields: dict[str, str]) -> pd.DataFrame:
    hourly = block.get("hourly") if isinstance(block, dict) else None
    if not hourly or "time" not in hourly:
        raise SourceError("Open-Meteo response is missing hourly data")
    missing = [f for f in fields if f not in hourly]
    if missing:
        raise SourceError(f"Open-Meteo response is missing {', '.join(missing)}")
    index = pd.to_datetime(hourly["time"], utc=True)
    frame = pd.DataFrame({name: pd.to_numeric(pd.Series(hourly[f]), errors="coerce").to_numpy() for f, name in fields.items()}, index=index)
    return frame.interpolate(limit_direction="both")


def _window(frame: pd.DataFrame, start: datetime, end: datetime) -> pd.DataFrame:
    index = pd.date_range(pd.Timestamp(start), pd.Timestamp(end), freq="h", inclusive="left")
    window = frame.reindex(index)
    if window.isna().all(axis=None):
        raise SourceError("Open-Meteo returned no data for the requested window")
    return window.interpolate(limit_direction="both")


def _dates(start: datetime, end: datetime) -> dict:
    return {"start_date": start.date().isoformat(), "end_date": end.date().isoformat(), "timezone": "GMT"}


def fetch_site_weather(site: Site, start: datetime, end: datetime, client: httpx.Client | None = None) -> pd.DataFrame:
    """Return hourly tilted irradiance, 100 m wind speed, temperature and cloud cover at the site."""
    fields = {"global_tilted_irradiance": "irradiance", "wind_speed_100m": "wind_100m", "temperature_2m": "temperature", "cloud_cover": "cloud_cover"}
    params = {
        "latitude": site.latitude,
        "longitude": site.longitude,
        "hourly": ",".join(fields),
        "tilt": site.solar.tilt,
        "azimuth": site.solar.azimuth,
        "wind_speed_unit": "ms",
        **_dates(start, end),
    }
    return _window(_frame(get_json(FORECAST_URL, params, client), fields), start, end)


def fetch_national_weather(start: datetime, end: datetime, history: bool = False, client: httpx.Client | None = None) -> pd.DataFrame:
    """Return Germany-wide mean wind, solar radiation and temperature used to estimate prices."""
    fields = {"wind_speed_100m": "wind", "shortwave_radiation": "solar", "temperature_2m": "temperature"}
    params = {
        "latitude": ",".join(str(p[0]) for p in NATIONAL_POINTS),
        "longitude": ",".join(str(p[1]) for p in NATIONAL_POINTS),
        "hourly": ",".join(fields),
        "wind_speed_unit": "ms",
        **_dates(start, end),
    }
    data = get_json(HISTORY_URL if history else FORECAST_URL, params, client)
    blocks = data if isinstance(data, list) else [data]
    frames = [_frame(b, fields) for b in blocks]
    mean = sum(frames) / len(frames)
    return _window(mean, start, end)
