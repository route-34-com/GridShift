import sqlite3
from dataclasses import replace

import pytest

from backend.datasets import LIVE, SAMPLE, resolve
from backend.store import Store
from tests.conftest import PASSWORD, add_user, make_client, sign_in


@pytest.fixture
def switchable(settings, tmp_path):
    """Sample data installed; the company's own folder still empty."""
    return replace(settings, sample_dir=settings.data_dir, data_dir=tmp_path / "live")


def test_old_runs_are_kept_out_of_both_data_sets(tmp_path):
    path = tmp_path / "old.db"
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE runs (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, horizon_start TEXT NOT NULL, status TEXT NOT NULL, payload TEXT NOT NULL)")
    db.execute("""INSERT INTO runs (created_at, horizon_start, status, payload) VALUES ('t', 'h', 'ok', '{"id": 1}')""")
    db.commit()
    db.close()
    store = Store(path)
    assert store.latest_run() is None and store.scoped(SAMPLE).latest_run() is None


def test_runs_and_weather_stay_in_their_data_set(tmp_path):
    live = Store(tmp_path / "x.db")
    sample = live.scoped(SAMPLE)
    sample.save_run({"created_at": "t", "horizon_start": "h", "status": "ok"})
    assert live.latest_run() is None and live.list_runs() == []
    assert sample.latest_run()["status"] == "ok"
    run_id = sample.list_runs()[0]["id"]
    assert live.get_run(run_id) is None


def test_sample_is_on_by_default_when_installed(switchable, tmp_path):
    store = Store(switchable.db_path)
    data = resolve(switchable, store)
    assert data.name == SAMPLE and data.settings.data_dir == switchable.sample_dir
    assert resolve(replace(switchable, sample_dir=None), store).name == LIVE


def test_admin_switches_data_sets_and_it_is_audited(switchable):
    admin = make_client(switchable)
    assert admin.post("/api/auth/setup", json={"email": "admin@example.com", "password": PASSWORD, "name": "Ada"}).status_code == 200
    state = admin.get("/api/dataset").json()
    assert state == {"active": "sample", "switchable": True, "sample": {"available": True}, "live": {"available": False}}
    assert admin.post("/api/runs").status_code == 201
    assert admin.get("/api/runs/latest").status_code == 200

    assert admin.put("/api/dataset", json={"active": "live"}).json()["active"] == "live"
    assert admin.get("/api/runs/latest").status_code == 404
    assert admin.post("/api/runs").status_code == 502  # no real site data yet

    admin.put("/api/dataset", json={"active": "sample"})
    assert admin.get("/api/runs/latest").status_code == 200
    switches = admin.get("/api/audit", params={"action": "data.switch"}).json()["entries"]
    assert [e["detail"]["to"] for e in switches] == ["sample", "live"]


def test_only_admins_switch(switchable):
    make_client(switchable)
    add_user(switchable, "pia@example.com", "planner")
    planner = sign_in(switchable, "pia@example.com")
    assert planner.get("/api/dataset").json()["active"] == "sample"
    assert planner.put("/api/dataset", json={"active": "live"}).status_code == 403
    assert planner.put("/api/dataset", json={"active": "other"}).status_code in (403, 422)


def test_sample_meter_data_cannot_be_replaced(switchable):
    admin = make_client(switchable)
    admin.post("/api/auth/setup", json={"email": "admin@example.com", "password": PASSWORD, "name": "Ada"})
    meter = switchable.sample_dir / "meter_data.csv"
    before = meter.read_bytes() if meter.exists() else None
    response = admin.post("/api/meter", content="timestamp,import_kw\n2026-03-02T06:00:00Z,1\n2026-03-02T06:15:00Z,2\n", headers={"content-type": "text/csv"})
    assert response.status_code == 409
    assert (meter.read_bytes() if meter.exists() else None) == before
