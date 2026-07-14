"""Application exceptions that keep services independent from FastAPI."""

from app.core.types import JsonValue
from app.enums.system import ErrorCodeEnum


class AppException(Exception):
    """Base exception translated into the unified API error contract."""

    def __init__(
        self,
        error_code: ErrorCodeEnum,
        *,
        status_code: int,
        message: str | None = None,
        details: JsonValue = None,
    ) -> None:
        super().__init__(message or error_code.desc)
        self.error_code = error_code
        self.status_code = status_code
        self.message = message or error_code.desc
        self.details = details


class BusinessRuleError(AppException):
    """Raised when valid input violates a business invariant."""

    def __init__(self, message: str, details: JsonValue = None) -> None:
        super().__init__(
            ErrorCodeEnum.BAD_REQUEST,
            status_code=400,
            message=message,
            details=details,
        )


class ResourceNotFoundError(AppException):
    """Raised when the requested business resource does not exist."""

    def __init__(self, message: str = "数据不存在", details: JsonValue = None) -> None:
        super().__init__(
            ErrorCodeEnum.NOT_FOUND,
            status_code=404,
            message=message,
            details=details,
        )


class InfrastructureUnavailableError(AppException):
    """Raised when required infrastructure cannot serve the request."""

    def __init__(self, message: str, details: JsonValue = None) -> None:
        super().__init__(
            ErrorCodeEnum.DATABASE_UNAVAILABLE,
            status_code=503,
            message=message,
            details=details,
        )


class AutomationEngineError(AppException):
    """Raised when a browser or device automation engine cannot proceed."""

    def __init__(self, message: str, details: JsonValue = None) -> None:
        super().__init__(
            ErrorCodeEnum.INTERNAL_ERROR,
            status_code=500,
            message=message,
            details=details,
        )
