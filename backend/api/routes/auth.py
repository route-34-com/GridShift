"""Sign-in, first setup, invitations, password reset and the user's own account."""

from fastapi import APIRouter, Request, Response

from backend.api.deps import AnonCtx, AuthCtx, Db, User, state
from backend.auth.permissions import permissions_for
from backend.auth.sessions import create_session, end_session
from backend.services import users
from backend.services.audit import record
from backend.services.errors import AppError
from backend.services.mailer import mail_status

router = APIRouter(prefix="/api/auth", tags=["auth"])
LOOPBACK = {"127.0.0.1", "::1", "::ffff:127.0.0.1", "testclient"}


def _setup_allowed(request: Request, db) -> bool:
    if users.has_users(db):
        return False
    local = (request.client.host if request.client else "") in LOOPBACK and "x-forwarded-for" not in request.headers
    return local or state(request).settings.allow_remote_setup


def _me(user: dict) -> dict:
    return {**users.public(user), "permissions": permissions_for(user["role"]), "local": bool(user.get("local"))}


def _account(ctx) -> None:
    if ctx.actor.get("local"):
        raise AppError(409, "Sign-in is switched off, so there is no personal account to change.")


@router.get("/setup")
def setup_status(request: Request, db: Db) -> dict:
    """Tell the sign-in page whether the first admin still has to be created."""
    login = state(request).settings.require_login
    return {
        "needed": login and not users.has_users(db),
        "allowed": _setup_allowed(request, db),
        "email": mail_status(state(request).settings.smtp)["configured"],
        "login": login,
    }


@router.post("/setup")
def setup(request: Request, response: Response, body: dict, ctx: AnonCtx) -> dict:
    """Create the first admin account and sign it in."""
    if not _setup_allowed(request, ctx.db):
        raise AppError(403, "Create the first admin on the computer running GridShift." if not users.has_users(ctx.db) else "An admin account already exists. Sign in instead.")
    user = users.create_first_admin(ctx, body)
    create_session(ctx.db, request, response, ctx.settings, user["id"])
    return _me(user)


@router.post("/login")
def login(request: Request, response: Response, body: dict, ctx: AnonCtx) -> dict:
    """Sign in with email and password."""
    user = users.authenticate(ctx, body.get("email"), body.get("password"))
    create_session(ctx.db, request, response, ctx.settings, user["id"])
    return _me(user)


@router.post("/logout")
def logout(request: Request, response: Response, ctx: AuthCtx) -> dict:
    """Sign out of this browser."""
    end_session(ctx.db, request, response, ctx.settings)
    record(ctx.db, ctx.actor, "auth.logout", ctx.origin, entity="user", entity_id=ctx.actor["id"])
    return {"ok": True}


@router.get("/me")
def me(user: User) -> dict:
    """Return the signed-in user and their permissions."""
    return _me(user)


@router.post("/invite")
def invite_details(body: dict, db: Db) -> dict:
    """Show who an invitation is for; the token travels in the body so it stays out of logs."""
    return users.invite_details(db, body.get("token"))


@router.post("/accept-invite")
def accept_invite(request: Request, response: Response, body: dict, ctx: AnonCtx) -> dict:
    """Set a password from an invitation and sign in."""
    user = users.accept_invite(ctx, body)
    create_session(ctx.db, request, response, ctx.settings, user["id"])
    return _me(user)


@router.post("/forgot-password")
def forgot_password(body: dict, ctx: AnonCtx) -> dict:
    """Email a reset link; the answer never says whether the email has an account."""
    return {"message": users.forgot_password(ctx, body.get("email"))}


@router.post("/reset-password")
def reset_password(body: dict, ctx: AnonCtx) -> dict:
    """Set a new password from a reset link."""
    users.reset_password(ctx, body)
    return {"ok": True}


@router.put("/profile")
def update_profile(body: dict, ctx: AuthCtx) -> dict:
    """Change your display name."""
    _account(ctx)
    return {**users.update_profile(ctx, body), "permissions": permissions_for(ctx.actor["role"])}


@router.post("/password")
def change_password(request: Request, response: Response, body: dict, ctx: AuthCtx) -> dict:
    """Change your password; other sessions are signed out and this one renewed."""
    _account(ctx)
    users.change_own_password(ctx, body.get("current"), body.get("new"))
    create_session(ctx.db, request, response, ctx.settings, ctx.actor["id"])
    return {"ok": True}
