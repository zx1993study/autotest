from collections.abc import Sequence
from typing import TypeVar


ResponseData = TypeVar("ResponseData")


def success(
    data: ResponseData | None = None,
    message: str = "success",
) -> dict[str, object]:
    """Build the stable success envelope consumed by the frontend."""

    return {"code": 0, "message": message, "data": data}


def page_result(
    items: Sequence[object],
    total: int,
    page: int,
    page_size: int,
) -> dict[str, object]:
    """Build a paginated success response without coupling to ORM entities."""

    return success(
        {
            "items": list(items),
            "total": total,
            "page": page,
            "pageSize": page_size,
        }
    )


def error_response(
    code: int,
    message: str,
    data: object | None = None,
) -> dict[str, object]:
    """Build the stable error envelope used by global exception handlers."""

    return {"code": code, "message": message, "data": data}
