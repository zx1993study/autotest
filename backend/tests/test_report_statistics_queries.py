import unittest
from datetime import datetime, timedelta

from app.models.resource_record import ResourceRecord
from app.models.test_case_record import (
    ApiTestCaseRecord,
    AppTestCaseRecord,
    MiniappTestCaseRecord,
    WebTestCaseRecord,
)
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.services.report_statistics_service import ReportStatisticsService
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session


class ReportStatisticsQueriesTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        for model in (ResourceRecord, ApiTestCaseRecord, WebTestCaseRecord, AppTestCaseRecord, MiniappTestCaseRecord):
            model.__table__.create(self.engine)
        self.db = Session(self.engine)
        self.repo = SqlAlchemyResourceRepository(self.db)
        self.service = ReportStatisticsService(self.repo)
        self.today = datetime.combine(datetime.now().date(), datetime.min.time())
        self.statements = []
        event.listen(self.engine, "before_cursor_execute", self.capture)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def capture(self, connection, cursor, statement, parameters, context, many):
        self.statements.append(statement)

    def record(self, key, *, days=0, status="success", project=1, deleted=False, **data):
        at = self.today - timedelta(days=days)
        self.db.add(ResourceRecord(id=key, table_name="execution_records", name=f"Record {key}",
                                   status=status, project_id=project, deleted=deleted, created_at=at,
                                   updated_at=at, data_json={"data": {"case_type": "API", **data}}))

    def test_counts_durations_trend_and_recent_records_preserve_scope(self):
        for key, value in enumerate([100, "200", None, "bad", -1, "1.5", 2.9, True, False], start=1):
            self.record(key, status="failed" if key == 2 else "success", duration_ms=value)
        self.record(10, days=8, status="error", duration_ms=10, error="Failure", evidence="x" * 100000)
        self.record(11, project=2, duration_ms=9999)
        self.record(12, deleted=True, duration_ms=9999)
        self.db.add_all([
            ApiTestCaseRecord(name="Active", project_id=1, status="active"),
            ApiTestCaseRecord(name="Inactive", project_id=1, status="disabled"),
            ApiTestCaseRecord(name="Deleted", project_id=1, deleted=True),
            ApiTestCaseRecord(name="Other project", project_id=2),
            WebTestCaseRecord(name="Web", project_id=1, status="active"),
        ])
        self.db.commit()
        self.statements.clear()
        result = self.service.overview(1)
        self.assertEqual(result["summary"]["case_total"], 3)
        self.assertEqual(result["summary"]["active_case_total"], 2)
        self.assertEqual(result["summary"]["execution_total"], 10)
        self.assertEqual(result["summary"]["abnormal_count"], 2)
        self.assertEqual(result["summary"]["avg_duration_ms"], 52)
        self.assertEqual(sum(row["total"] for row in result["trend"]), 9)
        self.assertEqual(sum(row["abnormal"] for row in result["trend"]), 1)
        self.assertEqual([row["id"] for row in result["recent_records"]], list(range(9, 1, -1)))
        self.assertEqual(len(self.statements), 8)
        self.assertFalse(any("resource_records.data_json AS" in sql for sql in self.statements))
        self.assertFalse(any("SELECT api_test_cases.id" in sql for sql in self.statements))
        self.assertEqual(self.service.overview(None)["summary"]["execution_total"], 11)

    def test_empty_statistics_are_zero_and_have_seven_days(self):
        result = self.service.overview(99)
        self.assertEqual(result["summary"]["execution_total"], 0)
        self.assertEqual(result["summary"]["avg_duration_ms"], 0)
        self.assertEqual(result["summary"]["pass_rate"], 0)
        self.assertEqual(len(result["trend"]), 7)
        self.assertEqual(result["recent_records"], [])


if __name__ == "__main__":
    unittest.main()
