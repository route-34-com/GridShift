"""Audit trail: record who did what, when, from where, and list it back with filters."""

import json
import sqlite3
from dataclasses import dataclass

from backend.database import insert, now_iso, one, rows

ACTIONS = {
    "auth.setup": "Created the first admin account",
    "auth.login": "Signed in",
    "auth.login_failed": "Failed sign-in",
    "auth.logout": "Signed out",
    "auth.forgot_requested": "Requested a password reset",
    "auth.reset_done": "Reset their password",
    "auth.reset_failed": "Used an invalid reset link",
    "auth.invite_accepted": "Accepted an invitation",
    "auth.invite_failed": "Used an invalid invitation link",
    "user.invite": "Invited a user",
    "user.invite_resent": "Resent an invitation",
    "user.reset_link": "Sent a password reset link",
    "user.update": "Changed a user",
    "user.delete": "Removed a user",
    "account.password_changed": "Changed their own password",
    "account.profile_updated": "Updated their profile",
    "plan.run": "Ran the planner",
    "plan.run_failed": "Planner run failed",
    "export.download": "Downloaded an export",
    "email.test": "Sent a test email",
    "email.plan_sent": "Daily plan email delivered",
    "email.failed": "Email could not be sent",
}

SUCCESS, FAILURE = "success", "failure"


@dataclass(frozen=True)
class Origin:
    """Where a request came from."""

    ip: str = ""
    user_agent: str = ""


SYSTEM = Origin("", "GridShift scheduler")


def record(
    db: sqlite3.Connection,
    actor: dict | None,
    action: str,
    origin: Origin = SYSTEM,
    *,
    outcome: str = SUCCESS,
    entity: str | None = None,
    entity_id: object = None,
    summary: str | None = None,
    detail: dict | None = None,
) -> int:
    """Write one audit entry and return its id."""
    return insert(
        db,
        "audit_log",
        {
            "at": now_iso(),
            "user_id": actor.get("id") if actor else None,
            "user_email": actor.get("email") if actor else None,
            "action": action,
            "outcome": outcome,
            "entity": entity,
            "entity_id": None if entity_id is None else str(entity_id),
            "summary": summary or ACTIONS.get(action, action),
            "detail": json.dumps(detail, ensure_ascii=False, default=str) if detail else None,
            "ip": origin.ip,
            "user_agent": origin.user_agent,
        },
    )


FILTERS = (
    ("user_id", "a.user_id = ?"),
    ("action", "a.action = ?"),
    ("outcome", "a.outcome = ?"),
    ("entity", "a.entity = ?"),
    ("from", "a.at >= ?"),
    ("to", "a.at < date(?, '+1 day')"),
)


def _where(query: dict) -> tuple[str, list]:
    clauses, params = [], []
    for key, condition in FILTERS:
        if query.get(key) not in (None, ""):
            clauses.append(condition)
            params.append(query[key])
    if query.get("category"):
        clauses.append("a.action LIKE ?")
        params.append(f"{query['category']}.%")
    if query.get("q"):
        clauses.append("(a.summary LIKE ? OR a.detail LIKE ? OR a.user_email LIKE ? OR a.ip LIKE ?)")
        params.extend([f"%{query['q']}%"] * 4)
    return (f"WHERE {' AND '.join(clauses)}" if clauses else ""), params


def actor_label(entry: dict) -> str:
    """Return who made an entry: the user's email, the scheduler, or an unknown visitor."""
    if entry.get("user_email"):
        return entry["user_email"]
    return "system" if entry.get("user_agent") == SYSTEM.user_agent else "unknown visitor"


def _decode(entry: dict) -> dict:
    return {**entry, "detail": json.loads(entry["detail"]) if entry.get("detail") else None}


def list_audit(db: sqlite3.Connection, query: dict, limit: int = 100, offset: int = 0) -> dict:
    """Return a page of audit entries, newest first, with the total matching count."""
    where, params = _where(query)
    total = one(db, f"SELECT COUNT(*) AS n FROM audit_log a {where}", tuple(params))["n"]
    found = rows(
        db,
        f"SELECT a.*, u.name AS user_name FROM audit_log a LEFT JOIN users u ON u.id = a.user_id {where} ORDER BY a.id DESC LIMIT ? OFFSET ?",
        [*params, max(1, min(limit, 1000)), max(0, offset)],
    )
    return {"total": total, "entries": [_decode(e) for e in found]}


def export_audit(db: sqlite3.Connection, query: dict, limit: int = 50000) -> list[dict]:
    """Return matching audit entries flattened for a spreadsheet."""
    found = list_audit(db, query, limit)["entries"]
    return [
        {
            "time_utc": e["at"],
            "user": actor_label(e),
            "name": e["user_name"] or "",
            "action": e["action"],
            "summary": e["summary"],
            "outcome": e["outcome"],
            "entity": e["entity"] or "",
            "entity_id": e["entity_id"] or "",
            "detail": json.dumps(e["detail"], ensure_ascii=False) if e["detail"] else "",
            "ip": e["ip"] or "",
            "browser": e["user_agent"] or "",
        }
        for e in found
    ]


def action_catalog() -> list[dict]:
    """Return every known action with its description."""
    return [{"action": k, "summary": v} for k, v in ACTIONS.items()]
