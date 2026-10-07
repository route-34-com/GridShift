from dataclasses import replace

import pytest

from backend import datafiles
from backend.datasets import resolve
from backend.store import Store
from tests.conftest import PASSWORD, TEST_DATABASE_URL, make_client


def test_daily_cron_needs_the_secret(settings):
    client = make_client(replace(settings, cron_secret="s3cret"))
    assert client.get("/api/cron/daily").status_code == 401
    assert client.get("/api/cron/daily", headers={"authorization": "Bearer wrong"}).status_code == 401
    assert make_client(settings).get("/api/cron/daily", headers={"authorization": "Bearer "}).status_code == 401


def test_daily_cron_runs_and_audits_the_plan(settings):
    client = make_client(replace(settings, cron_secret="s3cret"))
    response = client.get("/api/cron/daily", headers={"authorization": "Bearer s3cret"})
    assert response.status_code == 200 and response.json()["status"] != "failed"
    client.post("/api/auth/setup", json={"email": "admin@example.com", "password": PASSWORD, "name": "Ada"})
    entry = client.get("/api/audit", params={"action": "plan.run"}).json()["entries"][0]
    assert entry["detail"]["trigger"] == "scheduled"


def test_audit_search_ignores_case(settings):
    client = make_client(settings)
    client.post("/api/auth/setup", json={"email": "admin@example.com", "password": PASSWORD, "name": "Ada"})
    assert client.get("/api/audit", params={"q": "ADMIN@EXAMPLE"}).json()["total"] > 0


@pytest.mark.skipif(not TEST_DATABASE_URL, reason="needs GRIDSHIFT_TEST_DATABASE_URL")
def test_company_files_survive_a_fresh_disk(settings, tmp_path):
    live = replace(settings, data_dir=tmp_path / "live")
    store = Store(live.db_path)
    live.data_dir.mkdir()
    (live.data_dir / "site.yaml").write_text("name: Kept\n", encoding="utf-8")
    datafiles.save(live)

    (live.data_dir / "site.yaml").unlink()
    (live.data_dir / "machines.yaml").write_text("stale\n", encoding="utf-8")
    datafiles.forget()
    resolve(live, store)

    assert (live.data_dir / "site.yaml").read_text(encoding="utf-8") == "name: Kept\n"
    assert not (live.data_dir / "machines.yaml").exists()
