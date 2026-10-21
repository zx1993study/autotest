from __future__ import annotations

import re
import secrets
import time
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any


TOKEN = re.compile(r"(?<!\\)\{\{\s*([^{}]+?)\s*\}\}")
VARIABLE_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
PHONE_PREFIX = re.compile(r"1[3-9][0-9]\Z")


class DynamicValueError(ValueError):
    """An invalid dynamic value must fail before an external action is sent."""


class DynamicValueContext:
    """Freeze generated values for one execution, including retries and steps."""

    def __init__(
        self,
        variables: dict[str, Any] | None = None,
        *,
        snapshot: dict[str, Any] | None = None,
        used_phones: set[str] | None = None,
        now_ms: int | None = None,
    ) -> None:
        previous = snapshot or {}
        previous_time = previous.get("generated_at_ms", now_ms)
        self.now_ms = int(previous_time if previous_time is not None else time.time_ns() // 1_000_000)
        self.definitions = dict(variables or {})
        self.values = dict(previous.get("values") or {})
        self.templates = dict(previous.get("templates") or {})
        self.used_phones = used_phones if used_phones is not None else set()
        self.used_phones.update(value for value in self.values.values() if isinstance(value, str) and re.fullmatch(r"1[3-9][0-9]{9}", value))
        self.resolving: set[str] = set()

    def resolve(self, value: Any, path: str = "$", depth: int = 0) -> Any:
        if depth > 40:
            raise DynamicValueError(f"Dynamic value nesting is too deep at {path}")
        if isinstance(value, dict):
            return {key: self.resolve(item, f"{path}.{key}", depth + 1) for key, item in value.items()}
        if isinstance(value, list):
            return [self.resolve(item, f"{path}[{index}]", depth + 1) for index, item in enumerate(value)]
        if not isinstance(value, str):
            return value
        matches = list(TOKEN.finditer(value))
        if not matches:
            return value.replace(r"\{{", "{{")
        self.templates[path] = value
        try:
            if len(matches) == 1 and matches[0].span() == (0, len(value)):
                return deepcopy(self.value(matches[0].group(1).strip()))
            return TOKEN.sub(lambda match: self._text(self.value(match.group(1).strip())), value).replace(r"\{{", "{{")
        except DynamicValueError as exc:
            raise DynamicValueError(f"{path}: {exc}") from exc

    def value(self, token: str) -> Any:
        if token in self.values:
            return self.values[token]
        if token in self.resolving:
            raise DynamicValueError(f"Circular variable reference: {token}")
        self.resolving.add(token)
        try:
            if token in self.definitions:
                definition = self.definitions[token]
                if isinstance(definition, dict) and "generator" in definition:
                    result = self._generate(definition)
                else:
                    result = self.resolve(definition, f"$.variables.{token}")
            elif token in {"timestamp", "timestamp_ms", "datetime"}:
                result = self._generate({"generator": token})
            elif token == "random_phone" or token.startswith("random_phone:"):
                result = self._phone(token.partition(":")[2] or "138")
            elif token.startswith("random_digits:"):
                result = self._digits(token.partition(":")[2])
            else:
                raise DynamicValueError(f"Unknown dynamic variable: {token}")
            self.values[token] = result
            return result
        finally:
            self.resolving.remove(token)

    def _generate(self, definition: dict[str, Any]) -> Any:
        generator = str(definition.get("generator") or "")
        if generator == "timestamp":
            return str(self.now_ms // 1000)
        if generator == "timestamp_ms":
            return str(self.now_ms)
        if generator == "datetime":
            return datetime.fromtimestamp(self.now_ms / 1000, timezone(timedelta(hours=8))).strftime("%Y%m%d%H%M%S")
        if generator in {"phone", "random_phone"}:
            prefixes = definition.get("prefixes")
            if prefixes is not None:
                if not isinstance(prefixes, list) or not prefixes:
                    raise DynamicValueError("Phone prefixes must be a non-empty list")
                for prefix in prefixes:
                    self._validate_prefix(str(prefix))
                prefix = secrets.choice(prefixes)
            else:
                prefix = definition.get("prefix", "138")
            return self._phone(str(prefix))
        if generator == "random_digits":
            return self._digits(definition.get("length", 4))
        raise DynamicValueError(f"Unsupported dynamic generator: {generator}")

    def _validate_prefix(self, prefix: str) -> None:
        if not PHONE_PREFIX.fullmatch(prefix):
            raise DynamicValueError("Phone prefix must contain three digits and match 1[3-9][0-9]")

    def _phone(self, prefix: str) -> str:
        self._validate_prefix(prefix)
        for _ in range(100):
            phone = prefix + self._digits(8)
            if phone not in self.used_phones:
                self.used_phones.add(phone)
                return phone
        raise DynamicValueError("Unable to generate a distinct phone number for this batch")

    def _digits(self, length: Any) -> str:
        try:
            count = int(length)
        except (TypeError, ValueError) as exc:
            raise DynamicValueError("Random digit length must be an integer between 1 and 64") from exc
        if isinstance(length, bool) or str(count) != str(length) or not 1 <= count <= 64:
            raise DynamicValueError("Random digit length must be an integer between 1 and 64")
        return "".join(str(secrets.randbelow(10)) for _ in range(count))

    def _text(self, value: Any) -> str:
        if isinstance(value, (dict, list)):
            raise DynamicValueError("Object and array variables cannot be appended to text")
        if value is None:
            return ""
        return str(value)

    def snapshot(self) -> dict[str, Any]:
        return {"generated_at_ms": self.now_ms, "values": deepcopy(self.values), "templates": dict(self.templates)}


def prepare_dynamic_execution(
    case: dict[str, Any],
    payload: dict[str, Any],
    context: DynamicValueContext | None = None,
) -> tuple[dict[str, Any], dict[str, Any], DynamicValueContext]:
    """Resolve copies only; saved case templates and execution inputs stay intact."""

    data = case.get("data") if isinstance(case.get("data"), dict) else {}
    variables = data.get("variables", {})
    if variables is None:
        variables = {}
    config = payload.get("config") if isinstance(payload.get("config"), dict) else {}
    overrides = config.get("variables", {})
    if overrides is None:
        overrides = {}
    if not isinstance(variables, dict) or not isinstance(overrides, dict):
        raise DynamicValueError("Dynamic variables must be a JSON object")
    definitions = {**variables, **overrides}
    if any(not VARIABLE_NAME.fullmatch(str(name)) for name in definitions):
        raise DynamicValueError("Variable names must start with a letter or underscore and contain letters, digits or underscores")
    if context is None:
        context = DynamicValueContext(
            definitions,
            snapshot=case.get("_dynamic_values"),
            used_phones=payload.get("_dynamic_phone_reservations"),
        )
    resolved_case = deepcopy(case)
    resolved_data = dict(data)
    resolved_data.pop("variables", None)
    resolved_case["data"] = context.resolve(resolved_data, "$.data")
    resolved_case["data"]["variables"] = {name: context.value(str(name)) for name in definitions}
    for key in ("steps", "assertions"):
        if key in case:
            resolved_case[key] = context.resolve(case[key], f"$.{key}")
    resolved_payload = {key: deepcopy(value) for key, value in payload.items() if key != "_dynamic_phone_reservations"}
    resolved_config = {key: value for key, value in config.items() if key != "variables"}
    resolved_payload["config"] = context.resolve(resolved_config, "$.config")
    resolved_case["_dynamic_values"] = context.snapshot()
    return resolved_case, resolved_payload, context
