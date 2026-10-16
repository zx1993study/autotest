from __future__ import annotations

from typing import Any

from app.core.exceptions import BusinessRuleError, ResourceNotFoundError
from app.repositories.interfaces import ResourceRepository


class ProjectService:
    """Project-specific business rules beyond generic CRUD."""

    def __init__(self, repository: ResourceRepository) -> None:
        self.repository = repository

    def list_options(self) -> list[dict[str, Any]]:
        rows, _ = self.repository.list("projects", None, None, 1, 200)
        options = [
            {
                "id": item["id"],
                "name": item["name"],
                "base_url": self._project_url(item),
                "is_default": self._is_default(item),
            }
            for item in rows
        ]
        return sorted(options, key=lambda item: not item["is_default"])

    def set_default(self, project_id: int) -> dict[str, Any]:
        """Mark one active project as the global default project."""

        target = self.repository.get("projects", project_id)
        if not target:
            raise ResourceNotFoundError("项目不存在")
        if str(target.get("status") or "") != "active":
            raise BusinessRuleError("停用项目不能设置为默认项目")

        rows, _ = self.repository.list("projects", None, None, 1, 10_000)
        updated_target: dict[str, Any] | None = None
        for row in rows:
            row_id = int(row["id"])
            data = self._data(row)
            next_data = {**data, "is_default": row_id == project_id}
            updated = self.repository.update("projects", row_id, {"data": next_data})
            if row_id == project_id:
                updated_target = updated
        if updated_target is None:
            raise ResourceNotFoundError("项目不存在")
        return updated_target

    def _project_url(self, item: dict[str, Any]) -> str:
        data = self._data(item)
        value = data.get("base_url") or data.get("project_url") or data.get("url") or ""
        return str(value)

    def _is_default(self, item: dict[str, Any]) -> bool:
        return self._data(item).get("is_default") is True

    def _data(self, item: dict[str, Any]) -> dict[str, Any]:
        data = item.get("data")
        return data if isinstance(data, dict) else {}
