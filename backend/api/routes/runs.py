"""Planning run endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse

from backend.api.deps import AppState, latest_or_404, state
from backend.jobs import execute
from backend.notify.email import render_plan_email

router = APIRouter(prefix="/api/runs", tags=["runs"])

DETAIL_KEYS = ("hourly", "baseline_hourly", "blocks", "baseline_blocks")


def _summary(run: dict) -> dict:
    return {k: v for k, v in run.items() if k not in DETAIL_KEYS}


@router.get("")
def list_runs(limit: int = 20, app: AppState = Depends(state)) -> list[dict]:
    """Return recent runs, newest first."""
    return app.store.list_runs(max(1, min(limit, 100)))


@router.post("", status_code=201)
def create_run(email: bool = False, app: AppState = Depends(state)) -> dict:
    """Run the planner now."""
    if not app.lock.acquire(blocking=False):
        raise HTTPException(409, "A planning run is already in progress.")
    try:
        result = execute(app.settings, app.store, sources=app.sources, email=email)
    finally:
        app.lock.release()
    if result["status"] == "failed":
        raise HTTPException(502, f"Planning run failed: {result['error']}")
    return _summary(result)


@router.get("/latest")
def latest(app: AppState = Depends(state)) -> dict:
    """Return the newest successful run summary."""
    return _summary(latest_or_404(app))


@router.get("/latest/hourly")
def latest_hourly(app: AppState = Depends(state)) -> dict:
    """Return hourly flows for the plan and the baseline."""
    run = latest_or_404(app)
    return {"plan": run["hourly"], "baseline": run["baseline_hourly"]}


@router.get("/latest/blocks")
def latest_blocks(app: AppState = Depends(state)) -> dict:
    """Return machine run blocks for the plan and the baseline."""
    run = latest_or_404(app)
    return {"plan": run["blocks"], "baseline": run["baseline_blocks"]}


@router.get("/latest/email", response_class=HTMLResponse)
def latest_email(app: AppState = Depends(state)) -> str:
    """Return the daily plan email as HTML."""
    return render_plan_email(latest_or_404(app))[1]


@router.get("/{run_id}")
def get_run(run_id: int, app: AppState = Depends(state)) -> dict:
    """Return one run summary by id."""
    run = app.store.get_run(run_id)
    if run is None:
        raise HTTPException(404, f"Run {run_id} not found.")
    return _summary(run)
