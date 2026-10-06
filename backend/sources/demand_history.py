"""Historical hourly base load of the factory."""

import io
from pathlib import Path

import pandas as pd

from backend.sources.site import ConfigError


def load_demand_history(path: Path) -> pd.Series:
    """Load hourly base load in kW indexed by UTC timestamp."""
    if not path.exists():
        raise ConfigError(f"Demand history not found: {path}")
    return _series(pd.read_csv(path), path.name)


def parse_demand_history(text: str) -> pd.Series:
    """Validate uploaded load history (comma or semicolon separated) the same way the planner reads it."""
    try:
        # German exports use semicolons with decimal commas; a sniffer can mistake the comma for the separator.
        header = text.lstrip().splitlines()[0] if text.strip() else ""
        frame = pd.read_csv(io.StringIO(text), sep=";" if ";" in header else ",", dtype=str)
    except (pd.errors.ParserError, pd.errors.EmptyDataError, ValueError) as exc:
        raise ConfigError(f"Load history is not a readable CSV: {exc}") from exc
    frame.columns = [str(c).strip().lower() for c in frame.columns]
    return _series(frame, "Load history")


def _series(frame: pd.DataFrame, source: str) -> pd.Series:
    if not {"timestamp", "load_kw"} <= set(frame.columns):
        raise ConfigError(f"{source} needs columns timestamp and load_kw")
    values = frame["load_kw"]
    if not pd.api.types.is_numeric_dtype(values):
        values = values.astype(str).str.strip().str.replace(",", ".", regex=False)
    series = pd.Series(
        pd.to_numeric(values, errors="coerce").to_numpy(),
        index=pd.to_datetime(frame["timestamp"], utc=True, errors="coerce"),
        name="load_kw",
    )
    series = series[series.index.notna()].dropna()
    series = series[series >= 0].sort_index()
    series = series[~series.index.duplicated(keep="last")]
    if len(series) < 24 * 7:
        raise ConfigError(f"{source} needs at least one week of valid hourly rows")
    return series.resample("h").mean().interpolate(limit=3).dropna()
