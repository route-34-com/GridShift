from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from backend.pipeline import Sources
from backend.settings import ROOT, Settings, Smtp
from backend.sources.http import SourceError
from backend.store import Store

NOW = datetime(2026, 10, 1, 11, 30, tzinfo=timezone.utc)


def hours(start, end):
    return pd.date_range(pd.Timestamp(start), pd.Timestamp(end), freq="h", inclusive="left")


def fake_prices(start, end):
    index = hours(start, end)[:24]
    local = index.tz_convert("Europe/Berlin").hour
    return pd.Series(np.where((local < 6) | (local >= 22), 60.0, 140.0), index=index)


def fake_site_weather(site, start, end):
    index = hours(start, end)
    local = index.tz_convert("Europe/Berlin").hour.to_numpy()
    sun = np.clip(np.sin((local - 6) / 13 * np.pi), 0, None) * 700
    return pd.DataFrame({"irradiance": sun, "wind_100m": 6.0, "temperature": 14.0}, index=index)


def fake_national(start, end):
    return pd.DataFrame({"wind": 6.0, "solar": 150.0, "temperature": 14.0}, index=hours(start, end))


def broken(*args, **kwargs):
    raise SourceError("simulated outage")


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        data_dir=ROOT / "data" / "sample",
        db_path=tmp_path / "test.db",
        solver_time_limit=30,
        smtp=Smtp("", 587, "", "", "gridshift@example.com", True),
    )


@pytest.fixture
def store(settings) -> Store:
    return Store(settings.db_path)


def good_sources() -> Sources:
    return Sources(day_ahead=fake_prices, site_weather=fake_site_weather, national_weather=fake_national)
