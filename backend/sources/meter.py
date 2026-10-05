"""Measured grid import from the site's interval meter and this year's peak record."""

import io
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from backend.planner.model import LOCAL_TZ, Site
from backend.sources.site import ConfigError

VALUE_COLUMNS = {"import_kw": "kw", "import_kwh": "kwh"}
MAX_INTERVAL_MINUTES = 60


def parse_meter_csv(text: str) -> pd.Series:
    """Return average grid import in kW per meter interval, indexed by UTC interval start.

    Accepts comma or semicolon separated files with a ``timestamp`` column and either
    ``import_kw`` (average kW per interval) or ``import_kwh`` (energy per interval).
    Timestamps without a time zone are read as German local time.
    """
    try:
        frame = pd.read_csv(io.StringIO(text), sep=None, engine="python", dtype=str)
    except (pd.errors.ParserError, pd.errors.EmptyDataError, ValueError) as exc:
        raise ConfigError(f"Meter file is not a readable CSV: {exc}") from exc
    frame.columns = [c.strip().lower() for c in frame.columns]
    unit = next((VALUE_COLUMNS[c] for c in VALUE_COLUMNS if c in frame.columns), None)
    if "timestamp" not in frame.columns or unit is None:
        raise ConfigError("Meter file needs a timestamp column and an import_kw or import_kwh column")
    column = "import_kw" if unit == "kw" else "import_kwh"
    values = pd.to_numeric(frame[column].str.strip().str.replace(",", ".", regex=False), errors="coerce")
    stamps = _timestamps(frame["timestamp"].str.strip())
    if stamps.dt.tz is None:
        stamps = stamps.dt.tz_localize(LOCAL_TZ, ambiguous="NaT", nonexistent="NaT")
    series = pd.Series(values.to_numpy(), index=pd.DatetimeIndex(stamps).tz_convert("UTC"), name="import_kw")
    series = series[series.index.notna()].dropna()
    series = series[series >= 0].sort_index()
    series = series[~series.index.duplicated(keep="last")]
    if len(series) < 2:
        raise ConfigError("Meter file has fewer than two valid readings")
    minutes = series.index.to_series().diff().dropna().median() / pd.Timedelta(minutes=1)
    if not 1 <= minutes <= MAX_INTERVAL_MINUTES:
        raise ConfigError(f"Meter readings are {minutes:.0f} minutes apart; expected 15-minute (or at most hourly) intervals")
    if unit == "kwh":
        series = series * 60 / minutes
    series.attrs["interval_minutes"] = int(round(minutes))
    return series


def _timestamps(raw: pd.Series) -> pd.Series:
    # ISO 8601 first; day-first parsing would read 2026-09-12 as 9 December.
    iso = pd.to_datetime(raw, format="ISO8601", errors="coerce")
    if iso.notna().mean() >= 0.9:
        return iso
    return pd.to_datetime(raw, format="%d.%m.%Y %H:%M", errors="coerce")


def load_meter(path: Path) -> pd.Series | None:
    """Return stored meter readings, or None when no file has been uploaded."""
    if not path.exists():
        return None
    return parse_meter_csv(path.read_text(encoding="utf-8-sig"))


@dataclass
class PeakRecord:
    """This year's highest grid draw and what it costs in peak charges."""

    year: int
    kw: float
    source: str
    at: datetime | None
    settings_kw: float
    meter_kw: float | None
    charge_eur_per_kw_year: float
    meter: dict | None

    @property
    def annual_eur(self) -> float:
        """Return this year's peak charge at the current record."""
        return self.kw * self.charge_eur_per_kw_year

    def to_dict(self) -> dict:
        """Return the record as a JSON-ready dict."""
        return {
            "year": self.year,
            "record_kw": round(self.kw, 1),
            "source": self.source,
            "at": self.at.isoformat() if self.at else None,
            "settings_kw": self.settings_kw,
            "meter_kw": round(self.meter_kw, 1) if self.meter_kw is not None else None,
            "charge_eur_per_kw_year": self.charge_eur_per_kw_year,
            "annual_eur": round(self.annual_eur, 2),
            "monthly_eur": round(self.annual_eur / 12, 2),
            "meter": self.meter,
        }


def current_peak(site: Site, readings: pd.Series | None, now: datetime) -> PeakRecord:
    """Return the higher of the configured record and the metered peak for the current calendar year."""
    year = pd.Timestamp(now).tz_convert(LOCAL_TZ).year
    meter_kw, at, meter = None, None, None
    if readings is not None:
        local_years = readings.index.tz_convert(LOCAL_TZ).year
        this_year = readings[local_years == year]
        meter = {
            "rows": int(len(readings)),
            "start": readings.index[0].isoformat(),
            "end": readings.index[-1].isoformat(),
            "interval_minutes": readings.attrs.get("interval_minutes"),
            "rows_this_year": int(len(this_year)),
        }
        if len(this_year):
            meter_kw, at = float(this_year.max()), this_year.idxmax().to_pydatetime()
    settings_kw = site.grid.peak_so_far_kw
    if meter_kw is not None and meter_kw >= settings_kw:
        kw, source = meter_kw, "meter"
    else:
        kw, source, at = settings_kw, "settings", None
    return PeakRecord(year, kw, source, at, settings_kw, meter_kw, site.grid.peak_charge_eur_per_kw_year, meter)
