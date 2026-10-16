from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from app.core.response import error_response
from app.core.config import settings
from app.db.session import SessionLocal
from app.enums.system import ErrorCodeEnum
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.services.auth_service import AuthService


PUBLIC_API_PREFIXES = (
    "/api/v1/auth/login",
    "/api/v1/auth/bootstrap",
    "/api/v1/agent/runtime",
    "/api/v1/system/database-status",
)


def register_auth_middleware(app: FastAPI) -> None:
    """Protect API routes with bearer-token authentication."""

    @app.middleware("http")
    async def auth_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if _is_public_request(request):
            return await call_next(request)

        token = _bearer_token(request.headers.get("Authorization", "")) or _screenshot_query_token(request)
        if not token:
            return _unauthorized("请先登录")

        db = SessionLocal()
        try:
            user = AuthService(SqlAlchemyResourceRepository(db)).current_user_from_token(token)
            request.state.current_user = user
        except Exception:  # noqa: BLE001 - middleware must normalize auth failures.
            return _unauthorized("登录状态已失效，请重新登录")
        finally:
            db.close()
        return await call_next(request)


def _is_public_request(request: Request) -> bool:
    path = request.url.path
    if request.method.upper() == "OPTIONS":
        return True
    if not path.startswith("/api/v1"):
        return True
    if path.startswith("/api/v1/screenshots") and settings.allow_public_screenshots:
        return True
    return any(path.startswith(prefix) for prefix in PUBLIC_API_PREFIXES)


def _bearer_token(header_value: str) -> str:
    prefix = "Bearer "
    if not header_value.startswith(prefix):
        return ""
    return header_value[len(prefix) :].strip()


def _screenshot_query_token(request: Request) -> str:
    if not request.url.path.startswith(("/api/v1/screenshots/", "/api/v1/app-recordings/")):
        return ""
    return str(request.query_params.get("access_token") or "").strip()


def _unauthorized(message: str) -> JSONResponse:
    payload = error_response(ErrorCodeEnum.BAD_REQUEST.code, message)
    return JSONResponse(status_code=401, content=payload)
