"""System-level error codes."""

from app.enums.base import DescribedIntEnum


class ErrorCodeEnum(DescribedIntEnum):
    """Stable API error codes independent of HTTP status codes."""

    BAD_REQUEST = (40000, "请求参数错误")
    NOT_FOUND = (40400, "资源不存在")
    VALIDATION_ERROR = (42200, "请求数据校验失败")
    DATABASE_UNAVAILABLE = (50301, "数据库暂不可用")
    INTERNAL_ERROR = (50000, "服务器内部错误")
