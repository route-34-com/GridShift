"""Combine published day-ahead prices with weather-based estimates."""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from backend.planner.model import LOCAL_TZ
from backend.sources.site import ConfigError

FEATURES = ["hour", "weekday", "wind", "solar", "temperature"]


def load_price_history(path: Path) -> pd.DataFrame:
    """Load hourly prices with national weather features."""
    if not path.exists():
        raise ConfigError(f"Price history not found: {path}")
    frame = pd.read_csv(path, parse_dates=["timestamp"]).set_index("timestamp")
    missing = {"wind", "solar", "temperature", "price"} - set(frame.columns)
    if missing:
        raise ConfigError(f"{path.name} is missing columns: {', '.join(sorted(missing))}")
    frame.index = pd.to_datetime(frame.index, utc=True)
    frame = frame.dropna()
    if len(frame) < 24 * 14:
        raise ConfigError(f"{path.name} needs at least two weeks of rows")
    return frame


def _features(frame: pd.DataFrame) -> pd.DataFrame:
    local = frame.index.tz_convert(LOCAL_TZ)
    return frame.assign(hour=local.hour, weekday=local.weekday)[FEATURES]


class PriceEstimator:
    """Gradient-boosted price model on hour, weekday and national weather."""

    def __init__(self, history: pd.DataFrame):
        self.low, self.high = np.percentile(history["price"], [1, 99])
        self.model = HistGradientBoostingRegressor(loss="absolute_error", max_iter=300, random_state=0)
        self.model.fit(_features(history), history["price"].clip(self.low, self.high))
        local = history.index.tz_convert(LOCAL_TZ)
        self.profile = history["price"].groupby([local.weekday, local.hour]).median()

    def predict(self, index: pd.DatetimeIndex, national: pd.DataFrame | None) -> pd.Series:
        """Return estimated prices, falling back to the weekday-hour profile without weather."""
        if national is not None and not national.reindex(index).isna().any(axis=None):
            values = self.model.predict(_features(national.reindex(index)))
            return pd.Series(np.clip(values, self.low, self.high), index=index)
        local = index.tz_convert(LOCAL_TZ)
        values = [self.profile.get((d, h), self.profile.median()) for d, h in zip(local.weekday, local.hour)]
        return pd.Series(values, index=index, dtype="float64")


_CACHE: dict[tuple[str, float], PriceEstimator] = {}


def estimator_for(path: Path) -> PriceEstimator:
    """Return a trained estimator for a history file, reusing it until the file changes."""
    key = (str(path.resolve()), path.stat().st_mtime if path.exists() else 0.0)
    if key not in _CACHE:
        _CACHE.clear()
        _CACHE[key] = PriceEstimator(load_price_history(path))
    return _CACHE[key]


def price_forecast(
    index: pd.DatetimeIndex, actual: pd.Series | None, estimator: PriceEstimator, national: pd.DataFrame | None
) -> pd.DataFrame:
    """Return price in EUR/MWh and its source (actual or estimate) for every horizon hour."""
    estimate = estimator.predict(index, national)
    known = (actual if actual is not None else pd.Series(dtype="float64")).reindex(index)
    return pd.DataFrame(
        {"price": known.fillna(estimate), "source": np.where(known.notna(), "actual", "estimate")},
        index=index,
    )
