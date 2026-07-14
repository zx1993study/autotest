from __future__ import annotations

from typing import Any, Protocol


class ResourceRepository(Protocol):
    def list(
        self,
        table: str,
        keyword: str | None = None,
        project_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
        data_filters: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        ...

    def get(self, table: str, item_id: int) -> dict[str, Any] | None:
        ...

    def create(self, table: str, data: dict[str, Any]) -> dict[str, Any]:
        ...

    def create_many(self, table: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        ...

    def update(self, table: str, item_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        ...

    def delete(self, table: str, item_id: int) -> bool:
        ...

    def batch_delete(self, table: str, ids: list[int]) -> int:
        ...

    def delete_by_project(self, table: str, project_id: int) -> int:
        ...
