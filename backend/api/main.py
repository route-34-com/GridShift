"""FastAPI application serving the planner API and the built dashboard."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from backend.api.deps import AppState
from backend.api.routes import audit, auth, exports, meter, runs, system, users
from backend.pipeline import Sources
from backend.services.errors import AppError
from backend.settings import ROOT, Settings, load_settings
from backend.store import Store

DIST = ROOT / "frontend" / "dist"
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "SAMEORIGIN",
    "Referrer-Policy": "same-origin",
}


def _mount_dashboard(app: FastAPI, dist: Path) -> None:
    root = dist.resolve()

    @app.get("/{path:path}", include_in_schema=False)
    def dashboard(path: str):
        """Serve built dashboard files, falling back to index.html for client routes."""
        if path.startswith("api/"):
            return JSONResponse({"detail": "Not found"}, status_code=404)
        target = (root / path).resolve()
        if path and target.is_file() and root in target.parents:
            return FileResponse(target)
        return FileResponse(root / "index.html", headers={"Cache-Control": "no-cache"})


def _handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    def app_error(request: Request, exc: AppError) -> JSONResponse:
        """Return a refusal as JSON with its status."""
        return JSONResponse({"detail": exc.message}, status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    def invalid_request(request: Request, exc: RequestValidationError) -> JSONResponse:
        """Return malformed requests as a plain message."""
        return JSONResponse({"detail": "The request was not in the expected format."}, status_code=422)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        """Add basic security headers to every response."""
        response = await call_next(request)
        for key, value in SECURITY_HEADERS.items():
            response.headers.setdefault(key, value)
        return response


def create_app(settings: Settings | None = None, sources: Sources | None = None, dist: Path = DIST) -> FastAPI:
    """Build the API application."""
    settings = settings or load_settings()
    app = FastAPI(title="GridShift", version="0.2.0")
    app.state.gridshift = AppState(settings, Store(settings.db_path), sources)
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
    _handlers(app)
    for module in (system, auth, users, audit, exports, runs, meter):
        app.include_router(module.router)
    if (dist / "index.html").exists():
        _mount_dashboard(app, dist)
    return app


app = create_app()
