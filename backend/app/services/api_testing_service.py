from typing import Any
from urllib.parse import urlparse

from app.repositories.interfaces import ResourceRepository
from app.services.openapi_schema_service import OpenApiSchemaService
from app.services.resource_service import ResourceService
from app.utils.openapi_parser import OpenApiParser

UNGROUPED_MODULE_KEY = "__ungrouped__"
UNGROUPED_MODULE_LABEL = "未分组"
HTTP_METHOD_ORDER = ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE")


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
        source_type: str | None = None,
        source_name: str | None = None,
    ) -> dict[str, Any]:
        if isinstance(content, list):
            if overwrite:
                self._delete_project_api_data(project_id)
            imported_rows = []
            for row in content:
                if not isinstance(row, dict):
                    continue
                imported_rows.append(
                    self._normalize_interface_payload(
                        {
                            "name": str(row.get("name") or row.get("path") or f"导入数据 {len(imported_rows) + 1}"),
                            "project_id": project_id,
                            "description": row.get("description") or row.get("summary"),
                            "data": row,
                        }
                    )
                )
            if imported_rows:
                self.repository.create_many("api_interfaces", imported_rows)
            return {
                "project_id": project_id,
                "overwrite": overwrite,
                "interface_count": len(imported_rows),
                "field_count": 0,
                "interfaces": [],
            }
        parsed_endpoints = self.parser.parse(content)
        snapshot = OpenApiSchemaService(self.repository).save_snapshot(
            project_id,
            content,
            source_type=source_type or ("url" if source_url else "inline"),
            source=source_url or source_name,
        )
        snapshot_data = snapshot.get("data") if isinstance(snapshot.get("data"), dict) else {}
        api_base_path = self._api_base_path(content, source_url)
        if overwrite:
            self._delete_project_api_data(project_id)
        modules = self._ensure_modules(project_id, [parsed.get("module") for parsed in parsed_endpoints])
        interface_rows = [
            {
                "name": parsed["name"],
                "project_id": project_id,
                "description": parsed.get("description"),
                "data": {
                    "method": parsed["method"],
                    "path": parsed["path"],
                    "module": parsed.get("module"),
                    "module_id": modules[self._module_key(parsed.get("module"))]["id"],
                    "operation_id": parsed.get("operation_id"),
                    "content_type": parsed.get("content_type"),
                    "request_body_required": parsed.get("request_body_required", False),
                    "expected_statuses": parsed.get("expected_statuses", []),
                    "response_content_types": parsed.get("response_content_types", []),
                    "response_schemas": parsed.get("response_schemas", {}),
                    "security": parsed.get("security", []),
                    "deprecated": parsed.get("deprecated", False),
                    "tags": parsed.get("tags", []),
                    "api_base_path": api_base_path,
                    "schema_snapshot_id": snapshot["id"],
                    "schema_hash": snapshot_data.get("schema_hash"),
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
            "schema_snapshot_id": snapshot["id"],
            "schema_hash": snapshot_data.get("schema_hash"),
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

    def list_modules(
        self,
        project_id: int,
        keyword: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[dict[str, Any]], int]:
        rows, modules = self._synchronize_modules(project_id)
        summaries: dict[int, dict[str, Any]] = {}
        for module in modules.values():
            module_data = module.get("data") if isinstance(module.get("data"), dict) else {}
            module_key = str(module_data.get("module_key") or self._module_key(module.get("name")))
            summaries[int(module["id"])] = {
                "id": int(module["id"]),
                "key": module_key,
                "name": str(module.get("name") or UNGROUPED_MODULE_LABEL),
                "description": module.get("description"),
                "status": module.get("status") or "active",
                "interface_count": 0,
                "method_counts": {},
                "deprecated_count": 0,
                "disabled_count": 0,
                "updated_at": str(module.get("updated_at") or ""),
            }
        for item in rows:
            data = item.get("data") if isinstance(item.get("data"), dict) else {}
            module_id = self._to_int(data.get("module_id"))
            summary = summaries.get(module_id or 0)
            if not summary:
                continue
            summary["interface_count"] += 1
            method = str(data.get("method") or "OTHER").upper()
            method_counts = summary["method_counts"]
            method_counts[method] = int(method_counts.get(method, 0)) + 1
            if data.get("deprecated"):
                summary["deprecated_count"] += 1
            if str(item.get("status") or "") != "active":
                summary["disabled_count"] += 1
            updated_at = str(item.get("updated_at") or "")
            if updated_at > summary["updated_at"]:
                summary["updated_at"] = updated_at

        normalized_keyword = str(keyword or "").strip().casefold()
        result = [
            item
            for item in summaries.values()
            if not normalized_keyword or normalized_keyword in str(item["name"]).casefold()
        ]
        for item in result:
            counts = item["method_counts"]
            item["method_counts"] = {
                method: counts[method]
                for method in [*HTTP_METHOD_ORDER, *sorted(set(counts) - set(HTTP_METHOD_ORDER))]
                if method in counts
            }
        result.sort(
            key=lambda item: (
                item["key"] == UNGROUPED_MODULE_KEY,
                -int(item["interface_count"]),
                str(item["name"]).casefold(),
            )
        )
        total = len(result)
        start = (page - 1) * page_size
        return result[start : start + page_size], total

    def list_module_options(self, project_id: int) -> list[dict[str, Any]]:
        _, modules = self._synchronize_modules(project_id)
        result = [
            {
                "id": int(item["id"]),
                "project_id": item.get("project_id"),
                "name": item.get("name"),
                "key": (item.get("data") or {}).get("module_key"),
            }
            for item in modules.values()
        ]
        return sorted(result, key=lambda item: (item["key"] == UNGROUPED_MODULE_KEY, str(item["name"]).casefold()))

    def get_module(self, project_id: int, module_id: int) -> dict[str, Any]:
        _, modules = self._synchronize_modules(project_id)
        module = next((item for item in modules.values() if int(item["id"]) == module_id), None)
        if not module:
            raise ValueError("API 模块不存在或不属于当前项目")
        return module

    def create_interface(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.interfaces.create(self._normalize_interface_payload(payload))

    def update_interface(self, interface_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        current = self.repository.get("api_interfaces", interface_id)
        if not current:
            raise ValueError("API 接口不存在")
        merged = dict(payload)
        merged["project_id"] = payload.get("project_id", current.get("project_id"))
        if isinstance(payload.get("data"), dict):
            current_data = current.get("data") if isinstance(current.get("data"), dict) else {}
            merged["data"] = {**current_data, **payload["data"]}
        return self.interfaces.update(interface_id, self._normalize_interface_payload(merged))

    def _synchronize_modules(
        self,
        project_id: int,
    ) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
        rows, _ = self.repository.list("api_interfaces", project_id=project_id, page_size=10000)
        existing_modules, _ = self.repository.list("api_modules", project_id=project_id, page_size=10000)
        existing_module_ids = {int(item["id"]) for item in existing_modules}
        legacy_module_names = [
            self._interface_module_name(item)
            for item in rows
            if self._to_int((item.get("data") or {}).get("module_id")) not in existing_module_ids
        ]
        modules = self._ensure_modules(
            project_id,
            legacy_module_names,
        )
        modules_by_id = {int(item["id"]): item for item in modules.values()}
        pending_updates: list[tuple[int, dict[str, Any]]] = []
        for item in rows:
            data = item.get("data") if isinstance(item.get("data"), dict) else {}
            module = modules_by_id.get(self._to_int(data.get("module_id")) or 0)
            if module is None:
                module = modules[self._module_key(data.get("module"))]
            module_data = module.get("data") if isinstance(module.get("data"), dict) else {}
            module_key = str(module_data.get("module_key") or self._module_key(module.get("name")))
            module_name = "" if module_key == UNGROUPED_MODULE_KEY else str(module.get("name") or "")
            if (
                self._to_int(data.get("module_id")) != int(module["id"])
                or str(data.get("module") or "") != module_name
            ):
                pending_updates.append(
                    (
                        int(item["id"]),
                        {"data": {**data, "module_id": int(module["id"]), "module": module_name}},
                    )
                )
        if not pending_updates:
            return rows, modules
        updated_by_id = {
            int(item["id"]): item
            for item in self.repository.update_many("api_interfaces", pending_updates)
        }
        return [updated_by_id.get(int(item["id"]), item) for item in rows], modules

    def _ensure_modules(
        self,
        project_id: int,
        names: list[Any],
    ) -> dict[str, dict[str, Any]]:
        rows, _ = self.repository.list("api_modules", project_id=project_id, page_size=10000)
        modules = {
            str((item.get("data") or {}).get("module_key") or self._module_key(item.get("name"))): item
            for item in rows
        }
        required_keys = {self._module_key(name) for name in names}
        missing_keys = [
            module_key
            for module_key in sorted(required_keys, key=lambda value: value == UNGROUPED_MODULE_KEY)
            if module_key not in modules
        ]
        created_modules = self.repository.create_many(
            "api_modules",
            [
                {
                    "name": UNGROUPED_MODULE_LABEL if module_key == UNGROUPED_MODULE_KEY else module_key,
                    "project_id": project_id,
                    "status": "active",
                    "data": {
                        "module_key": module_key,
                        "is_ungrouped": module_key == UNGROUPED_MODULE_KEY,
                    },
                }
                for module_key in missing_keys
            ],
        )
        modules.update(zip(missing_keys, created_modules, strict=False))
        return modules

    def _normalize_interface_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(payload)
        project_id = self._to_int(normalized.get("project_id"))
        if project_id is None:
            raise ValueError("请选择接口所属项目")
        data = dict(normalized.get("data") or {})
        auth_id = self._to_int(data.get("auth_id"))
        if data.get("auth_id") not in (None, ""):
            auth = self.repository.get("project_auth", auth_id) if auth_id else None
            if not auth or int(auth.get("project_id") or 0) != project_id:
                raise ValueError("所选鉴权信息不属于当前项目，请重新选择")
            if str((auth.get("data") or {}).get("login_case_type") or "").upper() != "API":
                raise ValueError("请选择 API 类型的鉴权信息")
            data["auth_id"] = auth_id
        module_id = self._to_int(data.get("module_id"))
        if module_id is None:
            modules = self._ensure_modules(project_id, [data.get("module")])
            module = modules[self._module_key(data.get("module"))]
        else:
            module = self.repository.get("api_modules", module_id)
            if not module or int(module.get("project_id") or 0) != project_id:
                raise ValueError("所选 API 模块不属于当前项目")
        module_data = module.get("data") if isinstance(module.get("data"), dict) else {}
        module_key = str(module_data.get("module_key") or self._module_key(module.get("name")))
        data["module_id"] = int(module["id"])
        data["module"] = "" if module_key == UNGROUPED_MODULE_KEY else str(module.get("name") or "")
        normalized["data"] = data
        return normalized

    def _interface_module_name(self, item: dict[str, Any]) -> Any:
        data = item.get("data") if isinstance(item.get("data"), dict) else {}
        return data.get("module")

    def _module_key(self, value: Any) -> str:
        name = str(value).strip() if value is not None else ""
        return name or UNGROUPED_MODULE_KEY

    def _to_int(self, value: Any) -> int | None:
        try:
            result = int(value)
        except (TypeError, ValueError):
            return None
        return result if result > 0 else None

    def _delete_project_api_data(self, project_id: int) -> None:
        self.repository.delete_by_project("api_fields", project_id)
        self.repository.delete_by_project("api_interfaces", project_id)
        self.repository.delete_by_project("api_modules", project_id)

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
