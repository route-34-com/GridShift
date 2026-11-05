from datetime import datetime, timedelta, timezone

import pandas as pd

from backend.forecast.horizon import day_bounds
from backend.services.today import today_plan
from backend.store import Store
from tests.test_api import signed_in

NOW = datetime(2026, 11, 5, 8, 0, tzinfo=timezone.utc)
TODAY, TOMORROW = day_bounds(NOW)
MACHINES = [{"id": "mill", "name": "Mill", "type": "daily_quota", "power_kw": 1000}]


def block(start, end):
    hours = (end - start) / pd.Timedelta(hours=1)
    return {
        "machine_id": "mill",
        "machine_name": "Mill",
        "start": start.isoformat(),
        "end": end.isoformat(),
        "hours": hours,
        "energy_kwh": 1000 * hours,
        "avg_price": 50.0,
        "renewable_share": 0.1,
        "reason": "x: y",
    }


def payload(start, days=7, blocks=(), status="ok"):
    index = pd.date_range(start, periods=days * 24, freq="h")
    return {
        "created_at": (start - timedelta(hours=11)).isoformat(),
        "horizon_start": start.isoformat(),
        "horizon_end": (index[-1] + timedelta(hours=1)).isoformat(),
        "status": status,
        "machines": MACHINES,
        "hourly": [{"ts": t.isoformat(), "hours": 1, "price": 50.0, "price_source": "actual"} for t in index],
        "blocks": list(blocks),
    }


def test_a_plan_made_this_morning_does_not_replace_todays_plan(store):
    made_for_today = store.save_run(payload(TODAY))
    store.save_run(payload(TOMORROW))
    plan = today_plan(store, NOW)
    assert plan["run"]["id"] == made_for_today
    assert plan["hourly"][0]["ts"] == TODAY.isoformat()
    assert len(plan["hourly"]) == 24


def test_the_newest_run_for_today_wins(store):
    store.save_run(payload(TODAY))
    newest = store.save_run(payload(TODAY))
    assert today_plan(store, NOW)["run"]["id"] == newest


def test_an_older_run_still_covers_today_when_yesterdays_is_missing(store):
    older = store.save_run(payload(TODAY - timedelta(days=2)))
    plan = today_plan(store, NOW)
    assert plan["run"]["id"] == older
    assert plan["hourly"][0]["ts"] == TODAY.isoformat()


def test_failed_runs_are_skipped(store):
    good = store.save_run(payload(TODAY))
    store.save_run(payload(TODAY, status="failed"))
    assert today_plan(store, NOW)["run"]["id"] == good


def test_no_plan_when_no_run_covers_today(store):
    assert today_plan(store, NOW) is None
    store.save_run(payload(TOMORROW))
    assert today_plan(store, NOW) is None
    store.save_run(payload(TODAY - timedelta(days=10)))
    assert today_plan(store, NOW) is None


def test_blocks_are_clipped_to_today(store):
    overnight = block(TODAY + timedelta(hours=21), TODAY + timedelta(hours=37))
    earlier = block(TODAY - timedelta(hours=2), TODAY + timedelta(hours=2))
    tomorrow = block(TOMORROW + timedelta(hours=1), TOMORROW + timedelta(hours=3))
    store.save_run(payload(TODAY - timedelta(days=1), blocks=[earlier, overnight, tomorrow]))
    blocks = today_plan(store, NOW)["blocks"]
    assert [b["hours"] for b in blocks] == [2, 3]
    assert blocks[0]["start"] == TODAY.isoformat()
    assert blocks[1]["end"] == TOMORROW.isoformat()
    assert blocks[1]["energy_kwh"] == 3000
    assert blocks[1]["avg_price"] == 50.0


def test_short_dst_day_has_23_hours(store):
    now = datetime(2027, 3, 28, 12, tzinfo=timezone.utc)
    start, end = day_bounds(now)
    store.save_run(payload(start))
    assert end - start == pd.Timedelta(hours=23)
    assert len(today_plan(store, now)["hourly"]) == 23


def test_today_endpoint_returns_todays_plan(settings):
    now = datetime.now(timezone.utc)
    start, end = day_bounds(now)
    client = signed_in(settings)
    assert client.get("/api/runs/today").json() is None
    run_id = Store(settings.db_path).save_run(payload(start))
    Store(settings.db_path).save_run(payload(end))
    body = client.get("/api/runs/today").json()
    assert body["run"]["id"] == run_id
    assert body["hourly"][0]["ts"] == start.isoformat()
