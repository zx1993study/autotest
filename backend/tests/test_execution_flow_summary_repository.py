import unittest
from datetime import datetime
from unittest.mock import patch

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.models.resource_record import ResourceRecord
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.services.execution_flow_service import ExecutionFlowService


class ExecutionFlowSummaryRepositoryTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        ResourceRecord.__table__.create(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.repo = SqlAlchemyResourceRepository(self.db)
        self.statements = []
        event.listen(self.engine, "before_cursor_execute", self.record_statement)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def record_statement(self, connection, cursor, statement, parameters, context, executemany):
        self.statements.append(statement)

    def add_child(self, table, flow_id, status="active", day=15, deleted=False):
        row = ResourceRecord(
            table_name=table, name="metadata", project_id=10, status=status, deleted=deleted,
            updated_at=datetime(2026, 10, day),
            data_json={"data": {"flow_id": flow_id, "evidence": "x" * 100_000}},
        )
        self.db.add(row)
        self.db.flush()
        return row

    def test_counts_include_disabled_scenarios_but_exclude_deleted_rows(self):
        self.add_child("api_flow_scenarios", 1)
        self.add_child("api_flow_scenarios", "1", status="disabled")
        self.add_child("api_flow_scenarios", 1, deleted=True)
        self.add_child("api_flow_scenarios", 2)
        self.add_child("execution_records", 1)
        self.db.commit()
        self.assertEqual(self.repo.execution_flow_summaries([1, 3]), {
            1: {"scenario_count": 2, "latest_status": None},
            3: {"scenario_count": 0, "latest_status": None},
        })

    def test_latest_status_uses_updated_at_then_id_and_excludes_deleted(self):
        self.add_child("api_flow_runs", 1, status="failed")
        latest = self.add_child("api_flow_runs", "1", status="success")
        self.add_child("api_flow_runs", 1, status="cancelled", day=14)
        self.add_child("api_flow_runs", 1, status="running", deleted=True)
        self.add_child("api_flow_runs", 2, status="queued")
        self.db.commit()
        self.assertEqual(self.repo.execution_flow_summaries([1])[1]["latest_status"], "success")
        latest.updated_at = datetime(2026, 10, 13)
        self.db.commit()
        self.assertEqual(self.repo.execution_flow_summaries([1])[1]["latest_status"], "failed")

    def test_summary_selects_scalar_metadata_in_one_query_without_sorting(self):
        self.add_child("api_flow_runs", 1, status="success")
        self.add_child("api_flow_scenarios", 1)
        self.db.commit()
        self.statements.clear()
        self.repo.execution_flow_summaries([1])
        self.assertEqual(len(self.statements), 1)
        self.assertNotIn("ORDER BY", self.statements[0])
        self.assertNotIn("resource_records.data_json AS", self.statements[0])

    def test_empty_ids_issue_no_query(self):
        self.assertEqual(self.repo.execution_flow_summaries([]), {})
        self.assertEqual(self.statements, [])

    def test_twenty_flow_list_has_constant_query_count_and_correct_summaries(self):
        for index in range(20):
            flow = self.repo.create("execution_flows", {
                "name": f"Flow {index}", "project_id": 10, "data": {"nodes": []},
            })
            self.add_child("api_flow_scenarios", flow["id"])
            self.add_child("api_flow_runs", flow["id"], status="success")
        self.db.commit()
        self.statements.clear()
        with patch.object(self.repo, "list", wraps=self.repo.list) as list_resources:
            rows, total = ExecutionFlowService(self.repo).list(None, 10, 1, 20)
        self.assertEqual((len(rows), total), (20, 20))
        self.assertEqual(list_resources.call_count, 1)
        self.assertEqual(len(self.statements), 4)
        for row in rows:
            self.assertEqual(row["data"]["scenario_count"], 1)
            self.assertEqual(row["data"]["node_count"], 0)
            self.assertEqual(row["data"]["latest_status"], "通过")

    def test_empty_list_does_not_fetch_summaries(self):
        with patch.object(self.repo, "execution_flow_summaries") as summary:
            self.assertEqual(ExecutionFlowService(self.repo).list(None, 10, 1, 20), ([], 0))
        summary.assert_not_called()


if __name__ == "__main__":
    unittest.main()
