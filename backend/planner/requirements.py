"""Turn machine rules into per-hour availability and required run hours."""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from backend.forecast.horizon import local_dates
from backend.planner.model import DailyQuota, Deadline, FlexibleMachine


@dataclass
class Group:
    """Hours in which a machine must run a required number of hours."""

    hours: np.ndarray
    required: int
    label: str


@dataclass
class Requirement:
    """Availability and run-hour targets for one flexible machine."""

    machine: FlexibleMachine
    allowed: np.ndarray
    groups: list[Group]
    warnings: list[str]


def _quota(machine: DailyQuota, index: pd.DatetimeIndex) -> Requirement:
    dates = local_dates(index)
    groups = []
    for day in dict.fromkeys(dates):
        hours = np.flatnonzero(dates == day)
        full = len(hours) >= 23
        required = machine.hours_per_day if full else machine.hours_per_day * len(hours) // 24
        if required:
            groups.append(Group(hours, min(required, len(hours)), day.isoformat()))
    return Requirement(machine, np.ones(len(index), dtype=bool), groups, [])


def _deadline(machine: Deadline, index: pd.DatetimeIndex) -> Requirement:
    start, due = machine.window(index[0].to_pydatetime())
    stamps = index.to_pydatetime()
    allowed = np.array([start <= t and t + pd.Timedelta(hours=1) <= due for t in stamps])
    horizon_end = index[-1] + pd.Timedelta(hours=1)
    if due <= index[0]:
        return Requirement(machine, np.zeros(len(index), dtype=bool), [], [f"{machine.name} was due before the plan starts and is skipped"])
    after = max(0, int((pd.Timestamp(due) - max(horizon_end, pd.Timestamp(start))) / pd.Timedelta(hours=1)))
    required = max(0, machine.total_hours - after)
    warnings = []
    if after and required < machine.total_hours:
        warnings.append(f"{machine.name} is due after the horizon; {required} of {machine.total_hours} h must run this week")
    groups = [Group(np.flatnonzero(allowed), required, f"due {pd.Timestamp(due).isoformat()}")] if required else []
    return Requirement(machine, allowed, groups, warnings)


def build_requirements(machines: list[FlexibleMachine], index: pd.DatetimeIndex) -> list[Requirement]:
    """Return availability and targets for every flexible machine."""
    return [_quota(m, index) if isinstance(m, DailyQuota) else _deadline(m, index) for m in machines]
