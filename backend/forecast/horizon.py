"""Planning horizon helpers."""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from backend.planner.model import LOCAL_TZ

HORIZON_HOURS = 168
FINE_DAYS = 1
QUARTER = "15min"


def _midnight(now: datetime, days: int) -> pd.Timestamp:
    local = pd.Timestamp(now).tz_convert(LOCAL_TZ) if pd.Timestamp(now).tzinfo else pd.Timestamp(now, tz=LOCAL_TZ)
    return (local.tz_localize(None).normalize() + timedelta(days=days)).tz_localize(LOCAL_TZ).tz_convert("UTC")


def horizon_index(now: datetime, hours: int = HORIZON_HOURS, fine_days: int = FINE_DAYS) -> pd.DatetimeIndex:
    """Return UTC step starts from the next local midnight: 15-minute steps for the first local day(s), hourly after."""
    start = _midnight(now, 1)
    end = start + pd.Timedelta(hours=hours)
    if fine_days <= 0:
        return pd.date_range(start, end, freq="h", inclusive="left")
    split = min(_midnight(now, 1 + fine_days), end)
    fine = pd.date_range(start, split, freq=QUARTER, inclusive="left")
    coarse = pd.date_range(split, end, freq="h", inclusive="left") if split < end else pd.DatetimeIndex([], tz="UTC")
    return fine.append(coarse)


def today_index(now: datetime) -> pd.DatetimeIndex:
    """Return hourly UTC timestamps from today's local midnight up to the planning horizon."""
    return pd.date_range(_midnight(now, 0), _midnight(now, 1), freq="h", inclusive="left")


def step_hours(index: pd.DatetimeIndex) -> np.ndarray:
    """Return the length of each step in hours; the last step is as long as the one before it."""
    if len(index) == 0:
        return np.zeros(0)
    gaps = np.diff(index.as_unit("ns").asi8) / 3.6e12
    return np.append(gaps, gaps[-1] if len(gaps) else 1.0)


def horizon_end(index: pd.DatetimeIndex) -> pd.Timestamp:
    """Return the end of the last step."""
    return index[-1] + pd.Timedelta(hours=float(step_hours(index)[-1]))


def align(frame: pd.DataFrame, index: pd.DatetimeIndex) -> pd.DataFrame:
    """Return hourly values on the planning steps, interpolated in time between the hours."""
    union = frame.index.union(index)
    filled = frame.reindex(union).interpolate(method="time", limit_area="inside")
    return filled.reindex(index)


def local_dates(index: pd.DatetimeIndex) -> np.ndarray:
    """Return the local calendar date of each timestamp."""
    return np.array(index.tz_convert(LOCAL_TZ).date)
