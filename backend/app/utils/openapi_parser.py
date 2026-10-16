from __future__ import annotations

from copy import deepcopy
from typing import Any


HTTP_METHODS = {"get", "post", "put", "delete", "patch", "head", "options", "trace"}
_MISSING = object()


class OpenApiParser:
    def parse(self, content: dict[str, Any]) -> list[dict[str, Any]]:
        if not isinstance(content, dict):
            raise ValueError("OpenAPI 内容必须是对象")
        paths = content.get("paths")
        if not isinstance(paths, dict):
            raise ValueError("OpenAPI 内容缺少 paths 节点")

        endpoints: list[dict[str, Any]] = []
        for path, path_item in paths.items():
            path_item = self._resolve_ref(path_item, content)
            if not isinstance(path_item, dict):
                continue
            common_parameters = self._parameters(path_item.get("parameters"), content)
            for method, operation in path_item.items():
                method_lower = method.lower()
                if method_lower not in HTTP_METHODS or not isinstance(operation, dict):
                    continue
                operation = self._resolve_ref(operation, content)
                operation_parameters = self._parameters(operation.get("parameters"), content)
                parameters = self._merge_parameters(common_parameters, operation_parameters)
                request_fields = self._request_body_fields(operation, content)
                response_metadata = self._response_metadata(operation, content)
                endpoints.append(
                    {
                        "name": operation.get("summary") or operation.get("operationId") or f"{method_upper(method)} {path}",
                        "description": operation.get("description"),
                        "method": method_upper(method),
                        "path": path,
                        "module": self._module(operation),
                        "tags": operation.get("tags") if isinstance(operation.get("tags"), list) else [],
                        "operation_id": operation.get("operationId"),
                        "content_type": self._content_type(operation, content),
                        "request_body_required": self._request_body_required(operation, content),
                        "security": operation.get("security", content.get("security", [])),
                        "deprecated": bool(operation.get("deprecated")),
                        **response_metadata,
                        "raw": operation,
                        "fields": parameters + request_fields,
                    }
                )
        return endpoints

    def _parameters(self, value: Any, document: dict[str, Any]) -> list[dict[str, Any]]:
        fields: list[dict[str, Any]] = []
        if not isinstance(value, list):
            return fields
        for item in value:
            parameter = self._resolve_ref(item, document)
            if not isinstance(parameter, dict):
                continue
            schema = self._normalize_schema(parameter.get("schema") or {}, document)
            fields.append(
                {
                    "name": str(parameter.get("name") or "param"),
                    "location": parameter.get("in") or "query",
                    "field_type": self._schema_type(schema),
                    "type": self._schema_type(schema),
                    "required": bool(parameter.get("required")),
                    "description": parameter.get("description"),
                    "example": self._parameter_example(parameter, schema),
                    "example_provided": "example" in parameter or "example" in schema,
                    "default_value": schema.get("default"),
                    "enum": schema.get("enum"),
                    "schema": schema,
                }
            )
        return fields

    def _request_body_fields(self, operation: dict[str, Any], document: dict[str, Any]) -> list[dict[str, Any]]:
        request_body = self._resolve_ref(operation.get("requestBody") or {}, document)
        content = request_body.get("content") or {}
        media_type, media_value = self._pick_media_type(content)
        schema = self._normalize_schema((media_value or {}).get("schema") or {}, document)
        body_example = self._media_example(media_value)
        required = set(schema.get("required") or [])
        if schema.get("type") == "array":
            item_schema = self._normalize_schema(schema.get("items") or {}, document)
            return [
                {
                    "name": "body",
                    "location": "body",
                    "field_type": "array",
                    "type": "array",
                    "required": bool(request_body.get("required")),
                    "description": request_body.get("description"),
                    "example": deepcopy(body_example) if body_example is not _MISSING else self._example_from_schema(schema),
                    "example_provided": body_example is not _MISSING or "example" in schema,
                    "content_type": media_type,
                    "schema": schema,
                    "item_schema": item_schema,
                }
            ]

        properties = schema.get("properties") or {}
        fields = []
        if isinstance(properties, dict) and properties:
            for name, prop in properties.items():
                field_schema = self._normalize_schema(prop, document)
                has_property_example = isinstance(body_example, dict) and name in body_example
                fields.append(
                    {
                        "name": name,
                        "location": "body",
                        "field_type": self._schema_type(field_schema),
                        "type": self._schema_type(field_schema),
                        "required": name in required,
                        "description": field_schema.get("description"),
                        "example": deepcopy(body_example[name]) if has_property_example else self._schema_example(field_schema),
                        "example_provided": has_property_example or "example" in field_schema,
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
                    "field_type": self._schema_type(schema),
                    "type": self._schema_type(schema),
                    "required": bool(request_body.get("required")),
                    "description": request_body.get("description"),
                    "example": deepcopy(body_example) if body_example is not _MISSING else self._example_from_schema(schema),
                    "example_provided": body_example is not _MISSING or "example" in schema,
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

    def _content_type(self, operation: dict[str, Any], document: dict[str, Any]) -> str | None:
        request_body = self._resolve_ref(operation.get("requestBody") or {}, document)
        content = request_body.get("content") or {}
        media_type, _ = self._pick_media_type(content)
        return media_type

    def _request_body_required(self, operation: dict[str, Any], document: dict[str, Any]) -> bool:
        request_body = self._resolve_ref(operation.get("requestBody") or {}, document)
        return bool(request_body.get("required")) if isinstance(request_body, dict) else False

    def _response_metadata(self, operation: dict[str, Any], document: dict[str, Any]) -> dict[str, Any]:
        responses = operation.get("responses") if isinstance(operation.get("responses"), dict) else {}
        statuses: list[str] = []
        content_types: list[str] = []
        schemas: dict[str, dict[str, Any]] = {}
        for status, raw_response in responses.items():
            status_text = str(status).upper()
            statuses.append(status_text)
            response = self._resolve_ref(raw_response, document)
            if not isinstance(response, dict):
                continue
            response_content = response.get("content") if isinstance(response.get("content"), dict) else {}
            status_schemas: dict[str, Any] = {}
            for media_type, media in response_content.items():
                if not isinstance(media, dict):
                    continue
                content_types.append(str(media_type))
                status_schemas[str(media_type)] = self._normalize_schema(media.get("schema") or {}, document)
            if status_schemas:
                schemas[status_text] = status_schemas
        return {
            "expected_statuses": statuses,
            "response_content_types": list(dict.fromkeys(content_types)),
            "response_schemas": schemas,
        }

    def _resolve_ref(self, value: Any, document: dict[str, Any], seen: set[str] | None = None) -> Any:
        if not isinstance(value, dict) or "$ref" not in value:
            return value
        ref = value["$ref"]
        if not isinstance(ref, str) or not ref.startswith("#/"):
            return value
        visited = set(seen or ())
        if ref in visited:
            return value
        visited.add(ref)
        current: Any = document
        for part in ref.lstrip("#/").split("/"):
            if not isinstance(current, dict):
                return value
            current = current.get(part.replace("~1", "/").replace("~0", "~"))
        if current is None:
            return value
        resolved = self._resolve_ref(current, document, visited)
        if not isinstance(resolved, dict):
            return resolved
        siblings = {key: item for key, item in value.items() if key != "$ref"}
        return {**deepcopy(resolved), **siblings}

    def _normalize_schema(
        self,
        value: Any,
        document: dict[str, Any],
        seen_refs: set[str] | None = None,
    ) -> dict[str, Any]:
        if not isinstance(value, dict):
            return {}
        visited = set(seen_refs or ())
        ref = value.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/"):
            if ref in visited:
                return {"$ref": ref}
            visited.add(ref)
        resolved = self._resolve_ref(value, document, visited - ({ref} if isinstance(ref, str) else set()))
        if not isinstance(resolved, dict):
            return {}
        schema = deepcopy(resolved)

        all_of = schema.pop("allOf", None)
        if isinstance(all_of, list):
            for part in all_of:
                schema = self._merge_schema(schema, self._normalize_schema(part, document, visited))
        for keyword in ("oneOf", "anyOf"):
            alternatives = schema.get(keyword)
            if isinstance(alternatives, list) and alternatives:
                schema = self._merge_schema(
                    {key: item for key, item in schema.items() if key != keyword},
                    self._normalize_schema(alternatives[0], document, visited),
                )
                break

        properties = schema.get("properties")
        if isinstance(properties, dict):
            schema["properties"] = {
                str(name): self._normalize_schema(item, document, visited)
                for name, item in properties.items()
            }
        if isinstance(schema.get("items"), dict):
            schema["items"] = self._normalize_schema(schema["items"], document, visited)

        type_value = schema.get("type")
        if isinstance(type_value, list):
            types = [str(item) for item in type_value]
            schema["nullable"] = "null" in types
            schema["type"] = next((item for item in types if item != "null"), "null")
        return schema

    def _merge_schema(self, base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
        merged = {**base, **extra}
        base_properties = base.get("properties") if isinstance(base.get("properties"), dict) else {}
        extra_properties = extra.get("properties") if isinstance(extra.get("properties"), dict) else {}
        if base_properties or extra_properties:
            merged["properties"] = {**base_properties, **extra_properties}
        base_required = base.get("required") if isinstance(base.get("required"), list) else []
        extra_required = extra.get("required") if isinstance(extra.get("required"), list) else []
        required = [
            str(item)
            for item in [*base_required, *extra_required]
        ]
        if required:
            merged["required"] = list(dict.fromkeys(required))
        return merged

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

    def _schema_type(self, schema: dict[str, Any]) -> str:
        value = schema.get("type")
        if isinstance(value, str) and value:
            return value
        return self._infer_type(schema)

    def _media_example(self, media: dict[str, Any] | None) -> Any:
        if not isinstance(media, dict):
            return _MISSING
        if "example" in media:
            return media["example"]
        examples = media.get("examples")
        if isinstance(examples, dict):
            for item in examples.values():
                if isinstance(item, dict) and "value" in item:
                    return item["value"]
        return _MISSING

    def _parameter_example(self, parameter: dict[str, Any], schema: dict[str, Any]) -> Any:
        if "example" in parameter:
            return parameter["example"]
        return self._schema_example(schema)

    def _schema_example(self, schema: dict[str, Any]) -> Any:
        if "example" in schema:
            return schema["example"]
        return self._example_from_schema(schema)

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
