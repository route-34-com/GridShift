"""Which data set the dashboard shows: the built-in sample or the company's own."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from backend.api.deps import AppDep, AuthCtx, require
from backend.datasets import LIVE, SAMPLE, active_name, choose, describe
from backend.services.audit import record
from backend.services.errors import AppError

router = APIRouter(prefix="/api/dataset", tags=["dataset"])


class Choice(BaseModel):
    active: Literal["sample", "live"]


@router.get("", dependencies=[require("plan.view")])
def get_dataset(app: AppDep) -> dict:
    """Return the data set in use and whether each one has site data."""
    return describe(app.settings, app.store)


@router.put("", dependencies=[require("data.switch")])
def set_dataset(body: Choice, app: AppDep, ctx: AuthCtx) -> dict:
    """Switch the dashboard and the daily run to sample or real data."""
    if body.active == SAMPLE and app.settings.sample_dir is None:
        raise AppError(409, "No sample data is installed on this server.")
    before = active_name(app.settings, app.store)
    if not app.lock.acquire(blocking=False):
        raise AppError(409, "A planning run is in progress. Switch once it has finished.")
    try:
        choose(ctx.db, body.active)
    finally:
        app.lock.release()
    if before != body.active:
        label = {SAMPLE: "sample data", LIVE: "real data"}
        record(ctx.db, ctx.actor, "data.switch", ctx.origin, summary=f"Switched to {label[body.active]}", detail={"from": before, "to": body.active})
    return describe(app.settings, app.store, body.active)
