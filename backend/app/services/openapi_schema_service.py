from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from app.core.exceptions import BusinessRuleError, ResourceNotFoundError
from app.repositories.interfaces import ResourceRepository


SCHEMA_SNAPSHOT_TABLE = "api_schema_snapshots"


class OpenApiSchemaService:
    """Persist immutable, content-addressed OpenAPI snapshots."""

    def __init__(self, repository: ResourceRepository) -> None:
        self.repository = repository

    def save_snapshot(
        self,
        project_id: int,
        content: dict[str, Any],
        *,
        source_type: str,
        source: str | None = None,
    ) -> dict[str, Any]:
        canonical = json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        schema_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        rows, _ = self.repository.list(SCHEMA_SNAPSHOT_TABLE, project_id=project_id, page_size=10000)
        existing = next(
            (row for row in rows if str(self._data(row).get("schema_hash") or "") == schema_hash),
            None,
        )
        if existing:
            return existing

        version = str(content.get("openapi") or content.get("swagger") or "unknown")
        paths = content.get("paths") if isinstance(content.get("paths"), dict) else {}
        return self.repository.create(
            SCHEMA_SNAPSHOT_TABLE,
            {
                "name": f"OpenAPI {version} - {schema_hash[:12]}",
                "project_id": project_id,
                "status": "active",
                "data": {
                    "schema": content,
                    "schema_hash": schema_hash,
                    "openapi_version": version,
                    "source_type": source_type,
                    "source": source or "",
                    "operation_count": self._operation_count(paths),
                    "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                },
            },
        )

    def latest(self, project_id: int) -> dict[str, Any]:
        interfaces, _ = self.repository.list("api_interfaces", project_id=project_id, page_size=1)
        if interfaces:
            interface_data = self._data(interfaces[0])
            snapshot_id = interface_data.get("schema_snapshot_id")
            try:
                current = self.repository.get(SCHEMA_SNAPSHOT_TABLE, int(snapshot_id))
            except (TypeError, ValueError):
                current = None
            if current and int(current.get("project_id") or 0) == project_id:
                return current

        rows, _ = self.repository.list(SCHEMA_SNAPSHOT_TABLE, project_id=project_id, page_size=1)
        if not rows:
            raise ResourceNotFoundError("项目尚未保存 OpenAPI Schema，请先重新导入")
        return rows[0]

    def get(self, snapshot_id: int) -> dict[str, Any]:
        snapshot = self.repository.get(SCHEMA_SNAPSHOT_TABLE, snapshot_id)
        if not snapshot:
            raise ResourceNotFoundError("OpenAPI Schema 快照不存在")
        return snapshot

    def get_for_project(self, project_id: int, snapshot_id: int | None = None) -> dict[str, Any]:
        snapshot = self.get(snapshot_id) if snapshot_id else self.latest(project_id)
        if int(snapshot.get("project_id") or 0) != project_id:
            raise BusinessRuleError("Schema 快照不属于当前项目")
        return snapshot

    def schema_document(self, snapshot_id: int) -> dict[str, Any]:
        schema = self._data(self.get(snapshot_id)).get("schema")
        if not isinstance(schema, dict):
            raise BusinessRuleError("OpenAPI Schema 快照内容无效")
        return deepcopy(schema)

    def _operation_count(self, paths: dict[str, Any]) -> int:
        methods = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}
        return sum(
            1
            for item in paths.values()
            if isinstance(item, dict)
            for method, operation in item.items()
            if str(method).lower() in methods and isinstance(operation, dict)
        )

    def _data(self, item: dict[str, Any]) -> dict[str, Any]:
        value = item.get("data")
        return value if isinstance(value, dict) else {}
