"""User management for admins."""

from fastapi import APIRouter

from backend.api.deps import AuthCtx, require
from backend.notify.account_emails import test_email
from backend.services import users
from backend.services.audit import FAILURE, record
from backend.services.errors import AppError
from backend.services.mailer import MailError, mail_status, send_mail

router = APIRouter(prefix="/api/users", tags=["users"], dependencies=[require("users.manage")])


@router.get("")
def list_users(ctx: AuthCtx) -> list[dict]:
    """Return every account, marking the signed-in one."""
    return [{**u, "you": u["id"] == ctx.actor["id"]} for u in users.list_users(ctx.db)]


@router.get("/mail-status")
def get_mail_status(ctx: AuthCtx) -> dict:
    """Return whether email sending is configured, without secrets."""
    return mail_status(ctx.settings.smtp)


@router.post("/test-email")
def send_test_email(ctx: AuthCtx) -> dict:
    """Send a test email to the signed-in admin."""
    if not ctx.settings.smtp.enabled:
        raise AppError(400, "Email isn't set up. Add the SMTP settings to .env and restart GridShift.")
    try:
        send_mail(ctx.settings.smtp, ctx.actor["email"], *test_email(ctx.settings.smtp.sender))
    except MailError as exc:
        record(ctx.db, ctx.actor, "email.test", ctx.origin, outcome=FAILURE, detail={"to": ctx.actor["email"], "error": str(exc)})
        raise AppError(502, str(exc)) from exc
    record(ctx.db, ctx.actor, "email.test", ctx.origin, detail={"to": ctx.actor["email"]})
    return {"ok": True, "to": ctx.actor["email"]}


@router.post("/invite", status_code=201)
def invite(body: dict, ctx: AuthCtx) -> dict:
    """Invite a person by email with a role."""
    return users.invite_user(ctx, body)


@router.post("/{user_id}/resend-invite")
def resend_invite(user_id: int, ctx: AuthCtx) -> dict:
    """Send the invitation again with a fresh link."""
    return users.resend_invite(ctx, user_id)


@router.post("/{user_id}/reset-link")
def reset_link(user_id: int, ctx: AuthCtx) -> dict:
    """Email a password reset link."""
    return users.send_reset_link(ctx, user_id)


@router.put("/{user_id}")
def update(user_id: int, body: dict, ctx: AuthCtx) -> dict:
    """Change a person's name, role or status."""
    return users.update_user(ctx, user_id, body)


@router.delete("/{user_id}")
def delete(user_id: int, ctx: AuthCtx) -> dict:
    """Remove a person."""
    users.delete_user(ctx, user_id)
    return {"ok": True}
