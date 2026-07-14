from __future__ import annotations

import unittest

from app.services.web_element_service import WebElementService


class FakeResourceRepository:
    """Minimal repository double for Web element list behavior."""

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.rows: dict[str, list[dict[str, object]]] = {
            "web_elements": [
                {"id": 1, "name": "name", "data": {"page_id": 10}},
                {"id": 2, "name": "type", "data": {"page_id": 10}},
                {"id": 3, "name": "save", "data": {"page_id": 10}},
            ],
            "web_pages": [
                {"id": 10, "name": "create warehouse", "data": {}},
            ],
        }

    def list(
        self,
        table: str,
        keyword: str | None = None,
        project_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
        data_filters: dict[str, object] | None = None,
    ) -> tuple[list[dict[str, object]], int]:
        del keyword, project_id
        self.calls.append({"table": table, "page": page, "page_size": page_size})
        rows = list(self.rows.get(table, []))
        for key, value in (data_filters or {}).items():
            rows = [row for row in rows if self._data(row).get(key) == value]
        start = (page - 1) * page_size
        return rows[start : start + page_size], len(rows)

    def get(self, table: str, item_id: int) -> dict[str, object] | None:
        return next((row for row in self.rows.get(table, []) if row.get("id") == item_id), None)

    def create(self, table: str, data: dict[str, object]) -> dict[str, object]:
        raise NotImplementedError

    def create_many(self, table: str, rows: list[dict[str, object]]) -> list[dict[str, object]]:
        raise NotImplementedError

    def update(self, table: str, item_id: int, data: dict[str, object]) -> dict[str, object] | None:
        raise NotImplementedError

    def delete(self, table: str, item_id: int) -> bool:
        raise NotImplementedError

    def batch_delete(self, table: str, ids: list[int]) -> int:
        raise NotImplementedError

    def delete_by_project(self, table: str, project_id: int) -> int:
        raise NotImplementedError

    def _data(self, row: dict[str, object]) -> dict[str, object]:
        value = row.get("data")
        return value if isinstance(value, dict) else {}


class WebElementServiceTest(unittest.TestCase):
    """Verify Web elements keep the UI-facing ordering and page context."""

    def test_list_uses_requested_page_and_adds_page_name(self) -> None:
        repository = FakeResourceRepository()
        service = WebElementService(repository)

        rows, total = service.list(None, None, page=1, page_size=2, data_filters={"page_id": 10})

        self.assertEqual(total, 3)
        self.assertEqual([row["id"] for row in rows], [1, 2])
        self.assertEqual(rows[0]["data"]["page_name"], "create warehouse")
        self.assertEqual(repository.calls[0], {"table": "web_elements", "page": 1, "page_size": 2})


if __name__ == "__main__":
    unittest.main()
