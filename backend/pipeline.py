"""Run one planning cycle: fetch data, forecast, optimize, compare and store."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from backend.forecast.demand import base_demand
from backend.forecast.horizon import horizon_index, local_dates, today_index
from backend.forecast.price_estimate import estimator_for, price_forecast
from backend.forecast.renewables import hub_wind_speed, solar_kw, wind_kw
from backend.planner.baseline import baseline
from backend.planner.explain import explain_blocks
from backend.planner.inputs import PlanInputs, PlanResult
from backend.planner.metrics import Metrics, daily_costs, measure
from backend.planner.model import LOCAL_TZ, AlwaysOn, Machine, Site
from backend.planner.optimizer import PlannerError, optimize
from backend.planner.requirements import build_requirements
from backend.settings import Settings
from backend.sources import price, weather
from backend.sources.demand_history import load_demand_history
from backend.sources.http import SourceError
from backend.sources.meter import current_peak, load_meter
from backend.sources.site import ConfigError, load_machines, load_site
from backend.store import Store

PLAN_CHANGE_THRESHOLD = 0.2


class RunError(RuntimeError):
    """Raised when a run cannot produce a plan."""


@dataclass
class Sources:
    """External data fetchers, replaceable in tests or for client systems."""

    day_ahead: Callable = price.fetch_day_ahead
    backup_day_ahead: Callable | None = price.fetch_day_ahead_awattar
    site_weather: Callable = weather.fetch_site_weather
    national_weather: Callable = weather.fetch_national_weather


@dataclass
class Notes:
    """Warnings, alerts and source statuses collected during a run."""

    warnings: list[str] = field(default_factory=list)
    alerts: list[dict] = field(default_factory=list)
    sources: dict[str, str] = field(default_factory=dict)

    def alert(self, kind: str, level: str, message: str) -> None:
        """Record an alert."""
        self.alerts.append({"kind": kind, "level": level, "message": message})


def _cached_weather(store: Store, kind: str, index: pd.DatetimeIndex) -> pd.DataFrame | None:
    cached = store.load_weather(kind)
    if cached is None or cached.empty:
        return None
    aligned = cached.reindex(index)
    profile = cached.groupby(cached.index.hour).mean()
    fill = pd.DataFrame([profile.loc[h] if h in profile.index else profile.mean() for h in index.hour], index=index)
    return aligned.fillna(fill)


def _fetch_prices(sources: Sources, index: pd.DatetimeIndex, notes: Notes) -> pd.Series | None:
    start, end = index[0].to_pydatetime(), (index[-1] + pd.Timedelta(hours=1)).to_pydatetime()
    try:
        actual = sources.day_ahead(start, end)
    except SourceError as exc:
        primary_error = exc
        try:
            if sources.backup_day_ahead is None:
                raise SourceError("no backup price source configured")
            actual = sources.backup_day_ahead(start, end)
        except SourceError as backup_error:
            notes.sources["price"] = "estimated"
            notes.alert(
                "price_fallback",
                "warning",
                f"Real market prices couldn't be downloaded, so every hour uses GridShift's weather-based estimate. "
                f"Energy-Charts: {primary_error}. aWATTar: {backup_error}.",
            )
            return None
        notes.alert("price_backup", "info", f"Energy-Charts didn't respond, so the real market prices came from aWATTar instead ({primary_error}).")
    first_day = (local_dates(index) == local_dates(index)[0]).sum()
    known = actual.reindex(index).notna()
    if known[:first_day].all():
        notes.sources["price"] = "published"
    else:
        notes.sources["price"] = "partial"
        notes.warnings.append(f"Day-ahead prices for the first day are not fully published yet ({int(known[:first_day].sum())}/{first_day} h); missing hours are estimated.")
    return actual


def _fetch_weather(fetch: Callable, kind: str, store: Store, index: pd.DatetimeIndex, notes: Notes, required: bool) -> pd.DataFrame | None:
    try:
        frame = fetch(index[0].to_pydatetime(), (index[-1] + pd.Timedelta(hours=1)).to_pydatetime())
        store.save_weather(kind, frame)
        notes.sources[kind] = "live"
        return frame
    except SourceError as exc:
        cached = _cached_weather(store, kind, index)
        if cached is not None:
            notes.sources[kind] = "cached"
            notes.alert(f"{kind}_fallback", "warning", f"{kind.replace('_', ' ').title()} forecast unavailable ({exc}); using the last stored forecast.")
            return cached
        if required:
            raise RunError(f"Site weather forecast unavailable and no cached forecast exists: {exc}") from exc
        notes.sources[kind] = "profile"
        notes.warnings.append("National weather unavailable; prices beyond tomorrow use typical weekday-hour values.")
        return None


def _sentence(parts: list[str]) -> str:
    text = ", ".join(parts)
    return text[:1].upper() + text[1:]


def _day_label(day) -> str:
    return pd.Timestamp(day).strftime("%a %d %b")


def _battery_note(day: pd.DataFrame, site: Site) -> str:
    if site.battery.capacity_kwh <= 0:
        return "No battery configured."
    charge, discharge = day["charge"].sum(), day["discharge"].sum()
    if charge < 1 and discharge < 1:
        return f"Idle; holds {day['soc'].iloc[-1] / site.battery.capacity_kwh:.0%} charge."
    cheap = day[day["charge"] > 1]
    renewable_charge = (np.minimum(cheap["charge"], (cheap["solar"] + cheap["wind"] - cheap["demand"] - cheap["flexible"]).clip(lower=0))).sum()
    source = "mostly from surplus solar/wind" if renewable_charge > charge / 2 else "mostly in cheap grid hours"
    return f"Charges {charge:,.0f} kWh ({source}), discharges {discharge:,.0f} kWh in expensive hours, ends the day {day['soc'].iloc[-1] / site.battery.capacity_kwh:.0%} full."


def _daily(plan: PlanResult, ref: PlanResult, site: Site) -> list[dict]:
    hourly = plan.hourly
    dates = local_dates(hourly.index)
    costs, ref_costs = daily_costs(hourly, site), daily_costs(ref.hourly, site)
    renewable = (hourly["solar"] + hourly["wind"]).groupby(dates).sum()
    week_renewable, week_price = renewable.mean(), hourly["price"].mean()
    rows = []
    for day in dict.fromkeys(dates):
        mask = dates == day
        part, ref_part = hourly[mask], ref.hourly[mask]
        metrics = measure(part, site)
        avg_price = float(part["price"].mean())
        flex, ref_flex = part["flexible"].sum(), ref_part["flexible"].sum()
        outlook = []
        if renewable[day] >= 1.25 * week_renewable and renewable[day] > 0:
            outlook.append(f"strong solar/wind ({renewable[day] / 1000:,.1f} MWh on site)")
        elif renewable[day] <= 0.75 * week_renewable:
            outlook.append(f"weak solar/wind ({renewable[day] / 1000:,.1f} MWh on site)")
        else:
            outlook.append(f"average solar/wind ({renewable[day] / 1000:,.1f} MWh)")
        if avg_price < 0.9 * week_price:
            outlook.append("cheap grid")
        elif avg_price > 1.1 * week_price:
            outlook.append("expensive grid")
        if flex > ref_flex * 1.1 + 1:
            outlook.append(f"flexible jobs pulled in (+{(flex - ref_flex) / 1000:,.1f} MWh)")
        elif flex < ref_flex * 0.9 - 1:
            outlook.append(f"flexible jobs moved to better days (−{(ref_flex - flex) / 1000:,.1f} MWh)")
        rows.append(
            {
                "date": day.isoformat(),
                "label": _day_label(day),
                "start": hourly.index[mask][0].isoformat(),
                "cost_eur": float(costs[day]),
                "baseline_cost_eur": float(ref_costs[day]),
                "savings_eur": round(float(ref_costs[day] - costs[day]), 2),
                "renewable_kwh": round(float(renewable[day]), 1),
                "renewable_share": metrics.renewable_share,
                "avg_price": round(avg_price, 2),
                "price_estimated": bool((part["price_source"] == "estimate").any()),
                "flexible_kwh": round(float(flex), 1),
                "outlook": _sentence(outlook),
                "battery_note": _battery_note(part, site),
            }
        )
    return rows


def _machines(plan: PlanResult, ref: PlanResult, machines: list[Machine], requirements) -> list[dict]:
    required = {r.machine.id: sum(g.required for g in r.groups) for r in requirements}
    price = plan.hourly["price"]
    rows = []
    for m in machines:
        row = {"id": m.id, "name": m.name, "type": m.type, "power_kw": m.power_kw}
        if m.id in plan.schedule:
            on, ref_on = plan.schedule[m.id], ref.schedule[m.id]
            row |= {
                "scheduled_hours": int(on.sum()),
                "required_hours": required[m.id],
                "avg_price": round(float(price[on == 1].mean()), 2) if on.sum() else None,
                "baseline_avg_price": round(float(price[ref_on == 1].mean()), 2) if ref_on.sum() else None,
            }
        rows.append(row)
    return rows


def _plan_change(store: Store, plan: PlanResult, notes: Notes) -> None:
    previous = store.latest_run(successful=True)
    if not previous:
        return
    old = pd.Series({pd.Timestamp(r["ts"]): r["flexible"] for r in previous["hourly"]})
    dates = local_dates(plan.hourly.index)
    first = plan.hourly["flexible"][dates == dates[0]]
    overlap = old.reindex(first.index).dropna()
    if overlap.empty or overlap.sum() <= 0:
        return
    change = float((first.reindex(overlap.index) - overlap).abs().sum() / overlap.sum())
    if change > PLAN_CHANGE_THRESHOLD:
        notes.alert("plan_change", "info", f"Tomorrow's plan moved {change:.0%} of flexible energy compared with yesterday's preview.")


def _meter_readings(settings: Settings, notes: Notes) -> pd.Series | None:
    try:
        return load_meter(settings.meter_path)
    except ConfigError as exc:
        notes.alert("meter", "warning", f"Meter data could not be read ({exc}); using the peak from the site settings.")
        return None


def _peak_notes(site: Site, plan: Metrics, notes: Notes) -> None:
    grid = site.grid
    if grid.peak_charge_eur_per_kw_year <= 0:
        return
    if grid.peak_so_far_kw <= 0:
        notes.warnings.append("No peak record for this year yet, so this week's highest hour counts as a new yearly peak. Upload meter data or set peak_so_far_kw from the latest bill.")
    elif plan.peak_charge_eur > 0:
        notes.alert(
            "new_peak",
            "warning",
            f"Plan raises the yearly peak from {grid.peak_so_far_kw:,.0f} to {plan.peak_import_kw:,.0f} kW, adding €{plan.peak_charge_eur:,.0f} to this year's peak charge. Staying under it would cost more.",
        )


def _weather_table(weather: pd.DataFrame, site: Site) -> pd.DataFrame:
    """Return the site weather shown next to the plan: sunlight on the panels, clouds, hub-height wind and temperature."""
    return pd.DataFrame(
        {
            "sunlight_w_m2": weather["irradiance"].clip(lower=0),
            # Forecasts cached before cloud cover was fetched don't have it.
            "cloud_cover_pct": weather["cloud_cover"] if "cloud_cover" in weather else float("nan"),
            "wind_ms": hub_wind_speed(weather, site.wind),
            "temperature_c": weather["temperature"],
        },
        index=weather.index,
    ).round(1)


def _today(sources: Sources, site: Site, now: datetime) -> list[dict]:
    """Return today's published prices and site weather, shown before the plan so charts can mark the current hour.

    Best effort: the plan never depends on it, so a failed fetch just leaves gaps.
    """
    index = today_index(now)
    start, end = index[0].to_pydatetime(), (index[-1] + pd.Timedelta(hours=1)).to_pydatetime()
    prices = pd.Series(dtype="float64")
    for fetch in (sources.day_ahead, sources.backup_day_ahead):
        if fetch is None:
            continue
        try:
            prices = fetch(start, end)
            break
        except SourceError:
            continue
    try:
        weather = _weather_table(sources.site_weather(site, start, end), site)
    except SourceError:
        weather = pd.DataFrame(index=index)
    frame = pd.DataFrame({"price": prices.reindex(index)}, index=index).join(weather.reindex(index))
    frame["price_source"] = ["actual" if pd.notna(p) else None for p in frame["price"]]
    frame = frame.reset_index(names="ts")
    frame["ts"] = frame["ts"].map(lambda t: t.isoformat())
    return frame.astype(object).where(frame.notna(), None).to_dict(orient="records")


def _hourly_records(plan: PlanResult, weather: pd.DataFrame) -> list[dict]:
    frame = plan.hourly.join(weather).reset_index(names="ts")
    frame["ts"] = frame["ts"].map(lambda t: t.isoformat())
    frame = frame.astype(object).where(frame.notna(), None)
    return frame.to_dict(orient="records")


def run_plan(settings: Settings, store: Store, now: datetime | None = None, sources: Sources | None = None) -> dict:
    """Produce, store and return a full planning run payload."""
    now = now or datetime.now(timezone.utc)
    sources = sources or Sources()
    notes = Notes()
    site = load_site(settings.site_path)
    peak = current_peak(site, _meter_readings(settings, notes), now)
    if peak.meter and not peak.meter["rows_this_year"]:
        notes.warnings.append(f"Uploaded meter data has no readings from {peak.year}; using the peak from the site settings.")
    site = site.model_copy(update={"grid": site.grid.model_copy(update={"peak_so_far_kw": peak.kw})})
    machines = load_machines(settings.machines_path)
    history = load_demand_history(settings.demand_path)
    estimator = estimator_for(settings.price_history_path)
    index = horizon_index(now)

    actual = _fetch_prices(sources, index, notes)
    site_weather = _fetch_weather(lambda a, b: sources.site_weather(site, a, b), "site_weather", store, index, notes, True)
    national = _fetch_weather(lambda a, b: sources.national_weather(a, b), "national_weather", store, index, notes, False)
    prices = price_forecast(index, actual, estimator, national)
    inputs = PlanInputs(
        index=index,
        price=prices["price"],
        price_source=prices["source"],
        solar=solar_kw(site_weather, site.solar),
        wind=wind_kw(site_weather, site.wind),
        demand=base_demand(history, index),
    )

    weather_table = _weather_table(site_weather, site)

    flexible = [m for m in machines if not isinstance(m, AlwaysOn)]
    requirements = build_requirements(flexible, index)
    for req in requirements:
        notes.warnings.extend(req.warnings)
    try:
        plan = optimize(inputs, site, requirements, settings.solver_time_limit)
    except PlannerError as exc:
        if site.grid.peak_charge_eur_per_kw_year <= 0:
            raise RunError(str(exc)) from exc
        # Keeping every hour under a low record can be too hard to solve in time; a plan without it beats no plan.
        unguarded = site.model_copy(update={"grid": site.grid.model_copy(update={"peak_charge_eur_per_kw_year": 0})})
        try:
            plan = optimize(inputs, unguarded, requirements, settings.solver_time_limit)
        except PlannerError as again:
            raise RunError(str(again)) from again
        notes.alert(
            "peak_skipped",
            "warning",
            f"Peak protection could not be solved in time with a record of {site.grid.peak_so_far_kw:,.0f} kW, so this plan ignores the yearly peak. "
            "Enter this year's highest kW from the bill or upload meter data.",
        )
    reference = baseline(inputs, site, requirements)
    if plan.status == "time_limit":
        notes.warnings.append(f"Solver hit its time limit; plan is within {plan.gap:.1%} of optimal.")
    for s in plan.shortfalls:
        name = next(m.name for m in flexible if m.id == s.machine_id)
        notes.alert("shortfall", "error", f"{name} gets {s.scheduled_hours} of {s.required_hours} h ({s.reason}).")
    optimized, base = measure(plan.hourly, site), measure(reference.hourly, site)
    if optimized.unmet_kwh > 0:
        notes.alert("unmet", "error", f"{optimized.unmet_kwh:,.0f} kWh of demand exceeds the grid connection and on-site supply.")
    _plan_change(store, plan, notes)
    _peak_notes(site, optimized, notes)

    savings = round(base.cost_eur - optimized.cost_eur, 2)
    payload = {
        "id": None,
        "created_at": now.isoformat(),
        "horizon_start": index[0].isoformat(),
        "horizon_end": (index[-1] + pd.Timedelta(hours=1)).isoformat(),
        "status": "ok" if not any(a["level"] == "error" for a in notes.alerts) else "attention",
        "site_name": site.name,
        "solver": {"status": plan.status, "gap": plan.gap},
        "summary": {
            "optimized": optimized.to_dict(),
            "baseline": base.to_dict(),
            "savings_eur": savings,
            "savings_pct": round(savings / base.cost_eur, 4) if base.cost_eur > 0 else 0.0,
            "peak_savings_eur": round(base.peak_charge_eur - optimized.peak_charge_eur, 2),
            "peak": peak.to_dict(),
        },
        "daily": _daily(plan, reference, site),
        "machines": _machines(plan, reference, machines, requirements),
        "blocks": [b.to_dict() for b in explain_blocks(plan.hourly, plan.schedule, flexible)],
        "baseline_blocks": [b.to_dict() for b in explain_blocks(reference.hourly, reference.schedule, flexible)],
        "today": _today(sources, site, now),
        "hourly": _hourly_records(plan, weather_table),
        "baseline_hourly": _hourly_records(reference, weather_table),
        "alerts": notes.alerts,
        "warnings": notes.warnings,
        "sources": notes.sources,
        "email": {"status": "pending", "recipients": site.email_recipients},
        "timezone": str(LOCAL_TZ),
    }
    store.save_run(payload)
    return payload
