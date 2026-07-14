from __future__ import annotations

import unittest
from typing import Any

from app.services.case_draft_service import CaseDraftService
from app.services.test_case_service import TestCaseService


class RecordingResourceRepository:
    """Repository double that records list pagination parameters."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def list(
        self,
        table: str,
        keyword: str | None = None,
        project_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
        data_filters: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        self.calls.append(
            {
                "table": table,
                "keyword": keyword,
                "project_id": project_id,
                "page": page,
                "page_size": page_size,
                "data_filters": data_filters,
            }
        )
        return [
            {
                "id": 21,
                "name": "case",
                "project_id": project_id,
                "source_id": None,
                "status": "active",
                "data": {"case_type": "WEB"},
                "strategy_ids": [],
            }
        ], 101

    def get(self, table: str, item_id: int) -> dict[str, Any] | None:
        del table, item_id
        return None

    def create(self, table: str, data: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def create_many(self, table: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        raise NotImplementedError

    def update(self, table: str, item_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        raise NotImplementedError

    def delete(self, table: str, item_id: int) -> bool:
        raise NotImplementedError

    def batch_delete(self, table: str, ids: list[int]) -> int:
        raise NotImplementedError

    def delete_by_project(self, table: str, project_id: int) -> int:
        raise NotImplementedError


class ListServicePaginationTest(unittest.TestCase):
    def test_test_case_list_uses_requested_page(self) -> None:
        repository = RecordingResourceRepository()
        service = TestCaseService("WEB", repository)

        rows, total = service.list("keyword", 7, page=3, page_size=15)

        self.assertEqual(total, 101)
        self.assertEqual(rows[0]["id"], 21)
        self.assertEqual(
            repository.calls[0],
            {
                "table": "web_test_cases",
                "keyword": "keyword",
                "project_id": 7,
                "page": 3,
                "page_size": 15,
                "data_filters": None,
            },
        )

    def test_case_draft_list_uses_requested_page_and_case_type_filter(self) -> None:
        repository = RecordingResourceRepository()
        service = CaseDraftService("WEB", repository)

        rows, total = service.list(7, "keyword", page=2, page_size=30)

        self.assertEqual(total, 101)
        self.assertEqual(rows[0]["id"], 21)
        self.assertEqual(
            repository.calls[0],
            {
                "table": "case_drafts",
                "keyword": "keyword",
                "project_id": 7,
                "page": 2,
                "page_size": 30,
                "data_filters": {"case_type": "WEB"},
            },
        )

    def test_case_draft_list_includes_status_filter_when_supplied(self) -> None:
        repository = RecordingResourceRepository()
        service = CaseDraftService("API", repository)

        rows, total = service.list(3, "login", page=1, page_size=20, status="draft")

        self.assertEqual(total, 101)
        self.assertEqual(rows[0]["id"], 21)
        self.assertEqual(
            repository.calls[0],
            {
                "table": "case_drafts",
                "keyword": "login",
                "project_id": 3,
                "page": 1,
                "page_size": 20,
                "data_filters": {"case_type": "API", "status": "draft"},
            },
        )


if __name__ == "__main__":
    unittest.main()
