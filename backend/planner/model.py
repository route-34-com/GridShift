"""Shared configuration models for the site and its machines."""

from datetime import datetime, timedelta
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

LOCAL_TZ = ZoneInfo("Europe/Berlin")


class Strict(BaseModel):
    """Base model that rejects unknown fields."""

    model_config = ConfigDict(extra="forbid")


class Solar(Strict):
    """Photovoltaic array parameters."""

    kwp: float = Field(0, ge=0)
    tilt: float = Field(30, ge=0, le=90)
    azimuth: float = Field(0, ge=-180, le=180)
    performance_ratio: float = Field(0.85, gt=0, le=1)


class Wind(Strict):
    """Wind turbine parameters."""

    rated_kw: float = Field(0, ge=0)
    hub_height_m: float = Field(100, gt=0)
    power_curve: list[tuple[float, float]] = Field(default_factory=lambda: [(0, 0), (30, 0)])

    @field_validator("power_curve")
    @classmethod
    def _increasing(cls, curve: list[tuple[float, float]]) -> list[tuple[float, float]]:
        speeds = [s for s, _ in curve]
        if len(curve) < 2 or speeds != sorted(speeds) or len(set(speeds)) != len(speeds):
            raise ValueError("power_curve needs at least two points with strictly increasing wind speeds")
        if any(kw < 0 for _, kw in curve):
            raise ValueError("power_curve output cannot be negative")
        return curve


class Battery(Strict):
    """Stationary battery parameters."""

    capacity_kwh: float = Field(0, ge=0)
    max_charge_kw: float = Field(0, ge=0)
    max_discharge_kw: float = Field(0, ge=0)
    efficiency: float = Field(0.95, gt=0, le=1)
    min_soc: float = Field(0.1, ge=0, le=1)
    initial_soc: float = Field(0.5, ge=0, le=1)

    @model_validator(mode="after")
    def _soc_range(self) -> "Battery":
        if self.initial_soc < self.min_soc:
            raise ValueError("initial_soc cannot be below min_soc")
        return self


class Grid(Strict):
    """Grid connection and tariff parameters."""

    max_import_kw: float = Field(gt=0)
    max_export_kw: float = Field(0, ge=0)
    fee_eur_per_kwh: float = Field(0, ge=0)
    export_price_eur_per_kwh: float = Field(0, ge=0)
    peak_charge_eur_per_kw_year: float = Field(0, ge=0)
    peak_so_far_kw: float = Field(0, ge=0)


class Site(Strict):
    """Factory site with on-site generation, storage and grid connection."""

    name: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    solar: Solar = Field(default_factory=Solar)
    wind: Wind = Field(default_factory=Wind)
    battery: Battery = Field(default_factory=Battery)
    grid: Grid
    co2_kg_per_kwh: float = Field(0.38, ge=0)
    email_recipients: list[str] = Field(default_factory=list)


class MachineBase(Strict):
    """Fields shared by every machine type."""

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$")
    name: str
    power_kw: float = Field(gt=0)
    min_run_hours: int = Field(1, ge=1, le=24)


class AlwaysOn(MachineBase):
    """Machine that never stops and is part of the base load."""

    type: Literal["always_on"]


class DailyQuota(MachineBase):
    """Machine that must run a fixed number of hours every local day."""

    type: Literal["daily_quota"]
    hours_per_day: int = Field(ge=1, le=24)

    @model_validator(mode="after")
    def _block_fits(self) -> "DailyQuota":
        if self.min_run_hours > self.hours_per_day:
            raise ValueError(f"{self.id}: min_run_hours cannot exceed hours_per_day")
        return self


class Deadline(MachineBase):
    """Machine job that needs a total number of hours before a due time."""

    type: Literal["deadline"]
    total_hours: int = Field(ge=1)
    due: datetime | None = None
    due_in_hours: int | None = Field(None, ge=1)
    earliest_start: datetime | None = None
    start_in_hours: int | None = Field(None, ge=0)

    @model_validator(mode="after")
    def _one_due(self) -> "Deadline":
        if (self.due is None) == (self.due_in_hours is None):
            raise ValueError(f"{self.id}: set exactly one of due or due_in_hours")
        if self.earliest_start is not None and self.start_in_hours is not None:
            raise ValueError(f"{self.id}: set at most one of earliest_start or start_in_hours")
        if self.min_run_hours > self.total_hours:
            raise ValueError(f"{self.id}: min_run_hours cannot exceed total_hours")
        return self

    def window(self, horizon_start: datetime) -> tuple[datetime, datetime]:
        """Return the UTC start and due times relative to a horizon start."""
        start = _resolve(self.earliest_start, self.start_in_hours, horizon_start) or horizon_start
        due = _resolve(self.due, self.due_in_hours, horizon_start)
        return start, due


def _resolve(absolute: datetime | None, offset: int | None, origin: datetime) -> datetime | None:
    if absolute is not None:
        aware = absolute if absolute.tzinfo else absolute.replace(tzinfo=LOCAL_TZ)
        return aware.astimezone(ZoneInfo("UTC"))
    if offset is not None:
        return origin + timedelta(hours=offset)
    return None


Machine = Annotated[AlwaysOn | DailyQuota | Deadline, Field(discriminator="type")]
FlexibleMachine = DailyQuota | Deadline
