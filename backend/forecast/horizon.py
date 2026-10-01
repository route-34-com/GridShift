"""Planning horizon helpers."""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from backend.planner.model import LOCAL_TZ

HORIZON_HOURS = 168


def horizon_index(now: datetime, hours: int = HORIZON_HOURS) -> pd.DatetimeIndex:
    """Return hourly UTC timestamps starting at the next local midnight."""
    local = pd.Timestamp(now).tz_convert(LOCAL_TZ) if pd.Timestamp(now).tzinfo else pd.Timestamp(now, tz=LOCAL_TZ)
    midnight = (local.tz_localize(None).normalize() + timedelta(days=1)).tz_localize(LOCAL_TZ)
    return pd.date_range(midnight.tz_convert("UTC"), periods=hours, freq="h")


def local_dates(index: pd.DatetimeIndex) -> np.ndarray:
    """Return the local calendar date of each timestamp."""
    return np.array(index.tz_convert(LOCAL_TZ).date)
