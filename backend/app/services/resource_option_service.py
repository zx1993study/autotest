from __future__ import annotations

from typing import Any

from app.repositories.interfaces import ResourceRepository


class ResourceOptionService:
    """Build lightweight option rows for generic resource selectors."""

    def __init__(self, table: str, repository: ResourceRepository) -> None:
        self.table = table
        self.repository = repository

    def list_options(
        self,
        project_id: int | None = None,
        *,
        page_size: int = 5000,
    ) -> list[dict[str, Any]]:
        rows, _ = self.repository.list(self.table, project_id=project_id, page=1, page_size=page_size)
        return [self._option(row) for row in rows]

    def _option(self, row: dict[str, Any]) -> dict[str, Any]:
        data = row.get("data") if isinstance(row.get("data"), dict) else {}
        return {
            "id": row.get("id"),
            "name": row.get("name"),
            "project_id": row.get("project_id"),
            "status": row.get("status"),
            "data": data,
            **{key: value for key, value in data.items() if key not in {"id", "name", "project_id", "status"}},
        }
