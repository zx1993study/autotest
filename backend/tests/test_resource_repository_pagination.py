import unittest
from datetime import datetime

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.models.resource_record import ResourceRecord
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository


class ResourceRepositoryPaginationTest(unittest.TestCase):
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

    def seed(self):
        rows = [
            ResourceRecord(
                table_name=table, name=f"batch-{index}", project_id=project_id,
                status=status, deleted=deleted, updated_at=datetime(2026, 10, day),
                data_json={"data": {"flow_id": flow_id, "evidence": "x" * 100_000}},
            )
            for index, (table, project_id, flow_id, status, deleted, day) in enumerate([
                ("api_flow_runs", 10, 1, "success", False, 14),
                ("api_flow_runs", 10, 1, "success", False, 15),
                ("api_flow_runs", 10, 1, "success", False, 15),
                ("api_flow_runs", 10, 1, "failed", False, 15),
                ("api_flow_runs", 20, 1, "success", False, 15),
                ("api_flow_runs", 10, 2, "success", False, 15),
                ("api_flow_runs", 10, 1, "success", True, 15),
                ("execution_flows", 10, 1, "success", False, 15),
            ])
        ]
        self.db.add_all(rows)
        self.db.commit()
        self.statements.clear()

    def list_page(self, page, page_size=2):
        return self.repo.list(
            "api_flow_runs", keyword="batch", project_id=10, page=page, page_size=page_size,
            data_filters={"flow_id": 1, "status": "success"},
        )

    def test_pagination_preserves_order_filters_and_full_payloads(self):
        self.seed()
        first, total = self.list_page(1)
        second, second_total = self.list_page(2)
        self.assertEqual((total, second_total), (3, 3))
        self.assertEqual([row["name"] for row in first], ["batch-2", "batch-1"])
        self.assertEqual([row["name"] for row in second], ["batch-0"])
        self.assertEqual(first[0]["data"]["evidence"], "x" * 100_000)

    def test_only_ids_participate_in_sorting(self):
        self.seed()
        self.list_page(1)
        self.assertEqual(len(self.statements), 3)
        ordered = [sql for sql in self.statements if "ORDER BY" in sql]
        self.assertEqual(len(ordered), 1)
        self.assertNotIn("data_json", ordered[0].partition("FROM")[0])
        self.assertIn("JOIN (SELECT DISTINCT resource_records.id", ordered[0])
        detail = self.statements[-1]
        self.assertIn("resource_records.data_json", detail.partition("FROM")[0])
        self.assertNotIn("ORDER BY", detail)
        self.assertIn("resource_records.id IN", detail)

    def test_empty_page_keeps_total_without_fetching_details(self):
        self.seed()
        self.assertEqual(self.list_page(5), ([], 3))
        self.assertEqual(len(self.statements), 2)
        self.assertFalse(any("data_json" in sql.partition("FROM")[0] for sql in self.statements))

    def test_no_matches_returns_empty_page(self):
        self.assertEqual(self.list_page(1), ([], 0))


if __name__ == "__main__":
    unittest.main()
