from __future__ import annotations

import unittest
from datetime import datetime
from typing import Any

from app.models.resource_record import ResourceRecord
from app.models.test_case_record import (
    ApiTestCaseRecord,
    AppTestCaseRecord,
    MiniappTestCaseRecord,
    WebTestCaseRecord,
)
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.services.report_statistics_service import ReportStatisticsService
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


class FakeResourceRepository:
    """In-memory repository for testing report aggregation behavior."""

    def __init__(self, tables: dict[str, list[dict[str, Any]]]) -> None:
        self.tables = tables

    def report_statistics(self, project_id, start, end):
        models = {model.__tablename__: model for model in (
            ApiTestCaseRecord, WebTestCaseRecord, AppTestCaseRecord, MiniappTestCaseRecord,
        )}
        engine = create_engine("sqlite:///:memory:")
        for model in [ResourceRecord, *models.values()]:
            model.__table__.create(engine)
        with Session(engine) as db:
            for table, rows in self.tables.items():
                for row in rows:
                    values = {key: value for key, value in row.items() if key in {"id", "name", "project_id", "status", "description"}}
                    values.setdefault("name", "Case")
                    if row.get("updated_at"):
                        values["updated_at"] = datetime.fromisoformat(row["updated_at"])
                    model = models.get(table, ResourceRecord)
                    if model is ResourceRecord:
                        values.update(table_name=table, data_json={"data": row.get("data", {})})
                    db.add(model(**values))
            db.commit()
            result = SqlAlchemyResourceRepository(db).report_statistics(project_id, start, end)
        engine.dispose()
        return result


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
        self.assertEqual(overview["recent_records"][0]["case_type"], "WEB")


if __name__ == "__main__":
    unittest.main()
