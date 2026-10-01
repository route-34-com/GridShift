from dataclasses import replace

import numpy as np
import pandas as pd

from backend.jobs import execute
from backend.notify.email import render_plan_email, send_email
from backend.settings import Smtp
from tests.conftest import NOW, broken, fake_prices, good_sources, hours


def test_full_run_produces_complete_payload(settings, store):
    run = execute(settings, store, NOW, good_sources())
    assert run["status"] == "ok"
    assert len(run["hourly"]) == 168
    assert len(run["daily"]) == 7
    assert run["summary"]["savings_eur"] >= 0
    assert run["blocks"]
    assert run["sources"] == {"price": "published", "site_weather": "live", "national_weather": "live"}
    assert run["email"]["status"] == "disabled"
    assert store.latest_run()["id"] == run["id"]


def test_price_outage_falls_back_to_estimates(settings, store):
    sources = replace(good_sources(), day_ahead=broken)
    run = execute(settings, store, NOW, sources)
    assert run["sources"]["price"] == "estimated"
    assert any(a["kind"] == "price_fallback" for a in run["alerts"])
    assert all(h["price_source"] == "estimate" for h in run["hourly"])


def test_partial_prices_are_flagged(settings, store):
    sources = replace(good_sources(), day_ahead=lambda s, e: fake_prices(s, e)[:10])
    run = execute(settings, store, NOW, sources)
    assert run["sources"]["price"] == "partial"
    assert any("not fully published" in w for w in run["warnings"])


def test_weather_outage_uses_cache(settings, store):
    execute(settings, store, NOW, good_sources())
    sources = replace(good_sources(), site_weather=broken, national_weather=broken)
    run = execute(settings, store, NOW, sources)
    assert run["status"] != "failed"
    assert run["sources"]["site_weather"] == "cached"
    assert run["sources"]["national_weather"] == "cached"


def test_weather_outage_without_cache_fails_cleanly(settings, store):
    sources = replace(good_sources(), site_weather=broken)
    run = execute(settings, store, NOW, sources)
    assert run["status"] == "failed"
    assert "no cached forecast" in run["error"]
    assert store.latest_run()["status"] == "failed"
    assert store.latest_run(successful=True) is None


def test_national_outage_without_cache_uses_profile(settings, store):
    sources = replace(good_sources(), national_weather=broken)
    run = execute(settings, store, NOW, sources)
    assert run["sources"]["national_weather"] == "profile"


def test_missing_config_records_failure(settings, store, tmp_path):
    bad = replace(settings, data_dir=tmp_path / "missing")
    run = execute(bad, store, NOW, good_sources())
    assert run["status"] == "failed"
    assert "not found" in run["error"]


def test_plan_change_alert_compares_with_previous_preview(settings, store):
    execute(settings, store, NOW - pd.Timedelta(days=1), good_sources())
    cheap_midday = lambda s, e: pd.Series(np.where(hours(s, e)[:24].tz_convert("Europe/Berlin").hour.isin(range(10, 16)), -20.0, 300.0), index=hours(s, e)[:24])
    run = execute(settings, store, NOW, replace(good_sources(), day_ahead=cheap_midday))
    assert any(a["kind"] == "plan_change" for a in run["alerts"])


def test_email_renders_with_alerts(settings, store):
    sources = replace(good_sources(), day_ahead=broken)
    run = execute(settings, store, NOW, sources)
    subject, html = render_plan_email(run)
    assert subject.startswith("[1 alert]") and "saved this week" in subject
    assert run["daily"][0]["label"] in html
    assert "Needs attention" in html


def test_email_without_host_is_disabled():
    smtp = Smtp("", 587, "", "", "x@example.com", True)
    assert send_email(smtp, ["a@example.com"], "s", "<p>x</p>") == "disabled"


def test_email_unreachable_host_reports_failure():
    smtp = Smtp("127.0.0.1", 1, "", "", "x@example.com", False)
    assert send_email(smtp, ["a@example.com"], "s", "<p>x</p>").startswith("failed")
