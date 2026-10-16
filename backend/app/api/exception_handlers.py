"""Global exception-to-response translation for the presentation layer."""

import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError, DisconnectionError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppException
from app.core.response import error_response
from app.enums.system import ErrorCodeEnum

logger = logging.getLogger(__name__)


def _database_error_message(exc: SQLAlchemyError) -> str:
    args = getattr(getattr(exc, "orig", None), "args", ())
    error_number = args[0] if args else None
    if error_number == 1038:
        return "数据库查询排序内存不足，请联系管理员优化查询。"
    if (
        error_number in (1045, 1049, 2002, 2003, 2005, 2006, 2013, 2055)
        or isinstance(exc, DisconnectionError)
        or (isinstance(exc, DBAPIError) and exc.connection_invalidated)
    ):
        return "数据库连接失败，请检查服务端数据库配置。"
    return "数据库操作失败，请查看服务端日志。"


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
            _database_error_message(exc),
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
