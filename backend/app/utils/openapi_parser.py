from __future__ import annotations

from typing import Any


HTTP_METHODS = {"get", "post", "put", "delete", "patch", "head", "options", "trace"}


class OpenApiParser:
    def parse(self, content: dict[str, Any]) -> list[dict[str, Any]]:
        if not isinstance(content, dict):
            raise ValueError("OpenAPI 内容必须是 JSON 对象")
        paths = content.get("paths")
        if not isinstance(paths, dict):
            raise ValueError("OpenAPI 内容缺少 paths 节点")

        components = content.get("components") or {}
        endpoints: list[dict[str, Any]] = []
        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue
            common_parameters = self._parameters(path_item.get("parameters"), components)
            for method, operation in path_item.items():
                method_lower = method.lower()
                if method_lower not in HTTP_METHODS or not isinstance(operation, dict):
                    continue
                operation_parameters = self._parameters(operation.get("parameters"), components)
                parameters = self._merge_parameters(common_parameters, operation_parameters)
                request_fields = self._request_body_fields(operation, components)
                endpoints.append(
                    {
                        "name": operation.get("summary") or operation.get("operationId") or f"{method_upper(method)} {path}",
                        "description": operation.get("description"),
                        "method": method_upper(method),
                        "path": path,
                        "module": self._module(operation),
                        "operation_id": operation.get("operationId"),
                        "content_type": self._content_type(operation, components),
                        "raw": operation,
                        "fields": parameters + request_fields,
                    }
                )
        return endpoints

    def _parameters(self, value: Any, components: dict[str, Any]) -> list[dict[str, Any]]:
        fields: list[dict[str, Any]] = []
        if not isinstance(value, list):
            return fields
        for item in value:
            parameter = self._resolve_ref(item, components)
            if not isinstance(parameter, dict):
                continue
            schema = self._resolve_ref(parameter.get("schema") or {}, components)
            fields.append(
                {
                    "name": str(parameter.get("name") or "param"),
                    "location": parameter.get("in") or "query",
                    "field_type": schema.get("type") or self._infer_type(schema),
                    "type": schema.get("type") or self._infer_type(schema),
                    "required": bool(parameter.get("required")),
                    "description": parameter.get("description"),
                    "example": parameter.get("example") or schema.get("example") or self._example_from_schema(schema),
                    "default_value": schema.get("default"),
                    "enum": schema.get("enum"),
                    "schema": schema,
                }
            )
        return fields

    def _request_body_fields(self, operation: dict[str, Any], components: dict[str, Any]) -> list[dict[str, Any]]:
        request_body = self._resolve_ref(operation.get("requestBody") or {}, components)
        content = request_body.get("content") or {}
        media_type, media_value = self._pick_media_type(content)
        schema = self._resolve_ref((media_value or {}).get("schema") or {}, components)
        required = set(schema.get("required") or [])
        if schema.get("type") == "array":
            item_schema = self._resolve_ref(schema.get("items") or {}, components)
            return [
                {
                    "name": "body",
                    "location": "body",
                    "field_type": "array",
                    "type": "array",
                    "required": bool(request_body.get("required")),
                    "description": request_body.get("description"),
                    "example": self._example_from_schema(schema),
                    "content_type": media_type,
                    "schema": schema,
                    "item_schema": item_schema,
                }
            ]

        properties = schema.get("properties") or {}
        fields = []
        if isinstance(properties, dict) and properties:
            for name, prop in properties.items():
                field_schema = self._resolve_ref(prop, components)
                fields.append(
                    {
                        "name": name,
                        "location": "body",
                        "field_type": field_schema.get("type") or self._infer_type(field_schema),
                        "type": field_schema.get("type") or self._infer_type(field_schema),
                        "required": name in required,
                        "description": field_schema.get("description"),
                        "example": field_schema.get("example") or self._example_from_schema(field_schema),
                        "default_value": field_schema.get("default"),
                        "enum": field_schema.get("enum"),
                        "content_type": media_type,
                        "schema": field_schema,
                    }
                )
        elif schema:
            fields.append(
                {
                    "name": "body",
                    "location": "body",
                    "field_type": schema.get("type") or self._infer_type(schema),
                    "type": schema.get("type") or self._infer_type(schema),
                    "required": bool(request_body.get("required")),
                    "description": request_body.get("description"),
                    "example": self._example_from_schema(schema),
                    "content_type": media_type,
                    "schema": schema,
                }
            )
        return fields

    def _pick_media_type(self, content: dict[str, Any]) -> tuple[str | None, dict[str, Any] | None]:
        if not isinstance(content, dict) or not content:
            return None, None
        for candidate in ("application/json", "multipart/form-data", "application/x-www-form-urlencoded"):
            if candidate in content:
                return candidate, content[candidate]
        media_type = next(iter(content))
        return media_type, content[media_type]

    def _content_type(self, operation: dict[str, Any], components: dict[str, Any]) -> str | None:
        request_body = self._resolve_ref(operation.get("requestBody") or {}, components)
        content = request_body.get("content") or {}
        media_type, _ = self._pick_media_type(content)
        return media_type

    def _resolve_ref(self, value: Any, components: dict[str, Any]) -> Any:
        if not isinstance(value, dict) or "$ref" not in value:
            return value
        ref = value["$ref"]
        if not isinstance(ref, str) or not ref.startswith("#/components/"):
            return value
        current: Any = {"components": components}
        for part in ref.lstrip("#/").split("/"):
            if not isinstance(current, dict):
                return value
            current = current.get(part)
        return current if current is not None else value

    def _merge_parameters(
        self,
        common_parameters: list[dict[str, Any]],
        operation_parameters: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        merged: dict[tuple[str, str], dict[str, Any]] = {}
        for item in common_parameters + operation_parameters:
            merged[(str(item.get("location")), str(item.get("name")))] = item
        return list(merged.values())

    def _module(self, operation: dict[str, Any]) -> str | None:
        tags = operation.get("tags")
        if isinstance(tags, list) and tags:
            return str(tags[0])
        return None

    def _infer_type(self, schema: dict[str, Any]) -> str:
        if "properties" in schema:
            return "object"
        if "items" in schema:
            return "array"
        if "enum" in schema:
            return "string"
        return "string"

    def _example_from_schema(self, schema: dict[str, Any]) -> Any:
        if "example" in schema:
            return schema["example"]
        if "default" in schema:
            return schema["default"]
        values = schema.get("enum")
        if isinstance(values, list) and values:
            return values[0]
        data_type = schema.get("type")
        if data_type in {"integer", "number"}:
            return 1
        if data_type == "boolean":
            return True
        if data_type == "array":
            return []
        if data_type == "object" or "properties" in schema:
            return {}
        return "test"


def method_upper(method: str) -> str:
    return method.upper()
