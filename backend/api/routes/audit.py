"""Audit trail for admins."""

from fastapi import APIRouter, Request

from backend.api.deps import AuthCtx, require
from backend.services.audit import action_catalog, list_audit

router = APIRouter(prefix="/api/audit", tags=["audit"], dependencies=[require("audit.view")])
QUERY_KEYS = ("user_id", "action", "category", "outcome", "entity", "from", "to", "q")


def audit_query(request: Request) -> dict:
    """Return the audit filters present in the query string."""
    return {k: request.query_params[k] for k in QUERY_KEYS if request.query_params.get(k)}


@router.get("")
def entries(request: Request, ctx: AuthCtx, limit: int = 50, offset: int = 0) -> dict:
    """Return a filtered page of audit entries, newest first."""
    return list_audit(ctx.db, audit_query(request), limit, offset)


@router.get("/actions")
def actions(ctx: AuthCtx) -> list[dict]:
    """Return every action the audit trail records."""
    return action_catalog()
