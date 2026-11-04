"""Naive schedule that runs machines as early as allowed with a simple battery rule."""

import numpy as np

from backend.planner.inputs import PlanInputs, PlanResult
from backend.planner.model import DailyQuota, Site
from backend.planner.requirements import Requirement
from backend.planner.result import assemble

SHIFT_START_HOUR = 6


def _earliest(req: Requirement, local_hours: np.ndarray, hours: np.ndarray) -> np.ndarray:
    runs = np.zeros(len(hours))
    for group in req.groups:
        steps = group.hours
        if isinstance(req.machine, DailyQuota):
            first = next((i for i, t in enumerate(steps) if local_hours[t] >= SHIFT_START_HOUR), 0)
            steps = np.concatenate([steps[first:], steps[:first]])
        done = 0.0
        for t in steps:
            if done >= group.required - 1e-9:
                break
            runs[t] = 1
            done += hours[t]
    return runs


def simulate_battery(inputs: PlanInputs, site: Site, load: np.ndarray) -> dict[str, np.ndarray]:
    """Charge from surplus renewables and discharge to cover deficits, step by step."""
    bat, grid = site.battery, site.grid
    n = len(load)
    flows = {k: np.zeros(n) for k in ("charge", "discharge", "soc", "grid_import", "grid_export", "curtail", "unmet")}
    floor, cap = bat.min_soc * bat.capacity_kwh, bat.capacity_kwh
    soc = bat.initial_soc * cap
    for t, (net, renewable, dt) in enumerate(zip(load - inputs.renewables, inputs.renewables, inputs.hours)):
        if net < 0:
            charge = min(-net, bat.max_charge_kw, max(0.0, (cap - soc) / (bat.efficiency * dt)))
            soc += charge * bat.efficiency * dt
            spare = -net - charge
            export = min(spare, grid.max_export_kw, renewable)
            flows["charge"][t], flows["grid_export"][t], flows["curtail"][t] = charge, export, spare - export
        else:
            discharge = min(net, bat.max_discharge_kw, max(0.0, (soc - floor) * bat.efficiency / dt))
            soc -= discharge * dt / bat.efficiency
            need = net - discharge
            imported = min(need, grid.max_import_kw)
            flows["discharge"][t], flows["grid_import"][t], flows["unmet"][t] = discharge, imported, need - imported
        flows["soc"][t] = soc
    return flows


def baseline(inputs: PlanInputs, site: Site, requirements: list[Requirement]) -> PlanResult:
    """Return the run-as-early-as-possible reference schedule."""
    n = len(inputs.index)
    local_hours = inputs.index.tz_convert("Europe/Berlin").hour.to_numpy()
    on = {r.machine.id: _earliest(r, local_hours, inputs.hours) for r in requirements}
    load = inputs.demand.to_numpy() + sum((on[r.machine.id] * r.machine.power_kw for r in requirements), start=np.zeros(n))
    return assemble(inputs, requirements, on, simulate_battery(inputs, site, load), "baseline")
