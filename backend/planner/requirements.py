"""Turn machine rules into per-step availability and required run hours."""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from backend.forecast.horizon import horizon_end, local_dates, step_hours
from backend.planner.model import DailyQuota, Deadline, FlexibleMachine


@dataclass
class Group:
    """Steps in which a machine must run a required number of hours."""

    hours: np.ndarray
    required: float
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
    length = step_hours(index)
    groups = []
    for day in dict.fromkeys(dates):
        steps = np.flatnonzero(dates == day)
        day_hours = float(length[steps].sum())
        full = day_hours >= 23
        required = machine.hours_per_day if full else machine.hours_per_day * int(day_hours) // 24
        if required:
            groups.append(Group(steps, min(required, day_hours), day.isoformat()))
    return Requirement(machine, np.ones(len(index), dtype=bool), groups, [])


def _deadline(machine: Deadline, index: pd.DatetimeIndex) -> Requirement:
    start, due = machine.window(index[0].to_pydatetime())
    length = step_hours(index)
    ends = index + pd.to_timedelta(length, unit="h")
    allowed = np.asarray((index >= pd.Timestamp(start)) & (ends <= pd.Timestamp(due)))
    if due <= index[0]:
        return Requirement(machine, np.zeros(len(index), dtype=bool), [], [f"{machine.name} was due before the plan starts and is skipped"])
    after = max(0, int((pd.Timestamp(due) - max(horizon_end(index), pd.Timestamp(start))) / pd.Timedelta(hours=1)))
    required = max(0, machine.total_hours - after)
    warnings = []
    if after and required < machine.total_hours:
        warnings.append(f"{machine.name} is due after the horizon; {required} of {machine.total_hours} h must run this week")
    groups = [Group(np.flatnonzero(allowed), required, f"due {pd.Timestamp(due).isoformat()}")] if required else []
    return Requirement(machine, allowed, groups, warnings)


def build_requirements(machines: list[FlexibleMachine], index: pd.DatetimeIndex) -> list[Requirement]:
    """Return availability and targets for every flexible machine."""
    return [_quota(m, index) if isinstance(m, DailyQuota) else _deadline(m, index) for m in machines]
