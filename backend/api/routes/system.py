"""Health, status and configuration endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from backend.api.deps import AppState, state
from backend.sources.site import ConfigError, load_machines, load_site

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health")
def health() -> dict:
    """Return liveness."""
    return {"status": "ok"}


@router.get("/status")
def status(app: AppState = Depends(state)) -> dict:
    """Return whether a run is in progress and the latest run outcome."""
    runs = app.store.list_runs(1)
    latest = runs[0] if runs else None
    failure = None
    if latest and latest["status"] == "failed":
        failure = app.store.get_run(latest["id"])
    return {"running": app.lock.locked(), "latest": latest, "last_failure": failure}


@router.get("/config")
def config(app: AppState = Depends(state)) -> dict:
    """Return the site and machine configuration."""
    try:
        site = load_site(app.settings.site_path)
        machines = load_machines(app.settings.machines_path)
    except ConfigError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"site": site.model_dump(mode="json"), "machines": [m.model_dump(mode="json") for m in machines]}
