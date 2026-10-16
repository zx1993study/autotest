"""Validate every row in a filtered API response without evaluating expressions."""

import json
from datetime import datetime
from decimal import Decimal, InvalidOperation

from app.schemas.api_query_assertion import QueryResultAssertion
from jsonpointer import JsonPointerException, resolve_pointer


def _equal(actual, expected):
    if isinstance(actual, bool) or isinstance(expected, bool):
        return type(actual) is type(expected) and actual == expected
    if actual == expected:
        return True
    if isinstance(actual, (int, float)) or isinstance(expected, (int, float)):
        try:
            return Decimal(str(actual)) == Decimal(str(expected))
        except InvalidOperation:
            return False
    return False


def _matches(actual, operator, expected):
    if actual is None or expected is None:
        return False
    if operator == "eq":
        return _equal(actual, expected)
    if operator == "contains":
        return isinstance(actual, str) and isinstance(expected, str) and bool(expected) and expected in actual
    if operator == "tokens":
        values = actual if isinstance(actual, list) else str(actual).split(",")
        wanted = expected if isinstance(expected, list) else str(expected).split(",")
        return bool(wanted) and all(any(_equal(value, item) for value in values) for item in wanted)
    if operator in {"date_ge", "date_le"}:
        left = datetime.fromisoformat(str(actual))
        right = datetime.fromisoformat(str(expected))
        if len(str(expected)) == 10:
            left, right = left.date(), right.date()
        return left >= right if operator == "date_ge" else left <= right
    raise ValueError("Unsupported query operator")


def _rule_matches(row, rule):
    paths = rule.get("paths")
    if not isinstance(paths, list) or not paths or not all(isinstance(path, str) for path in paths):
        raise ValueError("Query rule needs explicit JSON Pointer paths")
    if rule.get("operator") not in {"eq", "contains", "tokens", "date_ge", "date_le"}:
        raise ValueError("Unsupported query operator")
    for path in paths:
        try:
            actual = resolve_pointer(row, path)
        except JsonPointerException:
            continue
        if _matches(actual, rule["operator"], rule.get("expected")):
            return True
    return False


def assert_query_result(response_body, assertion):
    result = {"type": "json_query_result", "passed": False, "path": assertion.get("path"),
              "expected": {key: assertion[key] for key in ("min_items", "max_items", "rules") if key in assertion}}
    try:
        assertion = QueryResultAssertion.model_validate(assertion).model_dump()
        minimum, maximum = assertion.get("min_items", 1), assertion.get("max_items")
        rows = resolve_pointer(json.loads(response_body), assertion["path"])
        if assertion.get("collection", True) is False:
            if not isinstance(rows, dict):
                raise ValueError("Expected a JSON object")
            rows = [rows]
        if not isinstance(rows, list):
            raise TypeError("Expected a JSON array")
        rules = assertion.get("rules", [])
        if not isinstance(rules, list):
            raise TypeError("Query rules must be an array")
        # Validate malformed rules even when an empty result is expected.
        for rule in rules:
            _rule_matches({}, rule)
        bad = [index for index, row in enumerate(rows) if not all(_rule_matches(row, rule) for rule in rules)]
        result.update(actual={"count": len(rows), "mismatched_indices": bad[:10]},
                      passed=len(rows) >= minimum and (maximum is None or len(rows) <= maximum) and not bad)
    except (ValueError, TypeError, KeyError, AttributeError, JsonPointerException, InvalidOperation) as exc:
        result["message"] = str(exc)
    return result
