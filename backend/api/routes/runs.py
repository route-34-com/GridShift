"""Planning run endpoints."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from backend.api.deps import AppDep, AuthCtx, latest_or_404, require
from backend.jobs import execute
from backend.notify.email import render_plan_email
from backend.services.errors import AppError

router = APIRouter(prefix="/api/runs", tags=["runs"], dependencies=[require("plan.view")])

DETAIL_KEYS = ("hourly", "baseline_hourly", "blocks", "baseline_blocks", "today")


def _summary(run: dict) -> dict:
    return {k: v for k, v in run.items() if k not in DETAIL_KEYS}


@router.get("")
def list_runs(app: AppDep, limit: int = 20) -> list[dict]:
    """Return recent runs, newest first."""
    return app.data.store.list_runs(max(1, min(limit, 100)))


@router.post("", status_code=201, dependencies=[require("plan.run")])
def create_run(app: AppDep, ctx: AuthCtx, email: bool = False) -> dict:
    """Run the planner now."""
    if not app.lock.acquire(blocking=False):
        raise AppError(409, "A planning run is already in progress.")
    try:
        data = app.data
        result = execute(data.settings, data.store, sources=app.sources, email=email, actor=ctx.actor, origin=ctx.origin)
    finally:
        app.lock.release()
    if result["status"] == "failed":
        raise AppError(502, f"Planning run failed: {result['error']}")
    return _summary(result)


@router.get("/latest")
def latest(app: AppDep) -> dict:
    """Return the newest successful run summary."""
    return _summary(latest_or_404(app))


@router.get("/latest/hourly")
def latest_hourly(app: AppDep) -> dict:
    """Return hourly flows for the plan and the baseline."""
    run = latest_or_404(app)
    return {"plan": run["hourly"], "baseline": run["baseline_hourly"], "today": run.get("today", [])}


@router.get("/latest/blocks")
def latest_blocks(app: AppDep) -> dict:
    """Return machine run blocks for the plan and the baseline."""
    run = latest_or_404(app)
    return {"plan": run["blocks"], "baseline": run["baseline_blocks"]}


@router.get("/latest/email", response_class=HTMLResponse)
def latest_email(app: AppDep) -> str:
    """Return the daily plan email as HTML."""
    return render_plan_email(latest_or_404(app))[1]


@router.get("/{run_id}")
def get_run(run_id: int, app: AppDep) -> dict:
    """Return one run summary by id."""
    run = app.data.store.get_run(run_id)
    if run is None:
        raise AppError(404, f"Run {run_id} not found.")
    return _summary(run)
