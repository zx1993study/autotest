import unittest
from datetime import datetime

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.models.resource_record import ResourceRecord
from app.repositories.sqlalchemy_resource_repository import (
    TEST_CASE_RECORDS,
    SqlAlchemyResourceRepository,
)
from app.services.api_flow_run_service import ApiFlowRunService
from app.services.api_flow_scenario_service import ApiFlowScenarioService
from app.services.execution_flow_service import ExecutionFlowService
from app.services.test_case_service import TestCaseService


class ApiListIdOrderingTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        ResourceRecord.__table__.create(self.engine)
        for model, _ in TEST_CASE_RECORDS.values():
            model.__table__.create(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.repo = SqlAlchemyResourceRepository(self.db)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def seed_resources(self, table):
        rows = [self.repo.create(table, {
            "name": f"item-{index}", "project_id": 10, "status": "success",
            "data": {"flow_id": 8, "api_id": 9}, "source_id": 9, "case_type": "API",
        }) for index in range(4)]
        for index, row in enumerate(rows):
            record = self.db.get(ResourceRecord, row["id"])
            record.updated_at = datetime(2026, 10, 20 - index)
        self.db.commit()
        return [row["id"] for row in rows]

    def assert_pages(self, table, expected, filters=None):
        ids = []
        for page in (1, 2):
            rows, total = self.repo.list(table, keyword="item", project_id=10,
                                         page=page, page_size=2, data_filters=filters)
            self.assertEqual(total, 4)
            ids.extend(row["id"] for row in rows)
        self.assertEqual(ids, expected)

    def test_api_management_and_detail_lists_use_id_before_pagination(self):
        for table, filters in (
            ("execution_flows", None), ("api_flow_scenarios", {"flow_id": 8}),
            ("api_flow_runs", {"flow_id": 8}), ("api_interfaces", None),
            ("api_fields", {"api_id": 9}), ("case_drafts", {"source_id": 9}),
        ):
            with self.subTest(table=table):
                ids = self.seed_resources(table)
                for project, deleted in ((20, False), (10, True)):
                    excluded = self.repo.create(table, {
                        "name": "item-excluded", "project_id": project, "status": "success",
                        "data": {"flow_id": 8, "api_id": 9},
                        "source_id": 9, "case_type": "API",
                    })
                    if deleted:
                        self.repo.delete(table, excluded["id"])
                self.assert_pages(table, ids[::-1], filters)
                self.repo.update(table, ids[0], {"name": "item-updated"})
                self.assert_pages(table, ids[::-1], filters)

    def test_all_formal_case_domains_keep_id_order_after_editing(self):
        for table, (model, kind) in TEST_CASE_RECORDS.items():
            with self.subTest(table=table):
                for item_id, day in ((2, 20), (11, 19), (100, 18)):
                    self.db.add(model(id=item_id, name=f"item-{item_id}", project_id=10,
                                      source_id=9, updated_at=datetime(2026, 10, day)))
                self.db.add(model(id=101, name="other-source", project_id=10, source_id=99))
                self.db.add(model(id=102, name="other-project", project_id=20, source_id=9))
                self.db.add(model(id=103, name="deleted", project_id=10, source_id=9, deleted=True))
                self.db.commit()
                service = TestCaseService(kind, self.repo)
                for edited in (False, True):
                    if edited:
                        self.repo.update(table, 2, {"name": "item-updated"})
                    first, total = service.list(None, 10, 1, 2, source_id=9)
                    second, remaining = service.list(None, 10, 2, 2, source_id=9)
                    self.assertEqual((total, remaining), (3, 3))
                    self.assertEqual([row["id"] for row in first + second], [100, 11, 2])

    def test_flow_detail_scenes_and_history_preserve_repository_order(self):
        flow = self.repo.create("execution_flows", {"name": "Flow", "project_id": 10, "data": {"nodes": []}})
        expected = {}
        for table in ("api_flow_scenarios", "api_flow_runs"):
            ids = self.seed_resources(table)
            for item_id in ids:
                self.repo.update(table, item_id, {"data": {"flow_id": flow["id"], "results": []}})
            self.repo.update(table, ids[0], {"name": "updated older row"})
            expected[table] = ids[::-1]
        scenes = ApiFlowScenarioService(self.repo).list_for_flow(flow["id"])
        runs = ApiFlowRunService(self.repo).list_for_flow(flow["id"])
        self.assertEqual([row["id"] for row in scenes], expected["api_flow_scenarios"])
        self.assertEqual([row["id"] for row in runs], expected["api_flow_runs"])

    def test_flow_list_enrichment_does_not_reorder_rows(self):
        ids = self.seed_resources("execution_flows")
        self.repo.update("execution_flows", ids[0], {"name": "item-updated"})
        rows, total = ExecutionFlowService(self.repo).list(None, 10, 1, 20)
        self.assertEqual(total, 4)
        self.assertEqual([row["id"] for row in rows], ids[::-1])

    def test_ordered_query_still_sorts_ids_without_large_json(self):
        self.seed_resources("api_flow_runs")
        statements = []
        def record(connection, cursor, statement, parameters, context, executemany):
            statements.append(statement)
        event.listen(self.engine, "before_cursor_execute", record)
        self.repo.list("api_flow_runs", project_id=10, data_filters={"flow_id": 8})
        ordered = [sql for sql in statements if "ORDER BY" in sql]
        self.assertEqual(len(ordered), 1)
        self.assertIn("ORDER BY resource_records.id DESC", ordered[0])
        self.assertNotIn("updated_at DESC", ordered[0])
        self.assertNotIn("data_json", ordered[0].partition("FROM")[0])
        self.assertIn("JOIN (SELECT DISTINCT resource_records.id", ordered[0])


if __name__ == "__main__":
    unittest.main()
