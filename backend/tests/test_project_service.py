from __future__ import annotations

import unittest

from app.core.exceptions import BusinessRuleError
from app.services.project_service import ProjectService


class FakeResourceRepository:
    """In-memory repository for project service behavior tests."""

    def __init__(self) -> None:
        self.rows: dict[int, dict[str, object]] = {}
        self.next_id = 1

    def list(
        self,
        table: str,
        keyword: str | None = None,
        project_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
        data_filters: dict[str, object] | None = None,
    ) -> tuple[list[dict[str, object]], int]:
        del keyword, project_id, data_filters
        rows = [row for row in self.rows.values() if row.get("table") == table]
        start = (page - 1) * page_size
        return rows[start : start + page_size], len(rows)

    def get(self, table: str, item_id: int) -> dict[str, object] | None:
        row = self.rows.get(item_id)
        return row if row and row.get("table") == table else None

    def create(self, table: str, data: dict[str, object]) -> dict[str, object]:
        item = {
            "id": self.next_id,
            "table": table,
            "name": data.get("name") or "Untitled",
            "status": data.get("status", "active"),
            "data": data.get("data", {}),
        }
        self.rows[self.next_id] = item
        self.next_id += 1
        return item

    def create_many(self, table: str, rows: list[dict[str, object]]) -> list[dict[str, object]]:
        return [self.create(table, row) for row in rows]

    def update(self, table: str, item_id: int, data: dict[str, object]) -> dict[str, object] | None:
        row = self.get(table, item_id)
        if row is None:
            return None
        row.update(data)
        return row

    def delete(self, table: str, item_id: int) -> bool:
        if self.get(table, item_id) is None:
            return False
        self.rows.pop(item_id)
        return True

    def batch_delete(self, table: str, ids: list[int]) -> int:
        return sum(1 for item_id in set(ids) if self.delete(table, item_id))

    def delete_by_project(self, table: str, project_id: int) -> int:
        del table, project_id
        return 0


class ProjectServiceTest(unittest.TestCase):
    def test_set_default_keeps_only_one_default_project(self) -> None:
        repository = FakeResourceRepository()
        first = repository.create("projects", {"name": "项目一", "status": "active", "data": {}})
        second = repository.create("projects", {"name": "项目二", "status": "active", "data": {}})
        service = ProjectService(repository)

        updated = service.set_default(int(second["id"]))
        options = service.list_options()

        self.assertTrue(isinstance(updated["data"], dict) and updated["data"]["is_default"])
        self.assertEqual(options[0]["id"], second["id"])
        self.assertTrue(options[0]["is_default"])
        self.assertFalse(isinstance(first["data"], dict) and bool(first["data"].get("is_default")))

    def test_disabled_project_cannot_be_default(self) -> None:
        repository = FakeResourceRepository()
        project = repository.create("projects", {"name": "停用项目", "status": "disabled", "data": {}})
        service = ProjectService(repository)

        with self.assertRaises(BusinessRuleError):
            service.set_default(int(project["id"]))


if __name__ == "__main__":
    unittest.main()
