"""Assemble plan results from solved flows."""

import numpy as np
import pandas as pd

from backend.planner.inputs import PlanInputs, PlanResult, Shortfall
from backend.planner.requirements import Requirement


def assemble(
    inputs: PlanInputs,
    requirements: list[Requirement],
    on: dict[str, np.ndarray],
    flows: dict[str, np.ndarray],
    status: str = "optimal",
    gap: float = 0.0,
) -> PlanResult:
    """Build a PlanResult from per-machine on/off arrays and energy flows."""
    schedule = pd.DataFrame({k: np.round(v).astype(int) for k, v in on.items()}, index=inputs.index)
    power = {r.machine.id: r.machine.power_kw for r in requirements}
    flexible = sum((schedule[k] * power[k] for k in schedule), start=pd.Series(0.0, index=inputs.index))
    hourly = pd.DataFrame(
        {
            "price": inputs.price,
            "price_source": inputs.price_source,
            "solar": inputs.solar,
            "wind": inputs.wind,
            "demand": inputs.demand,
            "hours": inputs.hours,
            "flexible": flexible.astype("float64"),
            **{k: np.clip(np.asarray(v, dtype="float64"), 0, None) for k, v in flows.items()},
        },
        index=inputs.index,
    )
    return PlanResult(hourly.round(3), schedule, shortfalls(requirements, schedule, inputs.hours), status, gap)


def shortfalls(requirements: list[Requirement], schedule: pd.DataFrame, hours: np.ndarray) -> list[Shortfall]:
    """Return groups whose required hours were not met."""
    found = []
    for req in requirements:
        runs = schedule[req.machine.id].to_numpy() if req.machine.id in schedule else np.zeros(len(schedule))
        for group in req.groups:
            got = float((runs[group.hours] * hours[group.hours]).sum())
            if got < group.required - 1e-6:
                reason = "not enough hours in its window" if hours[group.hours].sum() < group.required else "grid or site limits"
                found.append(Shortfall(req.machine.id, group.required, round(got, 2), f"{group.label}: {reason}"))
    return found
