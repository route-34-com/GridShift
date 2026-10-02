"""User accounts: setup, sign-in, invitations, password resets and changes."""

import re
import sqlite3

from backend.auth import lockout
from backend.auth.passwords import DUMMY_HASH, UNUSABLE, hash_password, password_problem, verify_password
from backend.auth.permissions import ROLES
from backend.database import insert, now_iso, one, rows
from backend.notify.account_emails import Message, invite_email, password_changed_email, reset_email
from backend.services import tokens
from backend.services.audit import FAILURE, record
from backend.services.context import Ctx
from backend.services.errors import AppError
from backend.services.mailer import MailError, send_mail

EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
STATUSES = ("active", "disabled")
PUBLIC = "id, email, name, role, status, created_at, last_login_at"
WRONG_LOGIN = "Wrong email or password."
DISABLED = "This account is switched off. Ask an admin to switch it back on."
INVITED = "Finish setting up your account from the invitation email first."
LAST_ADMIN = "Keep at least one active admin. Make someone else admin first."
FORGOT_ANSWER = "If that email belongs to an active account, a reset link is on its way. It expires in 1 hour."
NO_EMAIL = "Password reset by email isn't set up yet. Ask an admin to send you a reset link."


def clean_email(value: object) -> str:
    """Return a valid email in small letters or refuse it."""
    email = str(value or "").strip().lower()
    if len(email) > 254 or not EMAIL.fullmatch(email):
        raise AppError(400, "Enter a valid email address.")
    return email


def clean_name(value: object) -> str | None:
    """Return a trimmed display name or None."""
    name = str(value or "").strip()[:80]
    return name or None


def check_role(role: object) -> str:
    """Return a known role or refuse it."""
    if role not in ROLES:
        raise AppError(400, "Pick a role: admin, planner or viewer.")
    return str(role)


def by_email(db: sqlite3.Connection, email: str) -> dict | None:
    """Return the user with an email address."""
    return one(db, "SELECT * FROM users WHERE email = ?", (email,))


def get_user(db: sqlite3.Connection, user_id: int) -> dict:
    """Return a user or answer 404."""
    user = one(db, "SELECT * FROM users WHERE id = ?", (user_id,))
    if not user:
        raise AppError(404, "User not found.")
    return user


def public(user: dict) -> dict:
    """Return a user without secrets."""
    return {k: user.get(k) for k in ("id", "email", "name", "role", "status", "created_at", "last_login_at")}


def list_users(db: sqlite3.Connection) -> list[dict]:
    """Return every account, admins first."""
    return rows(db, f"SELECT {PUBLIC} FROM users ORDER BY CASE role WHEN 'admin' THEN 0 WHEN 'planner' THEN 1 ELSE 2 END, email")


def has_users(db: sqlite3.Connection) -> bool:
    """Return whether any account exists."""
    return db.execute("SELECT 1 FROM users LIMIT 1").fetchone() is not None


def _require_password(password: object) -> str:
    problem = password_problem(password)
    if problem:
        raise AppError(400, problem)
    return str(password)


def _set_password(db: sqlite3.Connection, user_id: int, password: str) -> None:
    db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(password), user_id))
    db.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))


def _assert_admin_remains(db: sqlite3.Connection, user_id: int) -> None:
    others = one(db, "SELECT COUNT(*) AS n FROM users WHERE role = 'admin' AND status = 'active' AND id != ?", (user_id,))["n"]
    if not others:
        raise AppError(400, LAST_ADMIN)


def _link(ctx: Ctx, kind: str, token: str) -> str:
    return f"{ctx.app_url}/{'invite' if kind == 'invite' else 'reset'}#t={token}"


