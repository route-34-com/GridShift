"""FastAPI application serving the planner API and the built dashboard."""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from backend.api.deps import AppState
from backend.api.routes import runs, system
from backend.pipeline import Sources
from backend.settings import ROOT, Settings, load_settings
from backend.store import Store

DIST = ROOT / "frontend" / "dist"


def _mount_dashboard(app: FastAPI, dist: Path) -> None:
    root = dist.resolve()

    @app.get("/{path:path}", include_in_schema=False)
    def dashboard(path: str) -> FileResponse:
        """Serve built dashboard files, falling back to index.html for client routes."""
        if path.startswith("api/"):
            raise HTTPException(404, "Not found")
        target = (root / path).resolve()
        if path and target.is_file() and root in target.parents:
            return FileResponse(target)
        return FileResponse(root / "index.html")


def create_app(settings: Settings | None = None, sources: Sources | None = None, dist: Path = DIST) -> FastAPI:
    """Build the API application."""
    settings = settings or load_settings()
    app = FastAPI(title="GridShift", version="0.1.0")
    app.state.gridshift = AppState(settings, Store(settings.db_path), sources)
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["*"], allow_headers=["*"])
    app.include_router(system.router)
    app.include_router(runs.router)
    if (dist / "index.html").exists():
        _mount_dashboard(app, dist)
    return app


app = create_app()
