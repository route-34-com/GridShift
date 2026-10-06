"""Shared state and dependencies for API routes."""

import sqlite3
import threading
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Annotated

from fastapi import Depends, Request

from backend.auth.permissions import can
from backend.auth.sessions import client_ip, session_user, user_agent
from backend.database import connect
from backend.datasets import DataSet, resolve
from backend.pipeline import Sources
from backend.services.audit import Origin
from backend.services.context import Ctx
from backend.services.errors import AppError
from backend.settings import Settings
from backend.store import Store


@dataclass
class AppState:
    """Settings, store and run lock shared by all requests."""

    settings: Settings
    store: Store
    sources: Sources | None = None
    lock: threading.Lock = field(default_factory=threading.Lock)

    @property
    def data(self) -> DataSet:
        """Settings and store for the data set in use (sample or the company's own)."""
        return resolve(self.settings, self.store)


def state(request: Request) -> AppState:
    """Return the application state."""
    return request.app.state.gridshift


def get_db(request: Request) -> Iterator[sqlite3.Connection]:
    """Open one transaction for the request."""
    with connect(state(request).settings.db_path) as db:
        yield db


def origin(request: Request) -> Origin:
    """Return the caller's address and browser."""
    return Origin(client_ip(request, state(request).settings), user_agent(request))


def get_ctx(request: Request, db: Annotated[sqlite3.Connection, Depends(get_db)]) -> Ctx:
    """Return the service context for an anonymous request."""
    return Ctx(db, state(request).settings, None, origin(request), str(request.base_url))


#: Who acts when sign-in is switched off. Has no account row, so it can't change a password or sign out.
LOCAL_ADMIN = {"id": None, "email": "local@gridshift", "name": "Local admin", "role": "admin", "status": "active", "created_at": None, "last_login_at": None, "local": True}


def get_user(request: Request, db: Annotated[sqlite3.Connection, Depends(get_db)]) -> dict:
    """Return the signed-in user, the local admin when sign-in is off, or answer 401."""
    user = session_user(db, request)
    if not user and not state(request).settings.require_login:
        return dict(LOCAL_ADMIN)
    if not user:
        raise AppError(401, "Please sign in.")
    return user


def get_auth_ctx(ctx: Annotated[Ctx, Depends(get_ctx)], user: Annotated[dict, Depends(get_user)]) -> Ctx:
    """Return the service context for a signed-in request."""
    ctx.actor = user
    return ctx


def require(permission: str):
    """Return a dependency that refuses users without a permission."""

    def check(user: Annotated[dict, Depends(get_user)]) -> dict:
        if not can(user, permission):
            raise AppError(403, "Your role doesn't allow this. Ask an admin.")
        return user

    return Depends(check)


def latest_or_404(app: AppState) -> dict:
    """Return the newest successful run or raise 404."""
    run = app.data.store.latest_run(successful=True)
    if run is None:
        raise AppError(404, "No plan yet. Run the planner to create the first one.")
    return run


AppDep = Annotated[AppState, Depends(state)]
Db = Annotated[sqlite3.Connection, Depends(get_db)]
AnonCtx = Annotated[Ctx, Depends(get_ctx)]
AuthCtx = Annotated[Ctx, Depends(get_auth_ctx)]
User = Annotated[dict, Depends(get_user)]
