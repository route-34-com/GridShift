from datetime import datetime, timezone
from pathlib import Path

import pytest

from backend.planner.model import Deadline
from backend.sources.site import ConfigError, load_machines, load_site

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "sample"


def test_sample_site_loads():
    site = load_site(SAMPLE / "site.yaml")
    assert site.solar.kwp == 1500
    assert site.battery.capacity_kwh == 1000


def test_sample_machines_load():
    machines = load_machines(SAMPLE / "machines.yaml")
    assert {m.type for m in machines} == {"always_on", "daily_quota", "deadline"}


def test_missing_file_raises(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load_site(tmp_path / "nope.yaml")


def test_invalid_yaml_raises(tmp_path):
    path = tmp_path / "site.yaml"
    path.write_text("name: [unclosed", encoding="utf-8")
    with pytest.raises(ConfigError, match="not valid YAML"):
        load_site(path)


def test_quota_over_24_hours_names_field(tmp_path):
    path = tmp_path / "machines.yaml"
    path.write_text(
        "machines:\n  - {id: p, name: P, type: daily_quota, power_kw: 10, hours_per_day: 25}\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="hours_per_day"):
        load_machines(path)


def test_deadline_needs_exactly_one_due(tmp_path):
    path = tmp_path / "machines.yaml"
    path.write_text(
        "machines:\n  - {id: f, name: F, type: deadline, power_kw: 10, total_hours: 2}\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="exactly one of due"):
        load_machines(path)


def test_duplicate_ids_rejected(tmp_path):
    path = tmp_path / "machines.yaml"
    path.write_text(
        "machines:\n"
        "  - {id: a, name: A, type: always_on, power_kw: 1}\n"
        "  - {id: a, name: B, type: always_on, power_kw: 1}\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="duplicate machine ids: a"):
        load_machines(path)


def test_empty_machine_list_rejected(tmp_path):
    path = tmp_path / "machines.yaml"
    path.write_text("machines: []\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="non-empty"):
        load_machines(path)


def test_unknown_field_rejected(tmp_path):
    path = tmp_path / "site.yaml"
    path.write_text("name: X\nlatitude: 1\nlongitude: 1\ngrid: {max_import_kw: 1}\ncolour: red\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="colour"):
        load_site(path)


def test_deadline_window_naive_due_is_berlin_time():
    job = Deadline(id="f", name="F", type="deadline", power_kw=1, total_hours=1, due=datetime(2026, 7, 1, 12))
    start = datetime(2026, 7, 1, tzinfo=timezone.utc)
    _, due = job.window(start)
    assert due == datetime(2026, 7, 1, 10, tzinfo=timezone.utc)
