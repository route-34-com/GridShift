"""Single-use invitation and password reset tokens."""

import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

from backend.auth.passwords import token_hash
from backend.database import insert, iso, now_iso, one
from backend.services.errors import AppError

LIFETIME = {"invite": timedelta(days=7), "reset": timedelta(hours=1)}
EXPIRED = "This link has expired or was already used. Ask for a new one."


def issue(db: sqlite3.Connection, user_id: int, kind: str, created_by: int | None) -> str:
    """Make a single-use token, voiding older unused ones of the same kind."""
    db.execute("DELETE FROM auth_tokens WHERE user_id = ? AND kind = ? AND used_at IS NULL", (user_id, kind))
    token = secrets.token_urlsafe(32)
    insert(
        db,
        "auth_tokens",
        {
            "user_id": user_id,
            "kind": kind,
            "token_hash": token_hash(token),
            "expires_at": iso(datetime.now(timezone.utc) + LIFETIME[kind]),
            "created_by": created_by,
            "created_at": now_iso(),
        },
    )
    return token


def peek(db: sqlite3.Connection, token: object, kind: str) -> dict | None:
    """Return the token's user while the token is unused and not expired."""
    if not token or not isinstance(token, str) or len(token) > 200:
        return None
    return one(
        db,
        "SELECT t.id AS token_id, u.* FROM auth_tokens t JOIN users u ON u.id = t.user_id "
        "WHERE t.token_hash = ? AND t.kind = ? AND t.used_at IS NULL AND t.expires_at > ?",
        (token_hash(token), kind, now_iso()),
    )


def consume(db: sqlite3.Connection, token: object, kind: str) -> dict:
    """Use a token once and return its user, or refuse an expired or used one."""
    found = peek(db, token, kind)
    if not found:
        raise AppError(400, EXPIRED)
    db.execute("UPDATE auth_tokens SET used_at = ? WHERE id = ?", (now_iso(), found["token_id"]))
    return found
