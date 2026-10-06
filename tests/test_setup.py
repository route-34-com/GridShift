from dataclasses import replace

import pandas as pd
import pytest

from backend.api.routes.setup import _carry_sample_peak
from backend.sources.site import load_machines, load_site, save_site
from tests.conftest import PASSWORD, add_user, make_client, sign_in


@pytest.fixture
def live(settings, tmp_path):
    """Sample installed, sample data switched off, the company's folder empty."""
    switchable = replace(settings, sample_dir=settings.data_dir, data_dir=tmp_path / "live")
    client = make_client(switchable)
    assert client.post("/api/auth/setup", json={"email": "admin@example.com", "password": PASSWORD, "name": "Ada"}).status_code == 200
    client.put("/api/dataset", json={"active": "live"})
    return switchable, client


def history_csv(days=8, sep=";", decimal=","):
    stamps = pd.date_range("2026-09-01", periods=days * 24, freq="h", tz="UTC")
    rows = [f"{t:%Y-%m-%dT%H:%M:%SZ}{sep}{str(11000.5 + i % 7).replace('.', decimal)}" for i, t in enumerate(stamps)]
    return f"timestamp{sep}load_kw\n" + "\n".join(rows)


def audit(client, action):
    return client.get("/api/audit", params={"action": action}).json()["entries"]


def test_empty_company_folder_lists_what_is_missing(live):
    _, client = live
    status = client.get("/api/setup").json()
    assert status["editable"] and not status["ready"]
    assert status["site"] == {"ok": False, "missing": True, "error": None}
    assert status["prices"] == {"ok": True, "shared": True}


def test_start_from_sample_then_plan(live):
    settings, client = live
    status = client.post("/api/setup/copy-sample").json()
    assert status["ready"] and status["machines"]["count"] == len(load_machines(settings.sample_dir / "machines.yaml"))
    assert client.get("/api/dataset").json()["live"]["available"] is True
    assert client.post("/api/runs").status_code == 201
    assert audit(client, "config.copy_sample")[0]["detail"]["copied"] == ["site.yaml", "machines.yaml", "demand_history.csv"]
    # A second copy never overwrites what the company has edited.
    client.post("/api/setup/copy-sample")
    assert audit(client, "config.copy_sample")[0]["detail"]["copied"] == []


def test_copied_site_gets_the_sample_peak_record_when_it_has_none(live):
    settings, client = live
    assert client.post("/api/setup/copy-sample").json()["peak_unknown"] is False
    assert load_site(settings.site_path).grid.peak_so_far_kw == 1200  # an existing record is kept
    site = load_site(settings.site_path)
    save_site(settings.site_path, site.model_copy(update={"grid": site.grid.model_copy(update={"peak_so_far_kw": 0})}))
    _carry_sample_peak(settings)
    assert load_site(settings.site_path).grid.peak_so_far_kw == 1248  # highest reading in the sample meter data


def test_unknown_peak_record_is_flagged(live):
    _, client = live
    client.post("/api/setup/copy-sample")
    site = client.get("/api/config").json()["site"]
    site["grid"]["peak_so_far_kw"] = 0
    assert client.put("/api/setup/site", json=site).json()["peak_unknown"] is True


def test_site_is_validated_and_saved(live):
    settings, client = live
    client.post("/api/setup/copy-sample")
    site = client.get("/api/config").json()["site"]
    bad = {**site, "latitude": 200}
    response = client.put("/api/setup/site", json=bad)
    assert response.status_code == 422 and "latitude" in response.json()["detail"]
    assert audit(client, "config.rejected")[0]["entity_id"] == "site"
    site["name"] = "Werk Lägerdorf"
    site["grid"]["peak_charge_eur_per_kw_year"] = 90
    assert client.put("/api/setup/site", json=site).status_code == 200
    saved = load_site(settings.site_path)
    assert saved.name == "Werk Lägerdorf" and saved.grid.peak_charge_eur_per_kw_year == 90


def test_machines_are_added_changed_and_removed(live):
    settings, client = live
    client.post("/api/setup/copy-sample")
    machines = client.get("/api/config").json()["machines"]
    removed = machines.pop()
    machines[0]["power_kw"] = machines[0]["power_kw"] + 10
    machines.append({"id": "cement-mill-3", "name": "Cement mill 3", "type": "deadline", "power_kw": 3000, "total_hours": 12, "due": "2026-10-09T18:00:00", "min_run_hours": 3})
    assert client.put("/api/setup/machines", json={"machines": machines}).status_code == 200
    detail = audit(client, "config.machines")[0]["detail"]
    assert detail == {"added": ["cement-mill-3"], "removed": [removed["id"]], "changed": [machines[0]["id"]]}
    assert {m.id for m in load_machines(settings.machines_path)} >= {"cement-mill-3"}


@pytest.mark.parametrize(
    "machines, reason",
    [
        ([{"id": "mill", "name": "Mill", "type": "daily_quota", "power_kw": 100, "hours_per_day": 2, "min_run_hours": 4}], "min_run_hours"),
        ([{"id": "a", "name": "A", "type": "always_on", "power_kw": 5}, {"id": "a", "name": "B", "type": "always_on", "power_kw": 5}], "duplicate"),
        ([], "non-empty"),
    ],
)
def test_bad_machine_lists_are_refused(live, machines, reason):
    _, client = live
    response = client.put("/api/setup/machines", json={"machines": machines})
    assert response.status_code == 422 and reason in response.json()["detail"]


def test_load_history_upload(live):
    settings, client = live
    status = client.post("/api/setup/demand", content=history_csv(), headers={"content-type": "text/csv"}).json()
    assert status["demand"]["ok"] and status["demand"]["rows"] == 192
    assert pd.read_csv(settings.demand_path).columns.tolist() == ["timestamp", "load_kw"]
    short = client.post("/api/setup/demand", content=history_csv(days=3), headers={"content-type": "text/csv"})
    assert short.status_code == 422 and "one week" in short.json()["detail"]


def test_sample_cannot_be_edited_and_viewers_cannot_edit(live):
    settings, client = live
    client.put("/api/dataset", json={"active": "sample"})
    assert client.put("/api/setup/machines", json={"machines": []}).status_code == 409
    client.put("/api/dataset", json={"active": "live"})
    add_user(settings, "vic@example.com", "viewer")
    viewer = sign_in(settings, "vic@example.com")
    assert viewer.get("/api/setup").status_code == 200
    assert viewer.post("/api/setup/copy-sample").status_code == 403
