"""Historical hourly base load of the factory."""

from pathlib import Path

import pandas as pd

from backend.sources.site import ConfigError


def load_demand_history(path: Path) -> pd.Series:
    """Load hourly base load in kW indexed by UTC timestamp."""
    if not path.exists():
        raise ConfigError(f"Demand history not found: {path}")
    frame = pd.read_csv(path)
    if not {"timestamp", "load_kw"} <= set(frame.columns):
        raise ConfigError(f"{path.name} needs columns timestamp and load_kw")
    series = pd.Series(
        pd.to_numeric(frame["load_kw"], errors="coerce").to_numpy(),
        index=pd.to_datetime(frame["timestamp"], utc=True, errors="coerce"),
        name="load_kw",
    )
    series = series[series.index.notna()].dropna()
    series = series[series >= 0].sort_index()
    series = series[~series.index.duplicated(keep="last")]
    if len(series) < 24 * 7:
        raise ConfigError(f"{path.name} needs at least one week of valid hourly rows")
    return series.resample("h").mean().interpolate(limit=3).dropna()
