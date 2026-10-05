"""Interval meter upload and this year's peak record."""

import os
from datetime import datetime, timezone

from fastapi import APIRouter, Request

from backend.api.deps import AppDep, AppState, AuthCtx, require
from backend.services.audit import FAILURE, record
from backend.services.errors import AppError
from backend.sources.meter import current_peak, load_meter, parse_meter_csv
from backend.sources.site import ConfigError, load_site

router = APIRouter(prefix="/api", tags=["meter"])

MAX_UPLOAD_BYTES = 20 * 1024 * 1024


def _peak(app: AppState) -> dict:
    try:
        site = load_site(app.settings.site_path)
        readings = load_meter(app.settings.meter_path)
    except ConfigError as exc:
        raise AppError(422, str(exc)) from exc
    return current_peak(site, readings, datetime.now(timezone.utc)).to_dict()


@router.get("/peak", dependencies=[require("plan.view")])
def peak(app: AppDep) -> dict:
    """Return this year's peak record and its monthly and annual cost."""
    return _peak(app)


@router.post("/meter", dependencies=[require("meter.upload")])
async def upload_meter(request: Request, app: AppDep, ctx: AuthCtx) -> dict:
    """Replace the stored meter data with an uploaded CSV and return the new peak record."""
    body = await request.body()
    try:
        if len(body) > MAX_UPLOAD_BYTES:
            raise AppError(413, "Meter file is larger than 20 MB.")
        try:
            text = body.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise AppError(422, "Meter file must be a UTF-8 text CSV.") from exc
        try:
            readings = parse_meter_csv(text)
        except ConfigError as exc:
            raise AppError(422, str(exc)) from exc
    except AppError as exc:
        record(ctx.db, ctx.actor, "meter.upload_failed", ctx.origin, outcome=FAILURE, entity="meter", detail={"bytes": len(body), "error": exc.message})
        raise
    path = app.settings.meter_path
    temp = path.with_suffix(".upload")
    temp.write_text(text, encoding="utf-8")
    os.replace(temp, path)
    result = _peak(app)
    record(ctx.db, ctx.actor, "meter.upload", ctx.origin, entity="meter", detail={"rows": len(readings), "record_kw": result["record_kw"]})
    return result
