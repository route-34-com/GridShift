"""Health, status and configuration endpoints."""

from fastapi import APIRouter

from backend.api.deps import AppDep, require
from backend.services.errors import AppError
from backend.sources.site import ConfigError, load_machines, load_site

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health")
def health() -> dict:
    """Return liveness."""
    return {"status": "ok"}


@router.get("/status", dependencies=[require("plan.view")])
def status(app: AppDep) -> dict:
    """Return whether a run is in progress and the latest run outcome."""
    runs = app.store.list_runs(1)
    latest = runs[0] if runs else None
    failure = app.store.get_run(latest["id"]) if latest and latest["status"] == "failed" else None
    return {"running": app.lock.locked(), "latest": latest, "last_failure": failure}


@router.get("/config", dependencies=[require("config.view")])
def config(app: AppDep) -> dict:
    """Return the site and machine configuration."""
    try:
        site = load_site(app.settings.site_path)
        machines = load_machines(app.settings.machines_path)
    except ConfigError as exc:
        raise AppError(422, str(exc)) from exc
    return {"site": site.model_dump(mode="json"), "machines": [m.model_dump(mode="json") for m in machines]}
