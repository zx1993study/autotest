import json
from decimal import Decimal, InvalidOperation

from jsonpointer import JsonPointerException, resolve_pointer


def assert_number_delta(response_body, assertion):
    result = {"type": "json_number_delta", "path": assertion.get("path"), "passed": False,
              "expected": assertion.get("expected"), "baseline": assertion.get("baseline")}
    try:
        actual = resolve_pointer(json.loads(response_body), assertion["path"])
        values = (actual, assertion["baseline"], assertion["expected"])
        if any(isinstance(value, bool) or value is None for value in values):
            raise ValueError("Numeric delta requires explicit finite numbers")
        current, baseline, expected = (Decimal(str(value)) for value in values)
        if not all(value.is_finite() for value in (current, baseline, expected)):
            raise ValueError("Numeric delta requires explicit finite numbers")
        result.update(actual=str(current - baseline), passed=current - baseline == expected)
    except (ValueError, KeyError, TypeError, InvalidOperation, JsonPointerException) as exc:
        result["message"] = str(exc)
    return result
