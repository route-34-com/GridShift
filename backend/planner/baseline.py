"""Naive schedule that runs machines as early as allowed with a simple battery rule."""

import numpy as np

from backend.planner.inputs import PlanInputs, PlanResult
from backend.planner.model import DailyQuota, Site
from backend.planner.requirements import Requirement
from backend.planner.result import assemble

SHIFT_START_HOUR = 6


def _earliest(req: Requirement, local_hours: np.ndarray, n: int) -> np.ndarray:
    runs = np.zeros(n)
    for group in req.groups:
        hours = group.hours
        if isinstance(req.machine, DailyQuota):
            first = next((i for i, t in enumerate(hours) if local_hours[t] >= SHIFT_START_HOUR), 0)
            hours = np.concatenate([hours[first:], hours[:first]])
        runs[hours[: group.required]] = 1
    return runs


def simulate_battery(inputs: PlanInputs, site: Site, load: np.ndarray) -> dict[str, np.ndarray]:
    """Charge from surplus renewables and discharge to cover deficits, hour by hour."""
    bat, grid = site.battery, site.grid
    n = len(load)
    flows = {k: np.zeros(n) for k in ("charge", "discharge", "soc", "grid_import", "grid_export", "curtail", "unmet")}
    floor, cap = bat.min_soc * bat.capacity_kwh, bat.capacity_kwh
    soc = bat.initial_soc * cap
    for t, (net, renewable) in enumerate(zip(load - inputs.renewables, inputs.renewables)):
        if net < 0:
            charge = min(-net, bat.max_charge_kw, max(0.0, (cap - soc) / bat.efficiency))
            soc += charge * bat.efficiency
            spare = -net - charge
            export = min(spare, grid.max_export_kw, renewable)
            flows["charge"][t], flows["grid_export"][t], flows["curtail"][t] = charge, export, spare - export
        else:
            discharge = min(net, bat.max_discharge_kw, max(0.0, (soc - floor) * bat.efficiency))
            soc -= discharge / bat.efficiency
            need = net - discharge
            imported = min(need, grid.max_import_kw)
            flows["discharge"][t], flows["grid_import"][t], flows["unmet"][t] = discharge, imported, need - imported
        flows["soc"][t] = soc
    return flows


def baseline(inputs: PlanInputs, site: Site, requirements: list[Requirement]) -> PlanResult:
    """Return the run-as-early-as-possible reference schedule."""
    n = len(inputs.index)
    local_hours = inputs.index.tz_convert("Europe/Berlin").hour.to_numpy()
    on = {r.machine.id: _earliest(r, local_hours, n) for r in requirements}
    load = inputs.demand.to_numpy() + sum((on[r.machine.id] * r.machine.power_kw for r in requirements), start=np.zeros(n))
    return assemble(inputs, requirements, on, simulate_battery(inputs, site, load), "baseline")
