from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

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


def test_summary_includes_peak_charge(settings, store):
    run = execute(settings, store, NOW, good_sources())
    summary = run["summary"]
    peak = summary["peak"]
    assert (peak["record_kw"], peak["source"], peak["monthly_eur"]) == (1248.0, "meter", 12480.0)
    for side in ("optimized", "baseline"):
        m = summary[side]
        assert m["total_cost_eur"] == pytest.approx(m["cost_eur"] + m["peak_charge_eur"], abs=0.01)
    energy = summary["baseline"]["cost_eur"] - summary["optimized"]["cost_eur"]
    peak = summary["baseline"]["peak_charge_eur"] - summary["optimized"]["peak_charge_eur"]
    assert summary["savings_eur"] == pytest.approx(energy, abs=0.01)
    assert summary["peak_savings_eur"] == pytest.approx(peak, abs=0.01)


def test_hourly_rows_carry_site_weather(settings, store):
    run = execute(settings, store, NOW, good_sources())
    noon = next(h for h in run["hourly"] if pd.Timestamp(h["ts"]).tz_convert("Europe/Berlin").hour == 12)
    assert noon["sunlight_w_m2"] > 600 and noon["cloud_cover_pct"] == 40.0 and noon["temperature_c"] == 14.0
    assert noon["wind_ms"] == pytest.approx(6.0, abs=0.05)  # sample hub is at 100 m
    assert run["baseline_hourly"][0]["wind_ms"] == run["hourly"][0]["wind_ms"]


def test_weather_cached_without_cloud_cover_still_plans(settings, store):
    old_style = lambda site, s, e: good_sources().site_weather(site, s, e).drop(columns="cloud_cover")
    execute(settings, store, NOW, replace(good_sources(), site_weather=old_style))
    run = execute(settings, store, NOW, replace(good_sources(), site_weather=broken))
    assert run["sources"]["site_weather"] == "cached"
    assert all(h["cloud_cover_pct"] is None for h in run["hourly"])
    assert run["hourly"][0]["sunlight_w_m2"] is not None


def test_today_is_included_for_the_now_marker(settings, store):
    run = execute(settings, store, NOW, good_sources())
    today = run["today"]
    assert len(today) == 24 and today[-1]["ts"] < run["horizon_start"] <= run["hourly"][0]["ts"]
    assert pd.Timestamp(today[0]["ts"]).tz_convert("Europe/Berlin").hour == 0
    assert all(h["price_source"] == "actual" and h["price"] is not None for h in today)
    assert today[12]["sunlight_w_m2"] > 0 and today[0]["wind_ms"] is not None


def test_today_survives_outages(settings, store):
    run = execute(settings, store, NOW, replace(good_sources(), day_ahead=broken))
    assert run["status"] != "failed"
    assert all(h["price"] is None and h["price_source"] is None for h in run["today"])


def test_plan_survives_when_peak_protection_cannot_be_solved(settings, store, monkeypatch):
    import backend.pipeline as pipeline
    from backend.planner.optimizer import PlannerError

    real = pipeline.optimize
    calls = []

    def flaky(inputs, site, requirements, time_limit):
        calls.append(site.grid.peak_charge_eur_per_kw_year)
        if site.grid.peak_charge_eur_per_kw_year > 0:
            raise PlannerError("Solver found no feasible plan (Time limit reached)")
        return real(inputs, site, requirements, time_limit)

    monkeypatch.setattr(pipeline, "optimize", flaky)
    run = execute(settings, store, NOW, good_sources())
    assert run["status"] != "failed" and calls == [120.0, 0]
    assert any(a["kind"] == "peak_skipped" for a in run["alerts"])
    assert run["summary"]["optimized"]["peak_charge_eur"] >= 0


def test_price_outage_falls_back_to_estimates(settings, store):
    sources = replace(good_sources(), day_ahead=broken)
    run = execute(settings, store, NOW, sources)
    assert run["sources"]["price"] == "estimated"
    assert any(a["kind"] == "price_fallback" for a in run["alerts"])
    assert all(h["price_source"] == "estimate" for h in run["hourly"])


def test_backup_source_supplies_real_prices(settings, store):
    sources = replace(good_sources(), day_ahead=broken, backup_day_ahead=fake_prices)
    run = execute(settings, store, NOW, sources)
    assert run["sources"]["price"] == "published"
    assert any(a["kind"] == "price_backup" and "aWATTar" in a["message"] for a in run["alerts"])
    assert not any(a["kind"] == "price_fallback" for a in run["alerts"])
    assert run["hourly"][0]["price_source"] == "actual"


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