def _deliver(ctx: Ctx, user: dict, message: Message, url: str, purpose: str) -> dict:
    try:
        if send_mail(ctx.settings.smtp, user["email"], *message):
            return {"emailed": True}
        return {"emailed": False, "link": url, "warning": "Email isn't set up, so nothing was sent. Copy the link and share it yourself."}
    except MailError as exc:
        record(ctx.db, ctx.actor, "email.failed", ctx.origin, outcome=FAILURE, entity="user", entity_id=user["id"], detail={"purpose": purpose, "to": user["email"], "error": str(exc)})
        return {"emailed": False, "link": url, "warning": f"{exc} Copy the link and share it yourself."}


def create_first_admin(ctx: Ctx, body: dict) -> dict:
    """Create the first admin account when no account exists yet."""
    if has_users(ctx.db):
        raise AppError(403, "An admin account already exists. Sign in instead.")
    email = clean_email(body.get("email"))
    password = _require_password(body.get("password"))
    user_id = insert(ctx.db, "users", {"email": email, "name": clean_name(body.get("name")), "role": "admin", "status": "active", "password_hash": hash_password(password), "created_at": now_iso()})
    user = get_user(ctx.db, user_id)
    record(ctx.db, user, "auth.setup", ctx.origin, entity="user", entity_id=user_id, detail={"email": email})
    return user


def authenticate(ctx: Ctx, email_value: object, password: object) -> dict:
    """Return the user for valid credentials, counting and auditing failures."""
    email = str(email_value or "").strip().lower()
    key = f"{email}|{ctx.origin.ip}"
    minutes = lockout.logins.minutes_left(key)
    if minutes:
        record(ctx.db, None, "auth.login_failed", ctx.origin, outcome=FAILURE, detail={"email": email, "reason": "locked out", "minutes_left": minutes})
        raise AppError(429, lockout.wait_message(minutes, "wrong attempts"))
    user = by_email(ctx.db, email) if email else None
    valid = verify_password(str(password or ""), user["password_hash"] if user else DUMMY_HASH) and user is not None
    if not valid:
        lockout.logins.fail(key)
        record(ctx.db, user, "auth.login_failed", ctx.origin, outcome=FAILURE, entity="user", entity_id=user["id"] if user else None, detail={"email": email, "reason": "wrong password" if user else "unknown email"})
        raise AppError(401, WRONG_LOGIN)
    if user["status"] != "active":
        record(ctx.db, user, "auth.login_failed", ctx.origin, outcome=FAILURE, entity="user", entity_id=user["id"], detail={"email": email, "reason": f"account {user['status']}"})
        raise AppError(401, DISABLED if user["status"] == "disabled" else INVITED)
    lockout.logins.clear(key)
    ctx.db.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (now_iso(), user["id"]))
    record(ctx.db, user, "auth.login", ctx.origin, entity="user", entity_id=user["id"])
    return user


def invite_user(ctx: Ctx, body: dict) -> dict:
    """Add a person by email with a role and email them an invitation."""
    email = clean_email(body.get("email"))
    role = check_role(body.get("role") or "viewer")
    if by_email(ctx.db, email):
        raise AppError(400, f"{email} already has an account.")
    user_id = insert(ctx.db, "users", {"email": email, "name": clean_name(body.get("name")), "role": role, "status": "invited", "password_hash": UNUSABLE, "created_at": now_iso()})
    record(ctx.db, ctx.actor, "user.invite", ctx.origin, entity="user", entity_id=user_id, detail={"email": email, "role": role, "name": clean_name(body.get("name"))})
    return {"id": user_id, **_send_invite(ctx, get_user(ctx.db, user_id))}


def _send_invite(ctx: Ctx, user: dict) -> dict:
    url = _link(ctx, "invite", tokens.issue(ctx.db, user["id"], "invite", ctx.actor["id"]))
    inviter = ctx.actor.get("name") or ctx.actor["email"]
    return _deliver(ctx, user, invite_email(user["name"], inviter, user["role"], url), url, "invite")


