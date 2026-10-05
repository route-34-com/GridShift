"""CSV and Excel downloads."""

from fastapi import APIRouter, Request
from fastapi.responses import Response

from backend.api.deps import AppDep, AuthCtx, latest_or_404, require
from backend.api.routes.audit import audit_query
from backend.auth.permissions import can
from backend.services import exporter, users
from backend.services.audit import export_audit, record
from backend.services.errors import AppError

router = APIRouter(prefix="/api/exports", tags=["exports"], dependencies=[require("export")])


def _download(ctx, data: bytes, stem: str, fmt: str, detail: dict) -> Response:
    name = exporter.filename(stem, fmt)
    record(ctx.db, ctx.actor, "export.download", ctx.origin, entity="export", entity_id=stem, detail={**detail, "format": fmt, "file": name, "bytes": len(data)})
    return Response(data, media_type=exporter.MIME[fmt], headers={"Content-Disposition": f'attachment; filename="{name}"', "Cache-Control": "no-store"})


@router.get("/run/{name}")
def run_export(name: str, app: AppDep, ctx: AuthCtx, format: str = "xlsx", run_id: int | None = None) -> Response:
    """Download part of a plan, or the full report, as CSV, Excel or PDF."""
    run = app.data.store.get_run(run_id) if run_id else latest_or_404(app)
    if not run or run.get("status") == "failed":
        raise AppError(404, f"Plan {run_id} not found.")
    data, rows = exporter.run_file(run, name, format)
    return _download(ctx, data, f"plan{run['id']}-{name}", format, {"export": name, "run_id": run["id"], "rows": rows})


@router.get("/users")
def users_export(ctx: AuthCtx, format: str = "xlsx") -> Response:
    """Download the user list (admins only)."""
    if not can(ctx.actor, "users.manage"):
        raise AppError(403, "Your role doesn't allow this. Ask an admin.")
    table = [{k: (v or "") for k, v in u.items()} for u in users.list_users(ctx.db)]
    return _download(ctx, exporter.render([("Users", table)], format, "GridShift users"), "users", format, {"export": "users", "rows": len(table)})


@router.get("/audit")
def audit_export(request: Request, ctx: AuthCtx, format: str = "xlsx") -> Response:
    """Download the filtered audit trail (admins only)."""
    if not can(ctx.actor, "audit.view"):
        raise AppError(403, "Your role doesn't allow this. Ask an admin.")
    query = audit_query(request)
    table = export_audit(ctx.db, query)
    subtitle = "Filters: " + ", ".join(f"{k}={v}" for k, v in query.items()) if query else "All entries"
    return _download(ctx, exporter.render([("Audit trail", table)], format, "GridShift audit trail", subtitle), "audit", format, {"export": "audit", "filters": query, "rows": len(table)})
