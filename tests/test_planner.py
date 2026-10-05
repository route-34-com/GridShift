from datetime import datetime, timezone

import numpy as np
import pytest

from backend.forecast.horizon import local_dates
from backend.planner.baseline import baseline
from backend.planner.explain import explain_blocks
from backend.planner.metrics import measure
from backend.planner.optimizer import optimize
from backend.planner.requirements import build_requirements
from tests.factories import furnace, make_inputs, make_site, press

TOL = 1e-3


def solve(inputs, site, machines):
    return optimize(inputs, site, build_requirements(machines, inputs.index))


def runs(values):
    padded = np.concatenate([[0], values, [0]])
    edges = np.flatnonzero(np.diff(padded))
    return list(zip(edges[::2], edges[1::2]))


@pytest.fixture(scope="module")
def standard():
    site = make_site()
    inputs = make_inputs(solar=np.tile(np.r_[np.zeros(8), np.full(8, 600.0), np.zeros(8)], 7))
    machines = [press(), press(6, id="press-b"), furnace()]
    return site, inputs, machines, solve(inputs, site, machines)


def test_energy_balance_every_hour(standard):
    _, _, _, plan = standard
    h = plan.hourly
    supply = h.solar + h.wind + h.discharge + h.grid_import + h.unmet
    use = h.demand + h.flexible + h.charge + h.grid_export + h.curtail
    assert np.allclose(supply, use, atol=0.01)


def test_battery_within_limits(standard):
    site, _, _, plan = standard
    h, bat = plan.hourly, site.battery
    assert (h.soc >= bat.min_soc * bat.capacity_kwh - TOL).all()
    assert (h.soc <= bat.capacity_kwh + TOL).all()
    assert h.soc.iloc[-1] >= bat.initial_soc * bat.capacity_kwh - TOL
    assert not ((h.charge > TOL) & (h.discharge > TOL)).any()


def test_no_simultaneous_import_and_export(standard):
    _, _, _, plan = standard
    h = plan.hourly
    assert not ((h.grid_import > TOL) & (h.grid_export > TOL)).any()


def test_daily_quotas_met(standard):
    _, inputs, _, plan = standard
    per_day = plan.schedule.groupby(local_dates(inputs.index)).sum()
    assert (per_day["press"] == 8).all()
    assert (per_day["press-b"] == 6).all()
    assert plan.shortfalls == []


def test_deadline_met_inside_window(standard):
    _, _, _, plan = standard
    furnace_runs = plan.schedule["furnace"].to_numpy()
    assert furnace_runs.sum() == 20
    assert furnace_runs[120:].sum() == 0


def test_min_run_blocks_respected(standard):
    _, _, machines, plan = standard
    for machine in machines:
        values = plan.schedule[machine.id].to_numpy()
        for a, b in runs(values):
            assert b - a >= machine.min_run_hours or b == len(values)


def test_optimizer_beats_baseline(standard):
    site, inputs, machines, plan = standard
    reference = baseline(inputs, site, build_requirements(machines, inputs.index))
    assert measure(plan.hourly, site).cost_eur <= measure(reference.hourly, site).cost_eur


def test_peak_charge_keeps_import_under_record():
    machines = [press(), press(6, id="press-b"), furnace()]
    inputs = make_inputs()
    free = solve(inputs, make_site(), machines)
    site = make_site(peak_charge=120, peak_so_far=900)
    capped = solve(inputs, site, machines)
    assert free.hourly.grid_import.max() > 900
    assert capped.hourly.grid_import.max() <= 900 + TOL
    assert capped.shortfalls == []
    assert measure(capped.hourly, site).peak_charge_eur == 0


def test_unavoidable_new_peak_is_kept_as_low_as_possible():
    site = make_site(battery=False, peak_charge=120, peak_so_far=100)
    inputs = make_inputs(demand=300.0)
    plan = solve(inputs, site, [press(4, min_run=1), press(4, min_run=1, id="press-b")])
    metrics = measure(plan.hourly, site)
    assert plan.hourly.grid_import.max() == pytest.approx(550, abs=TOL)
    assert metrics.peak_charge_eur == pytest.approx((550 - 100) * 120, abs=0.1)
    assert metrics.total_cost_eur == pytest.approx(metrics.cost_eur + metrics.peak_charge_eur, abs=0.01)


