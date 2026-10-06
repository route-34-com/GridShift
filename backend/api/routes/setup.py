"""Set up the company's own site: site settings, machines and load history, edited from the dashboard."""

import os
import shutil
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from pydantic import BaseModel

from backend.api.deps import AppDep, AuthCtx, require
from backend.datasets import LIVE, ready
from backend.services.audit import FAILURE, record
from backend.services.errors import AppError
from backend.settings import Settings
from backend.sources.demand_history import load_demand_history, parse_demand_history
from backend.sources.meter import current_peak, load_meter
from backend.sources.site import ConfigError, load_machines, load_site, save_machines, save_site, validate_machines, validate_site

router = APIRouter(prefix="/api/setup", tags=["setup"])

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
SAMPLE_FILES = ("site.yaml", "machines.yaml", "demand_history.csv")


class MachineList(BaseModel):
    machines: list[dict]


def _check(load) -> dict:
    try:
        return {"ok": True, **(load() or {})}
    except ConfigError as exc:
        missing = "not found" in str(exc)
        return {"ok": False, "missing": missing, "error": None if missing else str(exc)}


def setup_status(settings: Settings, dataset: str) -> dict:
    """Return what the planner needs for this data set and what is in place."""

    def demand():
        series = load_demand_history(settings.demand_path)
        return {"rows": len(series), "start": series.index[0].isoformat(), "end": series.index[-1].isoformat()}

    def meter():
        readings = load_meter(settings.meter_path)
        if readings is None:
            raise ConfigError("Meter data not found")
        return {"rows": len(readings)}

    def saved(load):
        try:
            return load()
        except ConfigError:
            return None

    site = saved(lambda: load_site(settings.site_path).model_dump(mode="json"))
    machines = saved(lambda: [m.model_dump(mode="json", exclude_none=True) for m in load_machines(settings.machines_path)])
    prices = settings.price_history_path
    meter_ok = settings.meter_path.exists()
    # A peak charge with no known record makes every kW a new peak: worth a warning before planning.
    peak_unknown = bool(site and site["grid"]["peak_charge_eur_per_kw_year"] > 0 and site["grid"]["peak_so_far_kw"] <= 0 and not meter_ok)
    return {
        "dataset": dataset,
        "editable": dataset == LIVE,
        "ready": ready(settings),
        "site": _check(lambda: {"name": load_site(settings.site_path).name}),
        "machines": _check(lambda: {"count": len(load_machines(settings.machines_path))}),
        "demand": _check(demand),
        "prices": {"ok": prices.exists(), "shared": prices.parent != settings.data_dir},
        "meter": _check(meter),
        "peak_unknown": peak_unknown,
        # Current values to edit; null or empty while a file is missing or invalid.
        "site_data": site,
        "machine_data": machines or [],
    }


def _editable(app: AppDep) -> Settings:
    data = app.data
    if data.name != LIVE:
        raise AppError(409, "Turn sample data off to set up your own site. The Holcim sample can't be edited here.")
    return data.settings


def _reject(ctx, what: str, exc: Exception) -> AppError:
    message = str(exc)
    record(ctx.db, ctx.actor, "config.rejected", ctx.origin, outcome=FAILURE, entity="config", entity_id=what, detail={"error": message})
    return AppError(422, message)


@router.get("", dependencies=[require("config.view")])
def get_setup(app: AppDep) -> dict:
    """Return the setup checklist for the data set in use."""
    data = app.data
    return setup_status(data.settings, data.name)


@router.put("/site", dependencies=[require("config.edit")])
def put_site(body: dict, app: AppDep, ctx: AuthCtx) -> dict:
    """Validate and save the site settings."""
    settings = _editable(app)
    try:
        site = validate_site(body)
    except ConfigError as exc:
        raise _reject(ctx, "site", exc) from exc
    save_site(settings.site_path, site)
    record(ctx.db, ctx.actor, "config.site", ctx.origin, entity="config", entity_id="site", detail={"name": site.name})
    return setup_status(settings, LIVE)


@router.put("/machines", dependencies=[require("config.edit")])
def put_machines(body: MachineList, app: AppDep, ctx: AuthCtx) -> dict:
    """Validate and save the whole machine list."""
    settings = _editable(app)
    try:
        machines = validate_machines(body.machines)
    except ConfigError as exc:
        raise _reject(ctx, "machines", exc) from exc
    try:
        before = {m.id: m for m in load_machines(settings.machines_path)}
    except ConfigError:
        before = {}
    after = {m.id: m for m in machines}
    save_machines(settings.machines_path, machines)
    detail = {
        "added": sorted(after.keys() - before.keys()),
        "removed": sorted(before.keys() - after.keys()),
        "changed": sorted(i for i in after.keys() & before.keys() if after[i] != before[i]),
    }
    record(ctx.db, ctx.actor, "config.machines", ctx.origin, entity="config", entity_id="machines", detail=detail)
    return setup_status(settings, LIVE)


@router.post("/demand", dependencies=[require("config.edit")])
async def post_demand(request: Request, app: AppDep, ctx: AuthCtx) -> dict:
    """Replace the load history with an uploaded CSV."""
    settings = _editable(app)
    body = await request.body()
    try:
        if len(body) > MAX_UPLOAD_BYTES:
            raise ConfigError("Load history file is larger than 20 MB.")
        try:
            text = body.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ConfigError("Load history must be a UTF-8 text CSV.") from exc
        series = parse_demand_history(text)
    except ConfigError as exc:
        raise _reject(ctx, "demand", exc) from exc
    path = settings.demand_path
    path.parent.mkdir(parents=True, exist_ok=True)
    # Store in the planner's own format so later reads never depend on the upload's separator.
    frame = series.rename_axis("timestamp").reset_index()
    frame["timestamp"] = frame["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    temp = path.with_suffix(".tmp")
    frame.round(1).to_csv(temp, index=False)
    os.replace(temp, path)
    record(ctx.db, ctx.actor, "config.demand", ctx.origin, entity="config", entity_id="demand", detail={"rows": len(series)})
    return setup_status(settings, LIVE)


def _carry_sample_peak(settings: Settings) -> None:
    """Give the copied site the sample's peak record, since the sample's meter data stays behind."""
    readings = load_meter(settings.sample_dir / "meter_data.csv")
    site = load_site(settings.site_path)
    if readings is None or site.grid.peak_so_far_kw > 0:
        return
    record_kw = current_peak(site, readings, datetime.now(timezone.utc)).kw
    save_site(settings.site_path, site.model_copy(update={"grid": site.grid.model_copy(update={"peak_so_far_kw": round(record_kw)})}))


@router.post("/copy-sample", dependencies=[require("config.edit")])
def copy_sample(app: AppDep, ctx: AuthCtx) -> dict:
    """Copy the sample's site, machines and load history into the company's folder, never overwriting a file."""
    settings = _editable(app)
    if settings.sample_dir is None:
        raise AppError(409, "No sample data is installed on this server.")
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    copied = []
    for name in SAMPLE_FILES:
        target = settings.data_dir / name
        if not target.exists() and (settings.sample_dir / name).exists():
            shutil.copyfile(settings.sample_dir / name, target)
            copied.append(name)
    if "site.yaml" in copied:
        _carry_sample_peak(settings)
    record(ctx.db, ctx.actor, "config.copy_sample", ctx.origin, entity="config", entity_id="sample", detail={"copied": copied})
    return setup_status(settings, LIVE)
