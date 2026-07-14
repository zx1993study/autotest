from __future__ import annotations

from app.core.exceptions import ResourceNotFoundError
from app.repositories.interfaces import ResourceRepository


class ResourceService:
    """Coordinate generic resource rules through a repository abstraction."""

    def __init__(self, table: str, repository: ResourceRepository) -> None:
        self.table = table
        self.repository = repository

    def list(
        self,
        keyword: str | None,
        project_id: int | None,
        page: int,
        page_size: int,
        data_filters: dict[str, object] | None = None,
    ) -> tuple[list[dict[str, object]], int]:
        return self.repository.list(self.table, keyword, project_id, page, page_size, data_filters)

    def get(self, item_id: int) -> dict[str, object]:
        item = self.repository.get(self.table, item_id)
        if not item:
            raise ResourceNotFoundError()
        return item

    def create(self, payload: dict[str, object]) -> dict[str, object]:
        payload.setdefault("data", {})
        payload.setdefault("status", "active")
        return self.repository.create(self.table, payload)

    def update(self, item_id: int, payload: dict[str, object]) -> dict[str, object]:
        item = self.repository.update(self.table, item_id, payload)
        if not item:
            raise ResourceNotFoundError()
        return item

    def delete(self, item_id: int) -> bool:
        if not self.repository.delete(self.table, item_id):
            raise ResourceNotFoundError()
        return True

    def batch_delete(self, ids: list[int]) -> dict[str, int]:
        return {"deleted_count": self.repository.batch_delete(self.table, ids)}

    def import_items(self, project_id: int, content: object) -> dict[str, int]:
        if isinstance(content, list):
            rows = content
        elif isinstance(content, dict):
            candidate = content.get("items", [])
            rows = candidate if isinstance(candidate, list) else []
        else:
            rows = []
        count = 0
        for row in rows:
            if not isinstance(row, dict):
                continue
            self.create(
                {
                    "name": str(row.get("name") or row.get("path") or f"导入数据 {count + 1}"),
                    "project_id": project_id,
                    "description": row.get("description") or row.get("summary"),
                    "data": row,
                }
            )
            count += 1
        return {"imported_count": count}
