"""Global exception-to-response translation for the presentation layer."""

import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppException
from app.core.response import error_response
from app.enums.system import ErrorCodeEnum


logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Register all transport-specific exception handlers in one place."""

    @app.exception_handler(AppException)
    async def app_exception_handler(
        request: Request,
        exc: AppException,
    ) -> JSONResponse:
        payload = error_response(
            exc.error_code.code,
            exc.message,
            {"path": request.url.path, "details": exc.details},
        )
        return JSONResponse(status_code=exc.status_code, content=jsonable_encoder(payload))

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        payload = error_response(
            ErrorCodeEnum.VALIDATION_ERROR.code,
            ErrorCodeEnum.VALIDATION_ERROR.desc,
            {"path": request.url.path, "errors": exc.errors()},
        )
        return JSONResponse(status_code=422, content=jsonable_encoder(payload))

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        message = str(exc.detail)
        code = (
            ErrorCodeEnum.NOT_FOUND.code
            if exc.status_code == 404
            else ErrorCodeEnum.BAD_REQUEST.code
        )
        payload = error_response(code, message, {"path": request.url.path})
        return JSONResponse(status_code=exc.status_code, content=jsonable_encoder(payload))

    @app.exception_handler(SQLAlchemyError)
    async def database_exception_handler(
        request: Request,
        exc: SQLAlchemyError,
    ) -> JSONResponse:
        logger.exception("Database operation failed for %s", request.url.path, exc_info=exc)
        payload = error_response(
            ErrorCodeEnum.DATABASE_UNAVAILABLE.code,
            "数据库连接失败，请检查服务端数据库配置。",
            {"path": request.url.path},
        )
        return JSONResponse(status_code=503, content=jsonable_encoder(payload))

    @app.exception_handler(Exception)
    async def unexpected_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.exception("Unhandled application error for %s", request.url.path, exc_info=exc)
        payload = error_response(
            ErrorCodeEnum.INTERNAL_ERROR.code,
            ErrorCodeEnum.INTERNAL_ERROR.desc,
            {"path": request.url.path},
        )
        return JSONResponse(status_code=500, content=jsonable_encoder(payload))