def resend_invite(ctx: Ctx, user_id: int) -> dict:
    """Send a fresh invitation to someone who hasn't joined yet."""
    user = get_user(ctx.db, user_id)
    if user["status"] != "invited":
        raise AppError(400, "This person has already set up their account.")
    record(ctx.db, ctx.actor, "user.invite_resent", ctx.origin, entity="user", entity_id=user_id, detail={"email": user["email"]})
    return _send_invite(ctx, user)


def send_reset_link(ctx: Ctx, user_id: int) -> dict:
    """Email a password reset link to an active user on an admin's request."""
    user = get_user(ctx.db, user_id)
    if user["status"] != "active":
        raise AppError(400, "Only active accounts can reset their password.")
    url = _link(ctx, "reset", tokens.issue(ctx.db, user_id, "reset", ctx.actor["id"]))
    record(ctx.db, ctx.actor, "user.reset_link", ctx.origin, entity="user", entity_id=user_id, detail={"email": user["email"]})
    return _deliver(ctx, user, reset_email(url), url, "reset")


def update_user(ctx: Ctx, user_id: int, body: dict) -> dict:
    """Change a user's name, role or status, recording before and after."""
    user = get_user(ctx.db, user_id)
    changes: dict = {}
    if "name" in body and clean_name(body.get("name")) != user["name"]:
        changes["name"] = clean_name(body.get("name"))
    if body.get("role") and body["role"] != user["role"]:
        changes["role"] = check_role(body["role"])
    if body.get("status") and body["status"] != user["status"]:
        if body["status"] not in STATUSES or user["status"] == "invited":
            raise AppError(400, "Status can be active or disabled once the person has joined.")
        changes["status"] = body["status"]
    if not changes:
        return public(user)
    loses_admin = user["role"] == "admin" and user["status"] == "active" and (changes.get("role", "admin") != "admin" or changes.get("status", "active") != "active")
    if loses_admin:
        _assert_admin_remains(ctx.db, user_id)
    ctx.db.execute(f"UPDATE users SET {', '.join(f'{k} = ?' for k in changes)} WHERE id = ?", (*changes.values(), user_id))
    if "role" in changes or "status" in changes:
        ctx.db.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
    record(ctx.db, ctx.actor, "user.update", ctx.origin, entity="user", entity_id=user_id, detail={"email": user["email"], "before": {k: user[k] for k in changes}, "after": changes})
    return public(get_user(ctx.db, user_id))


def delete_user(ctx: Ctx, user_id: int) -> None:
    """Remove a person other than yourself, never the last active admin."""
    if ctx.actor and user_id == ctx.actor["id"]:
        raise AppError(400, "You can't remove yourself. Ask another admin.")
    user = get_user(ctx.db, user_id)
    if user["role"] == "admin" and user["status"] == "active":
        _assert_admin_remains(ctx.db, user_id)
    ctx.db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    record(ctx.db, ctx.actor, "user.delete", ctx.origin, entity="user", entity_id=user_id, detail={"email": user["email"], "role": user["role"], "status": user["status"]})


def invite_details(db: sqlite3.Connection, token: object) -> dict:
    """Return who an invitation is for."""
    found = tokens.peek(db, token, "invite")
    if not found:
        raise AppError(400, tokens.EXPIRED)
    return {"email": found["email"], "name": found["name"], "role": found["role"]}


def _limit(ctx: Ctx, action: str) -> None:
    key = f"{action}|{ctx.origin.ip}"
    minutes = lockout.links.minutes_left(key)
    if minutes:
        raise AppError(429, lockout.wait_message(minutes, "tries"))
    lockout.links.fail(key)


