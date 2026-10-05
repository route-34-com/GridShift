from datetime import datetime, timezone

import httpx
import pandas as pd
import pytest

from backend.sources.http import SourceError
from backend.sources.price import fetch_day_ahead, fetch_day_ahead_awattar
from backend.sources.weather import NATIONAL_POINTS, fetch_national_weather, fetch_site_weather
from tests.factories import make_site

START = datetime(2026, 10, 1, 22, tzinfo=timezone.utc)
END = datetime(2026, 10, 2, 22, tzinfo=timezone.utc)


def client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def json_client(payload, status=200):
    return client(lambda request: httpx.Response(status, json=payload))


def quarter_hours(start, hours):
    return [int(start.timestamp()) + 900 * i for i in range(hours * 4)]


def test_price_resamples_quarter_hours_to_hourly_mean():
    stamps = quarter_hours(START, 24)
    prices = [float(i % 4) for i in range(len(stamps))]
    series = fetch_day_ahead(START, END, json_client({"unix_seconds": stamps, "price": prices}))
    assert len(series) == 24
    assert (series == 1.5).all()


def test_price_skips_null_values_and_returns_partial_day():
    stamps = quarter_hours(START, 12)
    prices = [None if i < 4 else 50.0 for i in range(len(stamps))]
    series = fetch_day_ahead(START, END, json_client({"unix_seconds": stamps, "price": prices}))
    assert len(series) == 11


def test_price_empty_response_returns_empty_series():
    series = fetch_day_ahead(START, END, json_client({"unix_seconds": [], "price": []}))
    assert series.empty


def test_price_malformed_response_raises():
    with pytest.raises(SourceError, match="missing"):
        fetch_day_ahead(START, END, json_client({"oops": 1}))


def test_awattar_prices_are_hourly_in_window():
    start_ms = int(START.timestamp() * 1000)
    rows = [{"start_timestamp": start_ms + 3_600_000 * i, "end_timestamp": start_ms + 3_600_000 * (i + 1), "marketprice": 50.0 + i, "unit": "Eur/MWh"} for i in range(-2, 26)]
    series = fetch_day_ahead_awattar(START, END, json_client({"object": "list", "data": rows}))
    assert len(series) == 24 and series.index[0] == pd.Timestamp(START)
    assert series.iloc[0] == 50.0 and series.iloc[-1] == 73.0


def test_awattar_malformed_response_raises():
    with pytest.raises(SourceError):
        fetch_day_ahead_awattar(START, END, json_client({"data": [{"price": 1}]}))


def test_price_http_errors_retry_then_raise():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(503)

    with pytest.raises(SourceError, match="failed after 3 attempts"):
        fetch_day_ahead(START, END, client(handler))
    assert len(calls) == 3


def hourly_block(fields, hours=48, value=5.0):
    times = pd.date_range(START.date(), periods=hours, freq="h").strftime("%Y-%m-%dT%H:%M").tolist()
    return {"hourly": {"time": times, **{f: [value] * hours for f in fields}}}


def test_site_weather_returns_horizon_window():
    payload = hourly_block(["global_tilted_irradiance", "wind_speed_100m", "temperature_2m", "cloud_cover"])
    frame = fetch_site_weather(make_site(), START, END, json_client(payload))
    assert list(frame.columns) == ["irradiance", "wind_100m", "temperature", "cloud_cover"]
    assert len(frame) == 24 and frame.index[0] == pd.Timestamp(START)


def test_site_weather_fills_gaps():
    payload = hourly_block(["global_tilted_irradiance", "wind_speed_100m", "temperature_2m", "cloud_cover"])
    payload["hourly"]["wind_speed_100m"][30] = None
    frame = fetch_site_weather(make_site(), START, END, json_client(payload))
    assert frame.notna().all(axis=None)


def test_site_weather_missing_field_raises():
    with pytest.raises(SourceError, match="missing"):
        fetch_site_weather(make_site(), START, END, json_client(hourly_block(["wind_speed_100m"])))


def test_national_weather_averages_points():
    fields = ["wind_speed_100m", "shortwave_radiation", "temperature_2m"]
    blocks = [hourly_block(fields, value=float(i)) for i in range(len(NATIONAL_POINTS))]
    frame = fetch_national_weather(START, END, client=json_client(blocks))
    assert (frame.wind == sum(range(len(NATIONAL_POINTS))) / len(NATIONAL_POINTS)).all()
