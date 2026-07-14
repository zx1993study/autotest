from __future__ import annotations

import unittest
from typing import Any

from app.services.report_statistics_service import ReportStatisticsService


class FakeResourceRepository:
    """In-memory repository for testing report aggregation behavior."""

    def __init__(self, tables: dict[str, list[dict[str, Any]]]) -> None:
        self.tables = tables

    def list(
        self,
        table: str,
        keyword: str | None = None,
        project_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
        data_filters: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = [
            item
            for item in self.tables.get(table, [])
            if project_id is None or item.get("project_id") == project_id
        ]
        start = (page - 1) * page_size
        return rows[start : start + page_size], len(rows)


class ReportStatisticsServiceTest(unittest.TestCase):
    def test_overview_aggregates_cases_and_execution_records(self) -> None:
        repository = FakeResourceRepository(
            {
                "api_test_cases": [
                    {"id": 1, "project_id": 10, "status": "active"},
                    {"id": 2, "project_id": 10, "status": "inactive"},
                ],
                "web_test_cases": [{"id": 3, "project_id": 10, "status": "active"}],
                "app_test_cases": [],
                "miniapp_test_cases": [],
                "execution_records": [
                    {
                        "id": 7,
                        "name": "ok",
                        "project_id": 10,
                        "status": "success",
                        "data": {"case_type": "API", "duration_ms": 120},
                        "updated_at": "2026-07-14T10:00:00",
                    },
                    {
                        "id": 8,
                        "name": "bad",
                        "project_id": 10,
                        "status": "failed",
                        "description": "断言失败",
                        "data": {"case_type": "WEB", "duration_ms": 80, "error": "定位失败"},
                        "updated_at": "2026-07-14T10:01:00",
                    },
                    {
                        "id": 9,
                        "name": "other project",
                        "project_id": 11,
                        "status": "failed",
                        "data": {"case_type": "API"},
                    },
                ],
            }
        )
        service = ReportStatisticsService(repository)

        overview = service.overview(project_id=10)

        self.assertEqual(overview["summary"]["case_total"], 3)
        self.assertEqual(overview["summary"]["active_case_total"], 2)
        self.assertEqual(overview["summary"]["execution_total"], 2)
        self.assertEqual(overview["summary"]["success_count"], 1)
        self.assertEqual(overview["summary"]["abnormal_count"], 1)
        self.assertEqual(overview["summary"]["pass_rate"], 50.0)
        self.assertEqual(overview["summary"]["avg_duration_ms"], 100)
        self.assertEqual(overview["recent_records"][0]["case_type"], "API")


if __name__ == "__main__":
    unittest.main()