def accept_invite(ctx: Ctx, body: dict) -> dict:
    """Activate an invited account with a password."""
    _limit(ctx, "accept")
    found = tokens.peek(ctx.db, body.get("token"), "invite")
    if not found:
        record(ctx.db, None, "auth.invite_failed", ctx.origin, outcome=FAILURE, detail={"reason": "expired or used link"})
        raise AppError(400, tokens.EXPIRED)
    password = _require_password(body.get("password"))
    user = tokens.consume(ctx.db, body.get("token"), "invite")
    name = clean_name(body.get("name")) or user["name"]
    ctx.db.execute("UPDATE users SET status = 'active', name = ?, last_login_at = ? WHERE id = ?", (name, now_iso(), user["id"]))
    _set_password(ctx.db, user["id"], password)
    joined = get_user(ctx.db, user["id"])
    record(ctx.db, joined, "auth.invite_accepted", ctx.origin, entity="user", entity_id=user["id"], detail={"email": joined["email"], "role": joined["role"]})
    return joined


def forgot_password(ctx: Ctx, email_value: object) -> str:
    """Email a reset link when the address belongs to an active account; the answer never reveals which."""
    _limit(ctx, "forgot")
    if not ctx.settings.smtp.enabled:
        return NO_EMAIL
    email = str(email_value or "").strip().lower()
    user = by_email(ctx.db, email) if EMAIL.fullmatch(email) else None
    record(ctx.db, user, "auth.forgot_requested", ctx.origin, entity="user", entity_id=user["id"] if user else None, outcome="success" if user and user["status"] == "active" else FAILURE, detail={"email": email, "account": user["status"] if user else "none"})
    if user and user["status"] == "active":
        url = _link(ctx, "reset", tokens.issue(ctx.db, user["id"], "reset", None))
        _deliver(ctx, user, reset_email(url), url, "forgot")
    return FORGOT_ANSWER


def reset_password(ctx: Ctx, body: dict) -> dict:
    """Set a new password from a reset link and sign that person out everywhere."""
    _limit(ctx, "reset")
    found = tokens.peek(ctx.db, body.get("token"), "reset")
    if not found:
        record(ctx.db, None, "auth.reset_failed", ctx.origin, outcome=FAILURE, detail={"reason": "expired or used link"})
        raise AppError(400, tokens.EXPIRED)
    password = _require_password(body.get("password"))
    tokens.consume(ctx.db, body.get("token"), "reset")
    _set_password(ctx.db, found["id"], password)
    user = get_user(ctx.db, found["id"])
    record(ctx.db, user, "auth.reset_done", ctx.origin, entity="user", entity_id=user["id"], detail={"email": user["email"]})
    _notify_password_changed(ctx, user)
    return user


def change_own_password(ctx: Ctx, current: object, new: object) -> None:
    """Change the signed-in user's password after checking the current one."""
    user = get_user(ctx.db, ctx.actor["id"])
    if not verify_password(str(current or ""), user["password_hash"]):
        record(ctx.db, user, "account.password_changed", ctx.origin, outcome=FAILURE, entity="user", entity_id=user["id"], detail={"reason": "wrong current password"})
        raise AppError(400, "Your current password is not right.")
    _set_password(ctx.db, user["id"], _require_password(new))
    record(ctx.db, user, "account.password_changed", ctx.origin, entity="user", entity_id=user["id"])
    _notify_password_changed(ctx, user)


def update_profile(ctx: Ctx, body: dict) -> dict:
    """Change the signed-in user's display name."""
    user = get_user(ctx.db, ctx.actor["id"])
    name = clean_name(body.get("name"))
    if name != user["name"]:
        ctx.db.execute("UPDATE users SET name = ? WHERE id = ?", (name, user["id"]))
        record(ctx.db, user, "account.profile_updated", ctx.origin, entity="user", entity_id=user["id"], detail={"before": {"name": user["name"]}, "after": {"name": name}})
    return public(get_user(ctx.db, user["id"]))


def _notify_password_changed(ctx: Ctx, user: dict) -> None:
    try:
        send_mail(ctx.settings.smtp, user["email"], *password_changed_email(user["name"]))
    except MailError as exc:
        record(ctx.db, user, "email.failed", ctx.origin, outcome=FAILURE, entity="user", entity_id=user["id"], detail={"purpose": "password changed notice", "error": str(exc)})