def test_flexible_load_moves_to_cheap_night_hours():
    site = make_site(battery=False)
    inputs = make_inputs()
    plan = solve(inputs, site, [press(6)])
    hours = inputs.index.tz_convert("Europe/Berlin").hour.to_numpy()
    night = (hours < 6) | (hours >= 22)
    assert plan.schedule["press"].to_numpy()[~night].sum() == 0


def test_sunny_middays_attract_load():
    site = make_site(battery=False)
    hours = make_inputs().index.tz_convert("Europe/Berlin").hour.to_numpy()
    solar = np.where((hours >= 10) & (hours < 16), 900.0, 0.0)
    inputs = make_inputs(price=120.0, solar=solar)
    plan = solve(inputs, site, [press(6, power=500)])
    assert plan.schedule["press"].to_numpy()[solar == 0].sum() == 0


def test_dark_week_charges_battery_off_peak():
    site = make_site()
    inputs = make_inputs()
    plan = solve(inputs, site, [press(4)])
    hours = inputs.index.tz_convert("Europe/Berlin").hour.to_numpy()
    night = (hours < 6) | (hours >= 22)
    assert plan.hourly.charge[night].sum() > plan.hourly.charge[~night].sum()
    assert plan.hourly.discharge[~night].sum() > 0


def test_negative_prices_pull_load_and_charging():
    site = make_site()
    price = np.full(168, 120.0)
    price[30:34] = -200.0
    inputs = make_inputs(price=price)
    plan = solve(inputs, site, [press(4, min_run=1)])
    assert plan.schedule["press"].to_numpy()[30:34].sum() == 4
    assert plan.hourly.charge.iloc[30:34].sum() > 0


def test_impossible_deadline_reports_shortfall():
    site = make_site()
    inputs = make_inputs()
    plan = solve(inputs, site, [furnace(total=30, due=20, min_run=1)])
    assert plan.schedule["furnace"].sum() == 20
    assert plan.shortfalls[0].required_hours == 30
    assert plan.shortfalls[0].scheduled_hours == 20


def test_grid_limit_too_low_reports_unmet_instead_of_failing():
    site = make_site(battery=False, max_import=200)
    inputs = make_inputs(demand=300.0)
    plan = solve(inputs, site, [press(2)])
    assert measure(plan.hourly, site).unmet_kwh > 0


def test_overdue_deadline_is_skipped_with_warning():
    inputs = make_inputs()
    job = furnace(due=1)
    job = job.model_copy(update={"due_in_hours": None, "due": datetime(2026, 1, 1, tzinfo=timezone.utc)})
    req = build_requirements([job], inputs.index)[0]
    assert req.groups == [] and "due before" in req.warnings[0]


def test_deadline_beyond_horizon_is_prorated():
    inputs = make_inputs()
    req = build_requirements([furnace(total=20, due=180)], inputs.index)[0]
    assert req.groups[0].required == 8
    assert "after the horizon" in req.warnings[0]


def test_dst_week_keeps_quotas_per_local_day():
    inputs = make_inputs(now=datetime(2026, 10, 24, 10, tzinfo=timezone.utc))
    assert len(inputs.index) == 168
    site = make_site()
    plan = solve(inputs, site, [press(8)])
    per_day = plan.schedule.groupby(local_dates(inputs.index)).sum()["press"]
    assert len(per_day) == 7
    assert (per_day == 8).all()


def test_site_without_battery_or_renewables():
    site = make_site(battery=False)
    inputs = make_inputs()
    plan = solve(inputs, site, [press(8)])
    assert plan.hourly.charge.sum() == 0 and plan.hourly.soc.sum() == 0


def test_no_flexible_machines_still_plans():
    site = make_site()
    plan = solve(make_inputs(), site, [])
    assert plan.schedule.empty or plan.schedule.shape[1] == 0
    assert plan.hourly.grid_import.sum() > 0


def test_blocks_have_reasons(standard):
    _, _, machines, plan = standard
    blocks = explain_blocks(plan.hourly, plan.schedule, machines)
    assert blocks
    assert all(b.reason and b.hours >= 1 for b in blocks)
    assert sum(b.hours for b in blocks if b.machine_id == "furnace") == 20
