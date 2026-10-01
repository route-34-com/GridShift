"""Forecast inputs and plan results shared by the optimizer and the baseline."""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

SERIES = ("price", "solar", "wind", "demand")


@dataclass
class PlanInputs:
    """Hourly forecasts over the planning horizon."""

    index: pd.DatetimeIndex
    price: pd.Series
    price_source: pd.Series
    solar: pd.Series
    wind: pd.Series
    demand: pd.Series

    def __post_init__(self) -> None:
        for name in SERIES:
            series = getattr(self, name).reindex(self.index)
            if series.isna().any():
                raise ValueError(f"{name} forecast has gaps in the horizon")
            setattr(self, name, series.astype("float64"))
        self.price_source = self.price_source.reindex(self.index).fillna("estimate")
        if (self.demand < 0).any():
            raise ValueError("demand forecast cannot be negative")

    @property
    def renewables(self) -> np.ndarray:
        """Return combined solar and wind output in kW."""
        return (self.solar + self.wind).to_numpy()

    @property
    def import_price(self) -> np.ndarray:
        """Return spot price in EUR/kWh."""
        return self.price.to_numpy() / 1000


@dataclass
class Shortfall:
    """Hours a machine could not get within its window."""

    machine_id: str
    required_hours: int
    scheduled_hours: int
    reason: str


@dataclass
class PlanResult:
    """Hourly energy flows and machine schedule for one strategy."""

    hourly: pd.DataFrame
    schedule: pd.DataFrame
    shortfalls: list[Shortfall] = field(default_factory=list)
    status: str = "optimal"
    gap: float = 0.0
