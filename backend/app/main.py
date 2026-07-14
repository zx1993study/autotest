from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth_middleware import register_auth_middleware
from app.api.exception_handlers import register_exception_handlers
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.init_db import try_init_db


def _mount_frontend(app: FastAPI) -> None:
    frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    index_file = frontend_dist / "index.html"
    if not index_file.exists():
        return

    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend_entry(path: str):
        if path.startswith("api/"):
            return JSONResponse(status_code=404, content={"code": 404, "message": "Not Found", "data": None})
        return FileResponse(index_file)


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

    _mount_frontend(app)
    return app


app = create_app()
