"""Shared state for API routes."""

import threading
from dataclasses import dataclass, field

from fastapi import HTTPException, Request

from backend.pipeline import Sources
from backend.settings import Settings
from backend.store import Store


@dataclass
class AppState:
    """Settings, store and run lock shared by all requests."""

    settings: Settings
    store: Store
    sources: Sources | None = None
    lock: threading.Lock = field(default_factory=threading.Lock)


def state(request: Request) -> AppState:
    """Return the application state."""
    return request.app.state.gridshift


def latest_or_404(app: AppState) -> dict:
    """Return the newest successful run or raise 404."""
    run = app.store.latest_run(successful=True)
    if run is None:
        raise HTTPException(404, "No plan yet. Run the planner to create the first one.")
    return run
