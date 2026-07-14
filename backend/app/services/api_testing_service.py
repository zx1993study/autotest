from typing import Any
from urllib.parse import urlparse

from app.repositories.interfaces import ResourceRepository
from app.services.resource_service import ResourceService
from app.utils.openapi_parser import OpenApiParser


class ApiTestingService:
    def __init__(self, repository: ResourceRepository) -> None:
        self.repository = repository
        self.interfaces = ResourceService("api_interfaces", repository)
        self.fields = ResourceService("api_fields", repository)
        self.parser = OpenApiParser()

    def import_openapi(
        self,
        project_id: int,
        content: dict[str, Any] | list[dict[str, Any]],
        overwrite: bool = True,
        source_url: str | None = None,
    ) -> dict[str, Any]:
        if isinstance(content, list):
            if overwrite:
                self._delete_project_api_data(project_id)
            result = self.interfaces.import_items(project_id, content)
            return {
                "project_id": project_id,
                "overwrite": overwrite,
                "interface_count": result.get("imported_count", 0),
                "field_count": 0,
                "interfaces": [],
            }
        parsed_endpoints = self.parser.parse(content)
        api_base_path = self._api_base_path(content, source_url)
        if overwrite:
            self._delete_project_api_data(project_id)
        interface_rows = [
            {
                "name": parsed["name"],
                "project_id": project_id,
                "description": parsed.get("description"),
                "data": {
                    "method": parsed["method"],
                    "path": parsed["path"],
                    "module": parsed.get("module"),
                    "operation_id": parsed.get("operation_id"),
                    "content_type": parsed.get("content_type"),
                    "api_base_path": api_base_path,
                    "raw": parsed.get("raw"),
                },
            }
            for parsed in parsed_endpoints
        ]
        endpoints = self.repository.create_many("api_interfaces", interface_rows)
        field_rows = []
        detail = []
        for parsed, endpoint in zip(parsed_endpoints, endpoints, strict=False):
            endpoint_field_count = len(parsed["fields"])
            field_rows.extend(
                {
                    "name": field["name"],
                    "project_id": project_id,
                    "description": field.get("description"),
                    "data": {**field, "interface_id": endpoint["id"]},
                }
                for field in parsed["fields"]
            )
            detail.append(
                {
                    "id": endpoint["id"],
                    "method": parsed["method"],
                    "path": parsed["path"],
                    "name": parsed["name"],
                    "field_count": endpoint_field_count,
                }
            )
        if field_rows:
            self.repository.create_many("api_fields", field_rows)
        return {
            "project_id": project_id,
            "overwrite": overwrite,
            "interface_count": len(endpoints),
            "field_count": len(field_rows),
            "interfaces": detail,
        }

    def _api_base_path(self, content: dict[str, Any], source_url: str | None) -> str | None:
        servers = content.get("servers") if isinstance(content, dict) else None
        if isinstance(servers, list):
            for server in servers:
                if not isinstance(server, dict):
                    continue
                value = server.get("url")
                if not isinstance(value, str) or not value:
                    continue
                parsed = urlparse(value)
                path = parsed.path if parsed.scheme else value
                path = "/" + path.strip("/")
                return path if path != "/" else None
        if not source_url:
            return None
        parsed = urlparse(source_url)
        parent = parsed.path.rsplit("/", 1)[0].strip("/")
        return f"/{parent}" if parent else None

    def sync_fields(self, project_id: int, interface_ids: list[int]) -> dict[str, int]:
        interfaces, _ = self.repository.list("api_interfaces", project_id=project_id, page_size=10000)
        if interface_ids:
            interfaces = [item for item in interfaces if item["id"] in set(interface_ids)]
        count = 0
        for interface in interfaces:
            raw = interface.get("data", {}).get("raw", {})
            for field in self._extract_fields(interface["id"], raw):
                self.fields.create(
                    {
                        "name": field["name"],
                        "project_id": project_id,
                        "description": field.get("description"),
                        "data": field,
                    }
                )
                count += 1
        return {"field_count": count}

    def list_interface_options(self, project_id: int | None = None) -> list[dict[str, Any]]:
        rows, _ = self.repository.list("api_interfaces", project_id=project_id, page_size=10000)
        return [
            {
                "id": item["id"],
                "project_id": item.get("project_id"),
                "name": item["name"],
                "method": (item.get("data") or {}).get("method", ""),
                "path": (item.get("data") or {}).get("path", ""),
            }
            for item in rows
        ]

    def _delete_project_api_data(self, project_id: int) -> None:
        self.repository.delete_by_project("api_fields", project_id)
        self.repository.delete_by_project("api_interfaces", project_id)

    def _extract_fields(self, interface_id: int, operation: dict[str, Any]) -> list[dict[str, Any]]:
        fields = []
        for param in operation.get("parameters", []) or []:
            fields.append(
                {
                    "interface_id": interface_id,
                    "name": param.get("name", "param"),
                    "location": param.get("in", "query"),
                    "field_type": (param.get("schema") or {}).get("type", "string"),
                    "type": (param.get("schema") or {}).get("type", "string"),
                    "required": bool(param.get("required")),
                    "description": param.get("description"),
                    "example": param.get("example"),
                }
            )
        schema = (
            operation.get("requestBody", {})
            .get("content", {})
            .get("application/json", {})
            .get("schema", {})
        )
        required = set(schema.get("required", []))
        for name, prop in (schema.get("properties") or {}).items():
            fields.append(
                {
                    "interface_id": interface_id,
                    "name": name,
                    "location": "body",
                    "field_type": prop.get("type", "string"),
                    "type": prop.get("type", "string"),
                    "required": name in required,
                    "description": prop.get("description"),
                    "example": prop.get("example"),
                }
            )
        return fields
