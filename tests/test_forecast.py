from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from backend.forecast.demand import base_demand
from backend.forecast.horizon import horizon_index
from backend.forecast.price_estimate import PriceEstimator, load_price_history, price_forecast
from backend.forecast.renewables import solar_kw, wind_kw
from backend.planner.model import Solar, Wind
from backend.sources.demand_history import load_demand_history
from backend.sources.site import ConfigError

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "sample"


def test_horizon_starts_at_next_local_midnight():
    index = horizon_index(datetime(2026, 7, 6, 21, 30, tzinfo=timezone.utc))
    assert index[0] == pd.Timestamp("2026-07-06T22:00Z")
    assert len(index) == 168


def test_horizon_from_late_evening_local_time():
    index = horizon_index(datetime(2026, 7, 6, 22, 30, tzinfo=timezone.utc))
    assert index[0].tz_convert("Europe/Berlin").date().isoformat() == "2026-07-08"


def test_horizon_across_dst_end_starts_at_midnight():
    index = horizon_index(datetime(2026, 10, 24, 12, tzinfo=timezone.utc))
    assert index[0].tz_convert("Europe/Berlin").hour == 0
    assert index[0] == pd.Timestamp("2026-10-24T22:00Z")


def weather(irradiance, wind, temperature=20.0):
    index = pd.date_range("2026-07-01", periods=len(irradiance), freq="h", tz="UTC")
    return pd.DataFrame({"irradiance": irradiance, "wind_100m": wind, "temperature": temperature}, index=index)


def test_solar_scales_with_irradiance_and_caps_at_kwp():
    out = solar_kw(weather([0, 500, 1000, 2000], [0] * 4, 10.0), Solar(kwp=100, performance_ratio=1))
    assert out.iloc[0] == 0
    assert 45 < out.iloc[1] < 55
    assert out.iloc[3] <= 100


def test_solar_handles_negative_and_missing_irradiance():
    out = solar_kw(weather([-5, np.nan], [0, 0]), Solar(kwp=100))
    assert (out == 0).all()


def test_wind_follows_power_curve_and_cut_out():
    turbine = Wind(rated_kw=800, hub_height_m=100, power_curve=[(3, 0), (12, 800), (25, 800), (25.1, 0)])
    out = wind_kw(weather([0] * 4, [2, 7.5, 15, 30]), turbine)
    assert out.iloc[0] == 0
    assert 350 < out.iloc[1] < 450
    assert out.iloc[2] == 800
    assert out.iloc[3] == 0


def test_demand_uses_weekday_hour_profile():
    history = load_demand_history(SAMPLE / "demand_history.csv")
    index = horizon_index(datetime(2026, 10, 1, 12, tzinfo=timezone.utc))
    forecast = base_demand(history, index)
    local = index.tz_convert("Europe/Berlin")
    weekday_noon = forecast[(local.weekday < 5) & (local.hour == 12)].mean()
    sunday_3am = forecast[(local.weekday == 6) & (local.hour == 3)].mean()
    assert weekday_noon > sunday_3am
    assert forecast.notna().all()


def test_demand_history_rejects_bad_files(tmp_path):
    path = tmp_path / "d.csv"
    path.write_text("time,kw\n1,2\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="timestamp and load_kw"):
        load_demand_history(path)
    path.write_text("timestamp,load_kw\n2026-01-01T00:00Z,5\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="one week"):
        load_demand_history(path)


def test_demand_history_skips_bad_rows(tmp_path):
    index = pd.date_range("2026-01-01", periods=200, freq="h", tz="UTC")
    frame = pd.DataFrame({"timestamp": index.strftime("%Y-%m-%dT%H:%MZ"), "load_kw": ["100"] * len(index)}, dtype=object)
    frame.loc[5, "load_kw"] = "oops"
    frame.loc[6, "load_kw"] = -20
    frame.loc[7, "timestamp"] = "not a date"
    path = tmp_path / "d.csv"
    frame.to_csv(path, index=False)
    series = load_demand_history(path)
    assert (series >= 0).all() and series.notna().all()


@pytest.fixture(scope="module")
def estimator():
    return PriceEstimator(load_price_history(SAMPLE / "price_history.csv"))


def test_price_forecast_keeps_actuals_and_flags_estimates(estimator):
    index = horizon_index(datetime(2026, 10, 1, 12, tzinfo=timezone.utc))
    actual = pd.Series(99.0, index=index[:24])
    national = pd.DataFrame({"wind": 6.0, "solar": 200.0, "temperature": 15.0}, index=index)
    frame = price_forecast(index, actual, estimator, national)
    assert (frame.price.iloc[:24] == 99).all()
    assert (frame.source.iloc[:24] == "actual").all()
    assert (frame.source.iloc[24:] == "estimate").all()
    assert frame.price.notna().all()


def test_windy_hours_estimated_cheaper(estimator):
    index = horizon_index(datetime(2026, 10, 1, 12, tzinfo=timezone.utc))
    calm = pd.DataFrame({"wind": 2.0, "solar": 0.0, "temperature": 12.0}, index=index)
    windy = calm.assign(wind=11.0)
    assert estimator.predict(index, windy).mean() < estimator.predict(index, calm).mean()


def test_price_forecast_without_any_data_uses_profile(estimator):
    index = horizon_index(datetime(2026, 10, 1, 12, tzinfo=timezone.utc))
    frame = price_forecast(index, None, estimator, None)
    assert frame.price.notna().all()
    assert (frame.source == "estimate").all()
