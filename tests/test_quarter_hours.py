from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from backend.forecast.horizon import align, horizon_end, horizon_index, local_dates, step_hours
from backend.planner.baseline import baseline
from backend.planner.explain import explain_blocks
from backend.planner.metrics import hourly_cost, measure
from backend.planner.optimizer import optimize
from backend.planner.requirements import build_requirements
from backend.sources.price import to_steps
from tests.factories import NOW, furnace, make_inputs, make_site, press

TOL = 1e-3


def solve(inputs, site, machines):
    return optimize(inputs, site, build_requirements(machines, inputs.index))


def on_hours(plan, inputs, machine_id):
    return pd.Series(plan.schedule[machine_id].to_numpy() * inputs.hours, index=inputs.index)


def runs(values):
    padded = np.concatenate([[0], values, [0]])
    edges = np.flatnonzero(np.diff(padded))
    return list(zip(edges[::2], edges[1::2]))


@pytest.fixture(scope="module")
def mixed():
    site = make_site()
    inputs = make_inputs(fine_days=1)
    local = inputs.index.tz_convert("Europe/Berlin").hour.to_numpy()
    solar = np.where((local >= 10) & (local < 16), 600.0, 0.0)
    inputs = make_inputs(solar=solar, fine_days=1)
    machines = [press(), press(6, id="press-b"), furnace()]
    return site, inputs, machines, solve(inputs, site, machines)


def test_first_day_is_quarter_hours_then_hourly():
    index = horizon_index(NOW)
    hours = step_hours(index)
    first_day = local_dates(index) == local_dates(index)[0]
    assert (hours[first_day] == 0.25).all() and first_day.sum() == 96
    assert (hours[~first_day] == 1).all() and (~first_day).sum() == 144
    assert horizon_end(index) - index[0] == pd.Timedelta(hours=168)


def test_short_dst_day_has_92_quarter_hours():
    index = horizon_index(datetime(2027, 3, 27, 10, tzinfo=timezone.utc))
    first_day = local_dates(index) == local_dates(index)[0]
    assert first_day.sum() == 92


def test_energy_balance_and_battery_per_step(mixed):
    site, inputs, _, plan = mixed
    h, bat = plan.hourly, site.battery
    assert np.allclose(h.solar + h.wind + h.discharge + h.grid_import + h.unmet, h.demand + h.flexible + h.charge + h.grid_export + h.curtail, atol=0.01)
    soc = h.soc.to_numpy()
    previous = np.r_[bat.initial_soc * bat.capacity_kwh, soc[:-1]]
    expected = previous + h.charge * bat.efficiency * h.hours - h.discharge * h.hours / bat.efficiency
    assert np.allclose(soc, expected, atol=0.5)


def test_quotas_count_hours_not_steps(mixed):
    _, inputs, _, plan = mixed
    per_day = on_hours(plan, inputs, "press").groupby(local_dates(inputs.index)).sum()
    assert np.allclose(per_day, 8)
    assert plan.shortfalls == []


def test_deadline_hours_and_min_run_in_hours(mixed):
    _, inputs, machines, plan = mixed
    assert on_hours(plan, inputs, "furnace").sum() == pytest.approx(20)
    for machine in machines:
        values = plan.schedule[machine.id].to_numpy()
        for a, b in runs(values):
            if b < len(values):
                assert inputs.hours[a:b].sum() >= machine.min_run_hours - TOL


def test_costs_weight_each_step_by_its_length(mixed):
    site, _, _, plan = mixed
    h = plan.hourly
    expected = (h.grid_import * (h.price / 1000 + site.grid.fee_eur_per_kwh) - h.grid_export * site.grid.export_price_eur_per_kwh) * h.hours
    assert hourly_cost(h, site).sum() == pytest.approx(expected.sum())
    assert measure(h, site).import_kwh == pytest.approx((h.grid_import * h.hours).sum(), abs=0.1)


def test_blocks_report_hours_and_end_on_the_quarter(mixed):
    _, inputs, machines, plan = mixed
    blocks = explain_blocks(plan.hourly, plan.schedule, machines)
    furnace_hours = sum(b.hours for b in blocks if b.machine_id == "furnace")
    assert furnace_hours == pytest.approx(20)
    assert all(pd.Timestamp(b.end).minute % 15 == 0 for b in blocks)


def test_optimizer_beats_baseline_on_mixed_steps(mixed):
    site, inputs, machines, plan = mixed
    reference = baseline(inputs, site, build_requirements(machines, inputs.index))
    per_day = pd.Series(reference.schedule["press"].to_numpy() * inputs.hours).groupby(local_dates(inputs.index)).sum()
    assert np.allclose(per_day, 8)
    assert measure(plan.hourly, site).cost_eur <= measure(reference.hourly, site).cost_eur


def test_expensive_quarter_inside_a_cheap_hour_is_skipped():
    inputs = make_inputs(price=100.0, fine_days=1)
    price = inputs.price.to_numpy().copy()
    price[8:16] = 20.0
    price[10] = 400.0
    inputs = make_inputs(price=price, fine_days=1)
    plan = solve(inputs, make_site(battery=False), [press(1, min_run=1)])
    on = plan.schedule["press"].to_numpy()
    assert on[10] == 0
    assert on[:96].sum() == 4
    assert set(np.flatnonzero(on[:96])) <= {8, 9, 11, 12, 13, 14, 15}


def test_peak_is_checked_per_quarter_hour():
    site = make_site(peak_charge=120, peak_so_far=900)
    plan = solve(make_inputs(fine_days=1), site, [press(), press(6, id="press-b"), furnace()])
    assert plan.hourly.grid_import.max() <= 900 + TOL
    assert measure(plan.hourly, site).peak_charge_eur == 0


def test_quarter_hour_prices_map_to_steps():
    index = horizon_index(NOW)
    raw = pd.Series(np.arange(96, dtype=float), index=pd.date_range(index[0], periods=96, freq="15min"))
    day2 = pd.Series([10.0, 20.0, 30.0, 40.0], index=pd.date_range(index[96], periods=4, freq="15min"))
    steps = to_steps(pd.concat([raw, day2]), index)
    assert (steps.iloc[:96].to_numpy() == np.arange(96)).all()
    assert steps.iloc[96] == 25.0
    assert steps.iloc[97:].isna().all()


def test_hourly_prices_fill_quarter_hour_steps():
    index = horizon_index(NOW)
    hourly = pd.Series([50.0, 70.0], index=pd.date_range(index[0], periods=2, freq="h"))
    steps = to_steps(hourly, index)
    assert (steps.iloc[:4] == 50).all() and (steps.iloc[4:8] == 70).all()


def test_hourly_weather_is_interpolated_to_quarters():
    index = horizon_index(NOW)
    frame = pd.DataFrame({"irradiance": [0.0, 400.0]}, index=pd.date_range(index[0], periods=2, freq="h"))
    aligned = align(frame, index)
    assert aligned.irradiance.iloc[:5].tolist() == [0.0, 100.0, 200.0, 300.0, 400.0]
