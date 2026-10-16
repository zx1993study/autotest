"""Build deterministic API test-case payloads from OpenAPI field constraints."""

from __future__ import annotations

import json
import math
from copy import deepcopy
from typing import Any

from app.services.api_natural_input_service import natural_text_example
from app.services.test_strategy_utils import (
    case_json,
    category_label,
    is_auth_strategy,
    knowledge_key,
    knowledge_keys,
    strategy_category,
    with_strategy_meta,
)

FORMAT_EXAMPLES: dict[str, Any] = {
    "date": "2026-01-15",
    "date-time": "2026-01-15T10:30:00Z",
    "email": "tester@example.com",
    "uuid": "123e4567-e89b-12d3-a456-426614174000",
    "uri": "https://example.com/resource",
    "url": "https://example.com/resource",
    "hostname": "api.example.com",
    "ipv4": "192.0.2.1",
    "ipv6": "2001:db8::1",
}
FORMAT_INVALID_VALUES = {key: "not-a-valid-value" for key in FORMAT_EXAMPLES}
MAX_STRING_BOUNDARY = 1024
MAX_ARRAY_BOUNDARY = 20


class ApiCaseTemplateBuilder:
    """Apply project knowledge or native OpenAPI strategies to API metadata."""

    def build(
        self,
        interface: dict[str, Any],
        fields: list[dict[str, Any]],
        strategy: str,
        strategies: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Keep the legacy rule-based generation contract."""

        base = self._base_request(interface, fields)
        normal = case_json("API", "[正常]", "normal", base, self._success_status(interface))
        normal["strategy_ids"] = [item["id"] for item in strategies if strategy_category(item) == "normal"]
        normal["knowledge_keys"] = knowledge_keys(strategies, "normal")
        cases = [normal]
        if strategies:
            for item in strategies:
                category = strategy_category(item)
                if category != "normal":
                    cases.extend(self._strategy_cases(interface, fields, base, item, category))
            return cases
        return [*cases, *self._fallback_cases(fields, base, strategy)]

    def build_from_openapi(
        self,
        interface: dict[str, Any],
        fields: list[dict[str, Any]],
        generation_strategies: set[str],
        knowledge_strategies: list[dict[str, Any]] | None = None,
        *,
        normal_request: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Generate bounded, explainable cases directly from OpenAPI constraints."""

        data = self._data(interface)
        base = deepcopy(normal_request) if normal_request is not None else self._base_request(interface, fields)
        cases: list[dict[str, Any]] = []

        if "normal" in generation_strategies:
            generated = case_json("API", "[正常]", "normal", deepcopy(base), self._success_status(interface))
            generated["assertions"] = self._status_assertions(interface, "normal")
            generated["strategy_ids"] = [
                int(item["id"])
                for item in knowledge_strategies or []
                if strategy_category(item) == "normal"
            ]
            generated["knowledge_keys"] = knowledge_keys(knowledge_strategies or [], "normal")
            content_types = [str(item) for item in data.get("response_content_types") or [] if item]
            if content_types:
                generated["assertions"].append({"type": "content_type_in", "expected": content_types})
            cases.append(self._tag_scenario(generated, "normal"))

        for field in fields:
            field_data = self._data(field)
            name = self._field_name(field)
            if not name:
                continue
            location = str(field_data.get("location") or "body")
            scenario_field = self._scenario_field(location, name)
            if "required" in generation_strategies and field_data.get("required") and location != "path":
                cases.append(
                    self._negative_case(
                        interface,
                        f"[缺失必填] {name}",
                        "required_missing",
                        self._without_field(base, field_data),
                        "required",
                        scenario_field,
                        "missing",
                    )
                )

            if "boundary" in generation_strategies:
                for variant, label, value, valid in self._boundary_variants(field_data):
                    original = (base.get("params") or {}).get(name)
                    if normal_request is not None and isinstance(value, list) and isinstance(original, list) and original:
                        value = [deepcopy(original[index % len(original)]) for index in range(len(value))]
                    request = self._replace_field(base, field_data, value)
                    generated = (
                        self._positive_case(interface, f"[{label}] {name}", "boundary", request)
                        if valid
                        else self._negative_case(
                            interface,
                            f"[{label}] {name}",
                            "boundary",
                            request,
                            "boundary",
                            scenario_field,
                            variant,
                        )
                    )
                    cases.append(self._tag_scenario(generated, "boundary", scenario_field, variant))

            schema = self._schema(field_data)
            enum_values = schema.get("enum") if isinstance(schema.get("enum"), list) else []
            if "enum" in generation_strategies and enum_values:
                for index, value in enumerate(enum_values[:3]):
                    cases.append(
                        self._tag_scenario(
                            self._positive_case(
                                interface,
                                f"[枚举值] {name} = {self._short_value(value)}",
                                "enum",
                                self._replace_field(base, field_data, value),
                            ),
                            "enum",
                            scenario_field,
                            f"valid-{index}",
                        )
                    )
                invalid_value = self._invalid_enum_value(enum_values, field_data)
                cases.append(
                    self._negative_case(
                        interface,
                        f"[非法枚举] {name} = {self._short_value(invalid_value)}",
                        "enum_invalid",
                        self._replace_field(base, field_data, invalid_value),
                        "enum",
                        scenario_field,
                        "invalid",
                    )
                )

            value_format = str(schema.get("format") or "").lower()
            if "format" in generation_strategies and value_format in FORMAT_INVALID_VALUES:
                cases.append(
                    self._negative_case(
                        interface,
                        f"[格式错误] {name} ({value_format})",
                        "format_invalid",
                        self._replace_field(base, field_data, FORMAT_INVALID_VALUES[value_format]),
                        "format",
                        scenario_field,
                        value_format,
                    )
                )

            if "type" in generation_strategies:
                cases.append(
                    self._negative_case(
                        interface,
                        f"[类型错误] {name}",
                        "type_invalid",
                        self._replace_field(base, field_data, self._invalid_value(field_data)),
                        "type",
                        scenario_field,
                        "invalid",
                    )
                )

        security = data.get("security")
        if "auth" in generation_strategies and self._requires_auth(security):
            request = deepcopy(base)
            request["skip_auth"] = True
            generated = case_json("API", "[未鉴权]", "auth", request, 401)
            generated["assertions"] = self._status_assertions(interface, "auth")
            cases.append(self._tag_scenario(generated, "auth"))

        for item in knowledge_strategies or []:
            category = strategy_category(item)
            if category == "normal":
                continue
            for index, generated in enumerate(self._strategy_cases(interface, fields, base, item, category)):
                cases.append(
                    self._tag_scenario(
                        generated,
                        "knowledge",
                        variant=f"{int(item['id'])}-{index}",
                    )
                )
        return cases

    def _requires_auth(self, security: Any) -> bool:
        if not isinstance(security, list) or not security:
            return False
        requirements = [item for item in security if isinstance(item, dict)]
        return bool(requirements) and all(bool(item) for item in requirements)

    def _scenario_field(self, location: str, name: str) -> str:
        return name if location == "body" and name == "body" else f"{location}.{name}"

    def _positive_case(
        self,
        interface: dict[str, Any],
        name: str,
        category: str,
        request: dict[str, Any],
    ) -> dict[str, Any]:
        generated = case_json("API", name, category, request, self._success_status(interface))
        generated["assertions"] = self._status_assertions(interface, "normal")
        return generated

    def _negative_case(
        self,
        interface: dict[str, Any],
        name: str,
        category: str,
        request: dict[str, Any],
        strategy: str,
        field: str,
        variant: str,
    ) -> dict[str, Any]:
        generated = case_json("API", name, category, request, 400)
        generated["assertions"] = self._status_assertions(interface, "negative")
        return self._tag_scenario(generated, strategy, field, variant)

    def _tag_scenario(
        self,
        generated: dict[str, Any],
        strategy: str,
        field: str = "",
        variant: str = "default",
    ) -> dict[str, Any]:
        generated["openapi_scenario"] = {
            "strategy": strategy,
            "field": field,
            "variant": variant,
            "key": ":".join(filter(None, [strategy, field, variant])),
        }
        return generated

    def _base_request(self, interface: dict[str, Any], fields: list[dict[str, Any]]) -> dict[str, Any]:
        interface_data = self._data(interface)
        request: dict[str, Any] = {
            "method": str(interface_data.get("method") or "GET").upper(),
            "path": str(interface_data.get("path") or interface.get("name") or ""),
            "headers": {},
            "query": {},
            "body": {},
            "params": {},
        }
        content_type = interface_data.get("content_type")
        if content_type:
            request["content_type"] = str(content_type)
        api_base_path = interface_data.get("api_base_path")
        if api_base_path:
            request["api_base_path"] = str(api_base_path)

        for field in fields:
            data = self._data(field)
            name = self._field_name(field)
            if not name:
                continue
            value = self._normal_value(data)
            location = str(data.get("location") or "body")
            if location == "body" and name == "body":
                request["body"] = deepcopy(value)
                continue
            request["params"][name] = deepcopy(value)
            if location == "query":
                request["query"][name] = deepcopy(value)
            elif location == "header":
                request["headers"][name] = str(value)
            elif location == "body" and isinstance(request["body"], dict):
                request["body"][name] = deepcopy(value)
        return request

    def _fallback_cases(
        self,
        fields: list[dict[str, Any]],
        base: dict[str, Any],
        strategy: str,
    ) -> list[dict[str, Any]]:
        cases: list[dict[str, Any]] = []
        if strategy in {"basic", "full"}:
            for field in fields:
                data = self._data(field)
                if data.get("required") and self._field_name(field):
                    cases.append(
                        case_json(
                            "API",
                            f"[缺失必填] {self._field_name(field)}",
                            "required_missing",
                            self._without_field(base, data),
                            400,
                        )
                    )
        if strategy == "full":
            for field in fields:
                data = self._data(field)
                cases.append(
                    case_json(
                        "API",
                        f"[异常] {self._field_name(field)}",
                        "invalid",
                        self._replace_field(base, data, self._invalid_value(data)),
                        400,
                    )
                )
        return cases

    def _strategy_cases(
        self,
        interface: dict[str, Any],
        fields: list[dict[str, Any]],
        base: dict[str, Any],
        strategy: dict[str, Any],
        category: str,
    ) -> list[dict[str, Any]]:
        strategy_id = int(strategy["id"])
        key = knowledge_key(strategy)
        required = [field for field in fields if self._data(field).get("required")]
        candidates = required or fields
        if category == "required_empty":
            return [
                self._tagged_field_case(
                    "缺失必填",
                    "required_missing",
                    field,
                    self._without_field(base, self._data(field)),
                    strategy_id,
                    key,
                )
                for field in required
                if self._field_name(field)
            ]
        if category == "boundary":
            return [
                self._tagged_field_case(
                    "边界场景",
                    "boundary",
                    field,
                    self._replace_field(base, self._data(field), self._boundary_value(self._data(field))),
                    strategy_id,
                    key,
                )
                for field in candidates
                if self._field_name(field)
            ]
        if category == "security" and is_auth_strategy(strategy):
            request = deepcopy(base)
            request["skip_auth"] = True
            return [
                with_strategy_meta(
                    case_json("API", "[未登录]", "auth", request, 401),
                    strategy_id,
                    key,
                )
            ]
        if category in {"invalid", "security"}:
            return self._invalid_strategy_cases(candidates[:5], base, category, strategy_id, key)
        generated = case_json(
            "API",
            f"[{category_label(category)}] {strategy.get('name')}",
            category,
            deepcopy(base),
            200 if category == "strategy" else 400,
        )
        return [with_strategy_meta(generated, strategy_id, key)]

    def _invalid_strategy_cases(
        self,
        fields: list[dict[str, Any]],
        base: dict[str, Any],
        category: str,
        strategy_id: int,
        key: str | None,
    ) -> list[dict[str, Any]]:
        value_override = "' OR 1=1 --" if category == "security" else None
        return [
            self._tagged_field_case(
                category_label(category),
                category,
                field,
                self._replace_field(
                    base,
                    self._data(field),
                    value_override if value_override is not None else self._invalid_value(self._data(field)),
                ),
                strategy_id,
                key,
            )
            for field in fields
            if self._field_name(field)
        ]

    def _tagged_field_case(
        self,
        label: str,
        category: str,
        field: dict[str, Any],
        request: dict[str, Any],
        strategy_id: int,
        key: str | None,
    ) -> dict[str, Any]:
        generated = case_json("API", f"[{label}] {self._field_name(field)}", category, request, 400)
        return with_strategy_meta(generated, strategy_id, key)

    def _without_field(self, request: dict[str, Any], field: dict[str, Any]) -> dict[str, Any]:
        copied = deepcopy(request)
        name = str(field.get("name") or "")
        params = copied.get("params")
        if isinstance(params, dict):
            params.pop(name, None)
        location = str(field.get("location") or "body")
        if location == "body" and name == "body":
            copied["body"] = None
            return copied
        target = "headers" if location == "header" else location
        container = copied.get(target)
        if isinstance(container, dict):
            container.pop(name, None)
        return copied

    def _replace_field(self, request: dict[str, Any], field: dict[str, Any], value: Any) -> dict[str, Any]:
        copied = self._without_field(request, field)
        name = str(field.get("name") or "")
        if not name:
            return copied
        location = str(field.get("location") or "body")
        if location == "body" and name == "body":
            copied["body"] = deepcopy(value)
            return copied
        params = copied.get("params")
        if isinstance(params, dict):
            params[name] = deepcopy(value)
        target = "headers" if location == "header" else location
        container = copied.get(target)
        if isinstance(container, dict):
            container[name] = str(value) if location == "header" else deepcopy(value)
        return copied

    def _boundary_variants(self, field: dict[str, Any]) -> list[tuple[str, str, Any, bool]]:
        schema = self._schema(field)
        data_type = str(schema.get("type") or field.get("field_type") or field.get("type") or "string")
        variants: list[tuple[str, str, Any, bool]] = []
        if data_type in {"integer", "number"}:
            step = schema.get("multipleOf")
            if not self._is_number(step) or float(step) <= 0:
                step = 1 if data_type == "integer" else 0.1
            minimum, minimum_exclusive = self._numeric_limit(schema, "minimum")
            maximum, maximum_exclusive = self._numeric_limit(schema, "maximum")
            if minimum is not None:
                valid = minimum + step if minimum_exclusive else minimum
                invalid = minimum if minimum_exclusive else minimum - step
                variants.extend(
                    [
                        ("minimum-valid", "最小边界", self._number_value(valid, data_type), True),
                        ("minimum-invalid", "低于最小值", self._number_value(invalid, data_type), False),
                    ]
                )
            if maximum is not None:
                valid = maximum - step if maximum_exclusive else maximum
                invalid = maximum if maximum_exclusive else maximum + step
                variants.extend(
                    [
                        ("maximum-valid", "最大边界", self._number_value(valid, data_type), True),
                        ("maximum-invalid", "超过最大值", self._number_value(invalid, data_type), False),
                    ]
                )
        elif data_type == "string":
            minimum = self._safe_int(schema.get("minLength"))
            maximum = self._safe_int(schema.get("maxLength"))
            if minimum is not None and 0 <= minimum <= MAX_STRING_BOUNDARY:
                variants.append(("min-length-valid", "最小长度", "x" * minimum, True))
                if minimum > 0:
                    variants.append(("min-length-invalid", "低于最小长度", "x" * (minimum - 1), False))
            if maximum is not None and 0 <= maximum < MAX_STRING_BOUNDARY:
                variants.extend(
                    [
                        ("max-length-valid", "最大长度", "x" * maximum, True),
                        ("max-length-invalid", "超过最大长度", "x" * (maximum + 1), False),
                    ]
                )
        elif data_type == "array":
            item_value = self._value_for_schema(schema.get("items") if isinstance(schema.get("items"), dict) else {})
            minimum = self._safe_int(schema.get("minItems"))
            maximum = self._safe_int(schema.get("maxItems"))
            if minimum is not None and 0 <= minimum <= MAX_ARRAY_BOUNDARY:
                variants.append(("min-items-valid", "最少元素", [deepcopy(item_value) for _ in range(minimum)], True))
                if minimum > 0:
                    variants.append(
                        ("min-items-invalid", "少于最少元素", [deepcopy(item_value) for _ in range(minimum - 1)], False)
                    )
            if maximum is not None and 0 <= maximum < MAX_ARRAY_BOUNDARY:
                variants.extend(
                    [
                        ("max-items-valid", "最多元素", [deepcopy(item_value) for _ in range(maximum)], True),
                        ("max-items-invalid", "超过最多元素", [deepcopy(item_value) for _ in range(maximum + 1)], False),
                    ]
                )
        return variants

    def _status_assertions(self, interface: dict[str, Any], mode: str) -> list[dict[str, Any]]:
        statuses = [str(item).upper() for item in self._data(interface).get("expected_statuses") or []]
        if mode == "normal":
            expected = [item for item in statuses if self._status_class(item) in {2, 3}] or ["2XX", "3XX"]
        elif mode == "auth":
            expected = [item for item in statuses if item in {"401", "403"}] or [401, 403]
        else:
            expected = [item for item in statuses if self._status_class(item) == 4] or ["4XX"]
        if len(expected) == 1 and str(expected[0]).isdigit():
            return [{"type": "status", "expected": int(expected[0])}]
        return [{"type": "status_in", "expected": expected}]

    def _normal_value(self, field: dict[str, Any]) -> Any:
        if field.get("example_provided"):
            return deepcopy(field.get("example"))
        if "example" in field and field.get("example") is not None:
            return deepcopy(field["example"])
        if "default_value" in field and field.get("default_value") is not None:
            return deepcopy(field["default_value"])
        value = self._value_for_schema(self._schema(field), field)
        schema = self._schema(field)
        if isinstance(value, str) and not schema.get("enum") and not schema.get("format") and not schema.get("pattern"):
            natural = natural_text_example(field, value)
            maximum = self._safe_int(schema.get("maxLength"))
            minimum = self._safe_int(schema.get("minLength")) or 0
            if maximum is not None:
                natural = natural[:maximum]
            return natural.ljust(minimum, "字")
        return value

    def _value_for_schema(self, schema: dict[str, Any], fallback: dict[str, Any] | None = None) -> Any:
        if "example" in schema:
            return deepcopy(schema["example"])
        if "default" in schema:
            return deepcopy(schema["default"])
        enum_values = schema.get("enum")
        if isinstance(enum_values, list) and enum_values:
            return deepcopy(enum_values[0])
        value_format = str(schema.get("format") or "").lower()
        if value_format in FORMAT_EXAMPLES:
            return FORMAT_EXAMPLES[value_format]
        data_type = str(schema.get("type") or (fallback or {}).get("field_type") or "string")
        if data_type == "integer":
            minimum, exclusive = self._numeric_limit(schema, "minimum")
            return int((minimum + 1 if exclusive else minimum) if minimum is not None else 1)
        if data_type == "number":
            minimum, exclusive = self._numeric_limit(schema, "minimum")
            return float((minimum + 0.1 if exclusive else minimum) if minimum is not None else 1)
        if data_type == "boolean":
            return True
        if data_type == "array":
            item_schema = schema.get("items") if isinstance(schema.get("items"), dict) else {}
            size = max(1, self._safe_int(schema.get("minItems")) or 0)
            size = min(size, MAX_ARRAY_BOUNDARY)
            return [self._value_for_schema(item_schema) for _ in range(size)]
        if data_type == "object" or isinstance(schema.get("properties"), dict):
            properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
            return {
                str(name): self._value_for_schema(value if isinstance(value, dict) else {})
                for name, value in properties.items()
            }
        minimum_length = min(self._safe_int(schema.get("minLength")) or 0, MAX_STRING_BOUNDARY)
        return "x" * max(1, minimum_length)

    def _invalid_value(self, field: dict[str, Any]) -> Any:
        data_type = str(self._schema(field).get("type") or field.get("field_type") or field.get("type") or "string")
        values: dict[str, Any] = {
            "integer": "not-an-integer",
            "number": "not-a-number",
            "boolean": "not-a-boolean",
            "array": {"not": "an-array"},
            "object": ["not-an-object"],
            "string": 12345,
            "null": "not-null",
        }
        return deepcopy(values.get(data_type, {"unexpected": True}))

    def _invalid_enum_value(self, values: list[Any], field: dict[str, Any]) -> Any:
        data_type = str(self._schema(field).get("type") or field.get("field_type") or "string")
        candidates: list[Any] = [-999999, "__invalid_enum__", False, None]
        for candidate in candidates:
            if candidate not in values and (data_type not in {"integer", "number"} or self._is_number(candidate)):
                return candidate
        return "__invalid_enum_value__"

    def _boundary_value(self, field: dict[str, Any]) -> Any:
        variants = self._boundary_variants(field)
        return deepcopy(variants[-1][2]) if variants else self._invalid_value(field)

    def _schema(self, field: dict[str, Any]) -> dict[str, Any]:
        value = field.get("schema")
        return value if isinstance(value, dict) else field

    def _field_name(self, field: dict[str, Any]) -> str:
        data = self._data(field)
        return str(data.get("name") or field.get("name") or "")

    def _success_status(self, interface: dict[str, Any]) -> int:
        statuses = self._data(interface).get("expected_statuses")
        for value in statuses if isinstance(statuses, list) else []:
            text = str(value).strip().upper()
            if text.isdigit() and 200 <= int(text) < 400:
                return int(text)
        return 200

    def _status_class(self, value: str) -> int | None:
        if value.isdigit() and len(value) == 3:
            return int(value) // 100
        if len(value) == 3 and value[0].isdigit() and value[1:] == "XX":
            return int(value[0])
        return None

    def _numeric_limit(self, schema: dict[str, Any], name: str) -> tuple[float | int | None, bool]:
        exclusive_key = f"exclusive{name[0].upper()}{name[1:]}"
        exclusive_value = schema.get(exclusive_key)
        if self._is_number(exclusive_value):
            return exclusive_value, True
        value = schema.get(name)
        return (value, bool(exclusive_value)) if self._is_number(value) else (None, False)

    def _number_value(self, value: float | int, data_type: str) -> float | int:
        if data_type == "integer":
            return int(math.floor(value))
        return round(float(value), 10)

    def _is_number(self, value: Any) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    def _safe_int(self, value: Any) -> int | None:
        if isinstance(value, bool):
            return None
        try:
            result = int(value)
        except (TypeError, ValueError, OverflowError):
            return None
        return result if result >= 0 else None

    def _short_value(self, value: Any) -> str:
        text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        return text if len(text) <= 24 else f"{text[:21]}..."

    def _data(self, item: dict[str, Any]) -> dict[str, Any]:
        value = item.get("data")
        return value if isinstance(value, dict) else item
