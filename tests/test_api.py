from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from backend.api.main import create_app
from tests.conftest import broken, good_sources


@pytest.fixture
def client(settings):
    return TestClient(create_app(settings, good_sources()))


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_no_runs_yet_returns_404_with_guidance(client):
    response = client.get("/api/runs/latest")
    assert response.status_code == 404
    assert "Run the planner" in response.json()["detail"]
    assert client.get("/api/status").json()["latest"] is None


def test_run_then_read_everything(client):
    created = client.post("/api/runs")
    assert created.status_code == 201
    body = created.json()
    assert "hourly" not in body and body["summary"]["savings_eur"] >= 0
    hourly = client.get("/api/runs/latest/hourly").json()
    assert len(hourly["plan"]) == 168 and len(hourly["baseline"]) == 168
    blocks = client.get("/api/runs/latest/blocks").json()
    assert blocks["plan"] and {"machine_id", "start", "end", "reason"} <= blocks["plan"][0].keys()
    assert client.get(f"/api/runs/{body['id']}").json()["id"] == body["id"]
    assert len(client.get("/api/runs").json()) == 1
    email = client.get("/api/runs/latest/email")
    assert email.status_code == 200 and "GridShift" in email.text


def test_failed_first_run_returns_502_and_reports_failure(settings):
    client = TestClient(create_app(settings, replace(good_sources(), site_weather=broken)))
    response = client.post("/api/runs")
    assert response.status_code == 502
    assert "no cached forecast" in response.json()["detail"]
    assert client.get("/api/status").json()["last_failure"]["status"] == "failed"
    assert client.get("/api/runs/latest").status_code == 404


def test_failed_run_keeps_last_good_plan(settings, tmp_path):
    app = create_app(settings, good_sources())
    client = TestClient(app)
    good = client.post("/api/runs").json()
    app.state.gridshift.settings = replace(settings, data_dir=tmp_path / "missing")
    assert client.post("/api/runs").status_code == 502
    assert client.get("/api/status").json()["last_failure"]["error"]
    assert client.get("/api/runs/latest").json()["id"] == good["id"]


def test_concurrent_run_is_rejected(client):
    lock = client.app.state.gridshift.lock
    lock.acquire()
    try:
        response = client.post("/api/runs")
        assert response.status_code == 409
        assert client.get("/api/status").json()["running"] is True
    finally:
        lock.release()


def test_unknown_run_404(client):
    assert client.get("/api/runs/999").status_code == 404


def test_config_endpoint(client):
    body = client.get("/api/config").json()
    assert body["site"]["battery"]["capacity_kwh"] == 1000
    assert len(body["machines"]) == 8


def test_invalid_config_returns_422(settings, tmp_path):
    bad = replace(settings, data_dir=tmp_path)
    (tmp_path / "site.yaml").write_text("name: x\n", encoding="utf-8")
    response = TestClient(create_app(bad, good_sources())).get("/api/config")
    assert response.status_code == 422
    assert "site.yaml" in response.json()["detail"]
