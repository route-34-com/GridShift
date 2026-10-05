import shutil
from dataclasses import replace
from datetime import datetime, timezone

import pytest
from backend.sources.meter import current_peak, parse_meter_csv
from backend.sources.site import ConfigError
from tests.conftest import add_user, make_client, sign_in
from tests.factories import make_site

NOW = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
ISO = "timestamp,import_kw\n2026-03-02T06:00:00Z,800\n2026-03-02T06:15:00Z,1310.5\n2026-03-02T06:30:00Z,900\n"
GERMAN = "timestamp;import_kwh\n16.02.2026 07:00;250,5\n16.02.2026 07:15;312,0\n16.02.2026 07:30;300\n"


def test_reads_iso_kw_readings():
    readings = parse_meter_csv(ISO)
    assert readings.attrs["interval_minutes"] == 15
    assert readings.max() == 1310.5
    assert str(readings.idxmax()) == "2026-03-02 06:15:00+00:00"


def test_reads_german_kwh_readings_as_local_time():
    readings = parse_meter_csv(GERMAN)
    assert readings.max() == pytest.approx(312 * 4)
    assert str(readings.idxmax()) == "2026-02-16 06:15:00+00:00"


def test_iso_dates_are_not_read_day_first():
    readings = parse_meter_csv("timestamp,import_kw\n2026-09-12T10:00:00Z,5\n2026-09-12T10:15:00Z,6\n")
    assert readings.index[0].month == 9


@pytest.mark.parametrize(
    "text, message",
    [
        ("time,kw\n2026-01-01T00:00Z,1\n", "timestamp column"),
        ("timestamp,import_kw\n2026-01-01T00:00:00Z,1\n", "fewer than two"),
        ("timestamp,import_kw\n2026-01-01T00:00:00Z,1\n2026-01-02T00:00:00Z,1\n", "minutes apart"),
    ],
)
def test_rejects_unusable_files(text, message):
    with pytest.raises(ConfigError, match=message):
        parse_meter_csv(text)


def test_meter_peak_wins_when_higher_than_settings():
    peak = current_peak(make_site(peak_charge=120, peak_so_far=1200), parse_meter_csv(ISO), NOW).to_dict()
    assert peak["record_kw"] == 1310.5 and peak["source"] == "meter"
    assert peak["at"] == "2026-03-02T06:15:00+00:00"
    assert peak["annual_eur"] == pytest.approx(1310.5 * 120)
    assert peak["monthly_eur"] == pytest.approx(1310.5 * 120 / 12, abs=0.01)


def test_settings_win_when_meter_is_lower_or_from_last_year():
    site = make_site(peak_charge=120, peak_so_far=1400)
    assert current_peak(site, parse_meter_csv(ISO), NOW).source == "settings"
    old = ISO.replace("2026-", "2025-")
    peak = current_peak(make_site(peak_charge=120, peak_so_far=0), parse_meter_csv(old), NOW)
    assert peak.kw == 0 and peak.meter["rows_this_year"] == 0


@pytest.fixture
def data_settings(settings, tmp_path):
    data = tmp_path / "data"
    shutil.copytree(settings.data_dir, data)
    copied = replace(settings, data_dir=data)
    make_client(copied)  # creates the database tables
    return copied


@pytest.fixture
def planner(data_settings):
    add_user(data_settings, "pia@example.com", "planner")
    return sign_in(data_settings, "pia@example.com")


def test_upload_replaces_meter_data_and_returns_peak(planner):
    assert planner.get("/api/peak").json()["record_kw"] == 1248.0
    response = planner.post("/api/meter", content=ISO.replace("1310.5", "1500"), headers={"content-type": "text/csv"})
    assert response.status_code == 200
    body = response.json()
    assert body["record_kw"] == 1500 and body["monthly_eur"] == 15000
    assert planner.get("/api/peak").json()["record_kw"] == 1500


def test_bad_upload_keeps_existing_data(planner):
    response = planner.post("/api/meter", content="hello", headers={"content-type": "text/csv"})
    assert response.status_code == 422
    assert planner.get("/api/peak").json()["record_kw"] == 1248.0


def test_viewer_sees_peak_but_cannot_upload(data_settings):
    add_user(data_settings, "vic@example.com", "viewer")
    viewer = sign_in(data_settings, "vic@example.com")
    assert viewer.get("/api/peak").status_code == 200
    assert viewer.post("/api/meter", content=ISO, headers={"content-type": "text/csv"}).status_code == 403
    assert make_client(data_settings).get("/api/peak").status_code == 401


def test_uploads_are_audited(admin, data_settings):
    add_user(data_settings, "pia@example.com", "planner")
    planner = sign_in(data_settings, "pia@example.com")
    planner.post("/api/meter", content=ISO, headers={"content-type": "text/csv"})
    planner.post("/api/meter", content="hello", headers={"content-type": "text/csv"})
    found = {e["action"]: e for e in admin.get("/api/audit").json()["entries"]}
    done, failed = found["meter.upload"], found["meter.upload_failed"]
    assert done["user_email"] == "pia@example.com" and done["detail"] == {"rows": 3, "record_kw": 1310.5}
    assert failed["outcome"] == "failure" and "timestamp" in failed["detail"]["error"]
