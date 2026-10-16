from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth_middleware import register_auth_middleware
from app.api.exception_handlers import register_exception_handlers
from app.api.v1.router import api_router
from app.api.health import router as health_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.init_db import try_init_db


def _frontend_dist_candidates() -> list[Path]:
    configured = os.getenv("AUTOTEST_FRONTEND_DIST", "").strip()
    candidates: list[Path] = []
    if configured:
        candidates.append(Path(configured))
    candidates.append(Path(__file__).resolve().parents[2] / "frontend" / "dist")
    return candidates


def _mount_frontend(app: FastAPI) -> None:
    frontend_dist = next(
        (candidate for candidate in _frontend_dist_candidates() if (candidate / "index.html").exists()),
        None,
    )
    if frontend_dist is None:
        return

    index_file = frontend_dist / "index.html"
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend_entry(path: str):
        page_path = path.rstrip("/")
        # API management pages share /api with the versioned backend namespace.
        is_api_page = any(page_path == prefix or (
            page_path.startswith(f"{prefix}/") and page_path.removeprefix(f"{prefix}/").isdigit()
        ) for prefix in ("api/interfaces", "api/flows"))
        if path.startswith("api/") and not is_api_page:
            return JSONResponse(status_code=404, content={"code": 404, "message": "Not Found", "data": None})
        return FileResponse(index_file, headers={"Cache-Control": "no-store, max-age=0", "Pragma": "no-cache"})


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Initialize infrastructure once while allowing readiness degradation."""

    try_init_db()
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    configure_logging(settings.resolved_log_dir, settings.log_level)
    app = FastAPI(title="Autotest Platform", version="0.2.0", lifespan=lifespan)
    register_exception_handlers(app)
    register_auth_middleware(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix="/api/v1")
    app.include_router(health_router)

    _mount_frontend(app)
    return app


app = create_app()
