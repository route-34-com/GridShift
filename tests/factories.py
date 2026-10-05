from datetime import datetime, timezone

import numpy as np
import pandas as pd

from backend.forecast.horizon import horizon_index
from backend.planner.inputs import PlanInputs
from backend.planner.model import Battery, DailyQuota, Deadline, Grid, Site, Solar

NOW = datetime(2026, 7, 6, 10, tzinfo=timezone.utc)


def make_site(
    battery: bool = True, max_import: float = 3000, max_export: float = 1000, peak_charge: float = 0, peak_so_far: float = 0
) -> Site:
    return Site(
        name="Test",
        latitude=48.8,
        longitude=9.2,
        solar=Solar(kwp=1000),
        battery=Battery(capacity_kwh=1000, max_charge_kw=500, max_discharge_kw=500) if battery else Battery(),
        grid=Grid(
            max_import_kw=max_import, max_export_kw=max_export, fee_eur_per_kwh=0.05, export_price_eur_per_kwh=0.04,
            peak_charge_eur_per_kw_year=peak_charge, peak_so_far_kw=peak_so_far,
        ),
    )


def make_inputs(price=None, solar=None, wind=None, demand=None, now: datetime = NOW, sources=None) -> PlanInputs:
    index = horizon_index(now)
    hours = index.tz_convert("Europe/Berlin").hour.to_numpy()
    n = len(index)

    def series(value, default):
        if value is None:
            value = default
        return pd.Series(np.broadcast_to(np.asarray(value, dtype=float), (n,)).copy(), index=index)

    night_cheap = np.where((hours < 6) | (hours >= 22), 40.0, 150.0)
    return PlanInputs(
        index=index,
        price=series(price, night_cheap),
        price_source=pd.Series(sources if sources is not None else "actual", index=index),
        solar=series(solar, 0.0),
        wind=series(wind, 0.0),
        demand=series(demand, 300.0),
    )


def press(hours: int = 8, power: float = 250, min_run: int = 2, id: str = "press") -> DailyQuota:
    return DailyQuota(id=id, name=id.title(), type="daily_quota", power_kw=power, hours_per_day=hours, min_run_hours=min_run)


def furnace(total: int = 20, due: int = 120, start: int | None = None, power: float = 600, min_run: int = 4) -> Deadline:
    return Deadline(
        id="furnace", name="Furnace", type="deadline", power_kw=power, total_hours=total,
        due_in_hours=due, start_in_hours=start, min_run_hours=min_run,
    )
