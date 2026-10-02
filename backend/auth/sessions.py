"""Cookie sessions and request details."""

import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

from fastapi import Request, Response

from backend.auth.passwords import token_hash
from backend.database import iso, now_iso
from backend.settings import Settings

SESSION_DAYS = 14
COOKIE = "gridshift_sid"


def client_ip(request: Request, settings: Settings) -> str:
    """Return the caller's address, trusting one proxy hop when configured."""
    forwarded = request.headers.get("x-forwarded-for")
    if settings.trust_proxy and forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else ""


def user_agent(request: Request) -> str:
    """Return the caller's browser description, trimmed."""
    return (request.headers.get("user-agent") or "")[:300]


def _is_https(request: Request, settings: Settings) -> bool:
    if settings.trust_proxy:
        proto = request.headers.get("x-forwarded-proto", "").split(",")[0].strip()
        if proto:
            return proto == "https"
    return request.url.scheme == "https"


def _set_cookie(request: Request, response: Response, settings: Settings, value: str, max_age: int) -> None:
    response.set_cookie(COOKIE, value, max_age=max_age, path="/", httponly=True, samesite="lax", secure=_is_https(request, settings))


def create_session(db: sqlite3.Connection, request: Request, response: Response, settings: Settings, user_id: int) -> None:
    """Start a session for a user and set its cookie."""
    token = secrets.token_hex(32)
    expires = iso(datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS))
    db.execute("DELETE FROM sessions WHERE expires_at < ?", (now_iso(),))
    db.execute("INSERT INTO sessions (token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)", (token_hash(token), user_id, now_iso(), expires))
    _set_cookie(request, response, settings, token, SESSION_DAYS * 86400)


def session_user(db: sqlite3.Connection, request: Request) -> dict | None:
    """Return the active user for the request's session cookie, or None."""
    token = request.cookies.get(COOKIE)
    if not token:
        return None
    row = db.execute(
        "SELECT u.id, u.email, u.name, u.role, u.status, u.created_at, u.last_login_at FROM sessions s JOIN users u ON u.id = s.user_id "
        "WHERE s.token_hash = ? AND s.expires_at > ? AND u.status = 'active'",
        (token_hash(token), now_iso()),
    ).fetchone()
    return dict(row) if row else None


def end_session(db: sqlite3.Connection, request: Request, response: Response, settings: Settings) -> None:
    """Delete the request's session and clear its cookie."""
    token = request.cookies.get(COOKIE)
    if token:
        db.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash(token),))
    _set_cookie(request, response, settings, "", 0)
