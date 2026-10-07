"""Daily planning run started by the host's scheduler (Vercel Cron)."""

import hmac

from fastapi import APIRouter, Request

from backend.api.deps import AppDep
from backend.jobs import execute
from backend.services.errors import AppError

router = APIRouter(prefix="/api/cron", tags=["cron"])


@router.get("/daily")
def daily(request: Request, app: AppDep) -> dict:
    """Run, store and email the daily plan when called with the scheduler's secret."""
    secret = app.settings.cron_secret
    if not secret or not hmac.compare_digest(request.headers.get("authorization", ""), f"Bearer {secret}"):
        raise AppError(401, "Only the scheduler can start the daily run.")
    if not app.lock.acquire(blocking=False):
        raise AppError(409, "A planning run is already in progress.")
    try:
        data = app.data
        result = execute(data.settings, data.store, sources=app.sources)
    finally:
        app.lock.release()
    return {"status": result["status"], "id": result.get("id"), "error": result.get("error")}
