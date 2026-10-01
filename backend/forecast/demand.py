"""Forecast the factory base load from its history."""

import pandas as pd

from backend.planner.model import LOCAL_TZ


def base_demand(history: pd.Series, index: pd.DatetimeIndex, weeks: int = 8) -> pd.Series:
    """Return base load in kW as the weekday-hour mean of recent history."""
    recent = history[history.index >= history.index.max() - pd.Timedelta(weeks=weeks)]
    local = recent.index.tz_convert(LOCAL_TZ)
    profile = recent.groupby([local.weekday, local.hour]).mean()
    by_hour = recent.groupby(local.hour).mean()
    target = index.tz_convert(LOCAL_TZ)
    values = [profile.get((d, h), by_hour.get(h, recent.mean())) for d, h in zip(target.weekday, target.hour)]
    return pd.Series(values, index=index, name="demand_kw", dtype="float64")
