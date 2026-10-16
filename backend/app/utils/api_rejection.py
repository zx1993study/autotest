"""Distinguish a deliberate client-input rejection from an internal failure."""

import json

INTERNAL_ERROR_MARKERS = (
    "invalid keyword argument", "sqlalchemy", "pymysql", "integrityerror",
    "operationalerror", "programmingerror", "traceback", "attributeerror",
    "typeerror", "keyerror", "data too long", "cannot be null", "unknown column",
    "you have an error in your sql", "object has no attribute", "duplicate entry",
    "not json serializable", "unsupported operand", "foreign key constraint",
)


def assert_api_rejection(status, body, expected, allowed_business_errors=None):
    try:
        response = json.loads(body)
    except (ValueError, TypeError):
        response = {}
    response = response if isinstance(response, dict) else {}
    code = response.get("code")
    message = str(response.get("msg") or response.get("message") or body)
    internal = any(marker in message.lower() for marker in INTERNAL_ERROR_MARKERS)
    auth_rejection = status in {401, 403} or (status == 200 and str(code) in {"401", "403"})
    validation_rejection = status in {400, 409, 422} or (status == 200 and str(code) in {"400", "409", "422"})
    allowed = allowed_business_errors if isinstance(allowed_business_errors, list) else []
    if status == 200 and str(code) == "500" and message in allowed:
        validation_rejection = True
    passed = (auth_rejection if expected == "auth" else validation_rejection) and not internal
    return {"type": "api_rejection", "passed": passed, "expected": expected,
            "actual": {"http_status": status, "code": code},
            "message": "Internal error is not a validation rejection" if internal else message[:500]}
