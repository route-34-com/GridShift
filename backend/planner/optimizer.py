"""Mixed-integer optimizer that schedules machines and the battery at lowest cost."""

import highspy
import numpy as np

from backend.planner.inputs import PlanInputs, PlanResult
from backend.planner.model import Site
from backend.planner.requirements import Requirement
from backend.planner.result import assemble

SHORTFALL_PENALTY = 1000.0
UNMET_PENALTY = 10.0
CURTAIL_PENALTY = 1e-4
INT = highspy.HighsVarType.kInteger


class PlannerError(RuntimeError):
    """Raised when the solver returns no usable solution."""


def optimize(inputs: PlanInputs, site: Site, requirements: list[Requirement], time_limit: float = 60.0) -> PlanResult:
    """Return the lowest-cost machine and battery schedule over the horizon."""
    n = len(inputs.index)
    bat, grid = site.battery, site.grid
    renewables = inputs.renewables
    h = highspy.Highs()
    h.silent()
    h.setOptionValue("time_limit", float(time_limit))
    h.setOptionValue("mip_rel_gap", 0.005)

    on, slack = {}, []
    for req in requirements:
        m = req.machine
        x = h.addVariables(n, lb=0, ub=req.allowed.astype(float).tolist(), type=INT)
        on[m.id] = x
        if m.min_run_hours > 1:
            s = h.addVariables(n, lb=0, ub=1, type=INT)
            h.addConstr(s[0] >= x[0])
            h.addConstrs(s[1:] >= x[1:] - x[:-1])
            for k in range(1, m.min_run_hours):
                h.addConstrs(x[k:] >= s[:-k])
        for group in req.groups:
            short = h.addVariable(lb=0, ub=group.required)
            h.addConstr(h.qsum(x[i] for i in group.hours) + short == group.required)
            slack.append((short, m.power_kw))

    cap = bat.capacity_kwh
    charge = h.addVariables(n, lb=0, ub=bat.max_charge_kw)
    discharge = h.addVariables(n, lb=0, ub=bat.max_discharge_kw)
    soc = h.addVariables(n, lb=bat.min_soc * cap, ub=cap)
    mode = h.addVariables(n, lb=0, ub=1, type=INT)
    grid_import = h.addVariables(n, lb=0, ub=grid.max_import_kw)
    grid_export = h.addVariables(n, lb=0, ub=grid.max_export_kw)
    direction = h.addVariables(n, lb=0, ub=1, type=INT)
    curtail = h.addVariables(n, lb=0, ub=renewables.tolist())
    unmet = h.addVariables(n, lb=0)

    load = inputs.demand.to_numpy()
    flexible = sum((on[r.machine.id] * r.machine.power_kw for r in requirements), start=0 * charge)
    h.addConstrs(renewables + discharge + grid_import + unmet == load + flexible + charge + grid_export + curtail)
    h.addConstrs(charge <= bat.max_charge_kw * mode)
    h.addConstrs(discharge <= bat.max_discharge_kw * (1 - mode))
    h.addConstrs(grid_import <= grid.max_import_kw * direction)
    h.addConstrs(grid_export <= grid.max_export_kw * (1 - direction))
    h.addConstrs(grid_export + curtail <= renewables)
    if cap > 0:
        start = bat.initial_soc * cap
        h.addConstr(soc[0] == start + bat.efficiency * charge[0] - discharge[0] * (1 / bat.efficiency))
        h.addConstrs(soc[1:] == soc[:-1] + bat.efficiency * charge[1:] - discharge[1:] * (1 / bat.efficiency))
        h.addConstr(soc[n - 1] >= start)
    else:
        h.addConstrs(charge == 0)
        h.addConstrs(discharge == 0)

    price = inputs.import_price + grid.fee_eur_per_kwh
    objective = (
        h.qsum(grid_import * price)
        - h.qsum(grid_export * grid.export_price_eur_per_kwh)
        + h.qsum(curtail * CURTAIL_PENALTY)
        + h.qsum(unmet * UNMET_PENALTY)
        + h.qsum(s * (SHORTFALL_PENALTY + p) for s, p in slack)
    )
    if grid.peak_charge_eur_per_kw_year > 0:
        # Any import above this year's record raises the annual peak charge for the whole year.
        new_peak = h.addVariable(lb=0)
        for t in range(n):
            h.addConstr(grid_import[t] <= grid.peak_so_far_kw + new_peak)
        objective = objective + new_peak * grid.peak_charge_eur_per_kw_year
    h.minimize(objective)

    status = h.modelStatusToString(h.getModelStatus())
    info = h.getInfo()
    if info.primal_solution_status != 2:
        raise PlannerError(f"Solver found no feasible plan ({status})")
    flows = {
        "charge": h.vals(charge),
        "discharge": h.vals(discharge),
        "soc": h.vals(soc) if cap > 0 else np.zeros(n),
        "grid_import": h.vals(grid_import),
        "grid_export": h.vals(grid_export),
        "curtail": h.vals(curtail),
        "unmet": h.vals(unmet),
    }
    on_values = {k: np.asarray(h.vals(v)) for k, v in on.items()}
    label = "optimal" if status == "Optimal" else "time_limit"
    return assemble(inputs, requirements, on_values, flows, label, float(info.mip_gap))
