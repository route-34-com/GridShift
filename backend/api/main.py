"""FastAPI application serving the planner API and the built dashboard."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.deps import AppState
from backend.api.routes import runs, system
from backend.pipeline import Sources
from backend.settings import ROOT, Settings, load_settings
from backend.store import Store

DIST = ROOT / "frontend" / "dist"


def create_app(settings: Settings | None = None, sources: Sources | None = None) -> FastAPI:
    """Build the API application."""
    settings = settings or load_settings()
    app = FastAPI(title="GridShift", version="0.1.0")
    app.state.gridshift = AppState(settings, Store(settings.db_path), sources)
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["*"], allow_headers=["*"])
    app.include_router(system.router)
    app.include_router(runs.router)
    if DIST.exists():
        app.mount("/", StaticFiles(directory=DIST, html=True), name="dashboard")
    return app


app = create_app()
