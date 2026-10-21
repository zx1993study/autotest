import importlib
import unittest
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.exception_handlers import register_exception_handlers
from app.db.session import get_db
from app.models.execution_plan import ExecutionPlan
from app.models.resource_record import ResourceRecord
from app.repositories.sqlalchemy_execution_plan_repository import (
    SqlAlchemyExecutionPlanRepository,
)
from app.repositories.sqlalchemy_resource_repository import (
    TEST_CASE_RECORDS,
    SqlAlchemyResourceRepository,
)

BATCH_ROUTES = {
    "api_cases": "api_test_cases", "api_case_drafts": "case_drafts", "api_fields": "api_fields",
    "api_interfaces": "api_interfaces", "app_devices": "app_devices", "app_features": "app_features",
    "app_entries": "app_entries", "execution_flows": "execution_flows", "execution_plans": "execution_plans",
    "miniapp_cases": "miniapp_test_cases", "miniapp_case_drafts": "case_drafts", "miniapp_elements": "miniapp_elements",
    "miniapp_pages": "miniapp_pages", "project_auth": "project_auth", "project_knowledge": "project_knowledge",
    "project_info": "projects", "report_records": "execution_records", "system_dictionaries": "system_dictionaries",
    "system_model_configs": "ai_models", "system_operation_logs": "system_operation_logs",
    "web_cases": "web_test_cases", "system_users": "system_users", "web_pages": "web_pages", "web_case_drafts": "case_drafts",
}


@pytest.mark.parametrize(("module_name", "table"), BATCH_ROUTES.items())
def test_public_batch_delete_endpoint_contract(module_name, table):
    module = importlib.import_module(f"app.api.v1.{module_name}")
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    for model in (ResourceRecord, ExecutionPlan, *(row[0] for row in TEST_CASE_RECORDS.values())):
        model.__table__.create(engine)
    try:
        with Session(engine) as db:
            repo = SqlAlchemyResourceRepository(db)
            if table == "execution_plans":
                db.add_all([ExecutionPlan(id=key, name="Plan", test_type="API") for key in (1, 2)])
                db.commit()
                ids = [1, 2]
            else:
                ids = [repo.create(table, {"name": "Test", "data": {}})["id"] for _ in range(2)]
            app = FastAPI()
            register_exception_handlers(app)
            app.include_router(module.router, prefix="/api/v1")
            app.dependency_overrides[get_db] = lambda: db
            url = "/api/v1" + module.router.prefix + "/batch-delete"
            with TestClient(app) as client:
                response = client.post(url, json={"ids": [*ids, ids[0], 999999]})
                assert response.status_code == 200, response.text
                assert response.json()["data"] == {"deleted_count": 2}, module_name
                assert client.post(url, json={"ids": ids}).json()["data"] == {"deleted_count": 0}
                assert client.post(url, json={"ids": []}).status_code == 422
                assert client.post(url, json={"ids": list(range(501))}).status_code == 422
    finally:
        engine.dispose()


class BatchDeletionTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        for model in (ResourceRecord, ExecutionPlan, *(row[0] for row in TEST_CASE_RECORDS.values())):
            model.__table__.create(self.engine)
        self.db = Session(self.engine)
        self.repo = SqlAlchemyResourceRepository(self.db)
        self.statements = []
        event.listen(self.engine, "before_cursor_execute", self.capture)
        self.addCleanup(self.engine.dispose)
        self.addCleanup(self.db.close)

    def capture(self, connection, cursor, statement, parameters, context, many):
        self.statements.append(statement)

    def seed(self, table, count=1, **values):
        rows = [ResourceRecord(table_name=table, name=f"Item {index}", **values) for index in range(count)]
        self.db.add_all(rows)
        self.db.flush()
        ids = [row.id for row in rows]
        self.db.commit()
        self.statements.clear()
        return ids

    def test_500_resources_use_one_update_and_one_commit(self):
        ids = self.seed("execution_records", 500, data_json={"data": {"evidence": "x" * 10000}})
        other = self.seed("api_interfaces")[0]
        with patch.object(self.db, "commit", wraps=self.db.commit) as commit:
            self.assertEqual(self.repo.batch_delete("execution_records", ids + ids), 500)
        self.assertEqual(commit.call_count, 1)
        self.assertEqual(len(self.statements), 1)
        self.assertTrue(all(sql.startswith("UPDATE ") for sql in self.statements))
        self.assertEqual(self.repo.batch_delete("execution_records", [other, 99999]), 0)
        self.assertIsNotNone(self.repo.get("api_interfaces", other))
        self.statements.clear()
        self.assertEqual(self.repo.batch_delete("execution_records", ids), 0)
        self.assertEqual(len(self.statements), 1)
        self.statements.clear()
        self.assertEqual(self.repo.batch_delete("execution_records", []), 0)
        self.assertEqual(self.statements, [])

    def test_all_formal_case_tables_use_one_update_and_keep_history(self):
        history = self.seed("execution_records")[0]
        for table, (model, _) in TEST_CASE_RECORDS.items():
            with self.subTest(table=table):
                self.db.add_all([model(id=index, name="Case", data_json={}) for index in range(1, 501)])
                self.db.commit()
                self.statements.clear()
                with patch.object(self.db, "commit", wraps=self.db.commit) as commit:
                    self.assertEqual(self.repo.batch_delete(table, list(range(1, 501))), 500)
                self.assertEqual((len(self.statements), commit.call_count), (1, 1))
        self.assertIsNotNone(self.repo.get("execution_records", history))

    def test_execution_plans_use_one_update_and_preserve_other_rows(self):
        self.db.add_all([ExecutionPlan(id=index, name="Plan", test_type="API") for index in range(1, 502)])
        self.db.commit()
        self.statements.clear()
        repository = SqlAlchemyExecutionPlanRepository(self.db)
        with patch.object(self.db, "commit", wraps=self.db.commit) as commit:
            self.assertEqual(repository.batch_delete(list(range(1, 501))), 500)
        self.assertEqual((len(self.statements), commit.call_count), (1, 1))
        self.assertFalse(self.db.get(ExecutionPlan, 501).deleted)

    def test_chunk_failure_rolls_back_every_update(self):
        ids = self.seed("projects", 1001)

        def fail_second_update(connection, cursor, statement, parameters, context, many):
            if statement.startswith("UPDATE ") and len(self.statements) == 2:
                raise RuntimeError("simulated database failure")

        event.listen(self.engine, "before_cursor_execute", fail_second_update)
        try:
            with self.assertRaisesRegex(RuntimeError, "simulated database failure"):
                self.repo.batch_delete("projects", ids)
        finally:
            event.remove(self.engine, "before_cursor_execute", fail_second_update)
        self.assertEqual(self.db.query(ResourceRecord).filter(ResourceRecord.deleted.is_(True)).count(), 0)
        self.assertEqual(self.repo.batch_delete("projects", ids), 1001)

    def test_cascade_is_bounded_and_scoped_without_child_limit(self):
        first, second = self.seed("app_features", 2)
        foreign = self.seed("projects")[0]
        self.db.add_all([
            ResourceRecord(table_name="app_feature_scenarios", name="Scene", data_json={"data": {"feature_id": first}})
            for _ in range(10001)
        ])
        self.db.add_all([
            ResourceRecord(table_name="app_feature_scenarios", name="String ID", data_json={"data": {"feature_id": str(first)}}),
            ResourceRecord(table_name="app_feature_scenarios", name="Other", data_json={"data": {"feature_id": second}}),
            ResourceRecord(table_name="app_feature_scenarios", name="Foreign", data_json={"data": {"feature_id": foreign}}),
            ResourceRecord(table_name="app_feature_scenarios", name="Malformed", data_json={"data": {"feature_id": f"{first}x"}}),
            ResourceRecord(table_name="app_scenario_runs", name="History", data_json={"data": {"feature_id": first}}),
        ])
        self.db.commit()
        self.statements.clear()
        with patch.object(self.db, "commit", wraps=self.db.commit) as commit:
            count = self.repo.batch_delete_with_children("app_features", [first, first, foreign], "app_feature_scenarios", "feature_id")
        self.assertEqual((count, len(self.statements), commit.call_count), (1, 3, 1))
        rows, total = self.repo.list("app_feature_scenarios")
        self.assertEqual((total, {row["name"] for row in rows}), (3, {"Other", "Foreign", "Malformed"}))
        self.assertIsNotNone(self.repo.get("app_features", second))
        self.assertEqual(self.repo.list("app_scenario_runs")[1], 1)

    def test_cascade_failure_keeps_parent_and_children(self):
        parent = self.seed("app_features")[0]
        child = self.seed("app_feature_scenarios", data_json={"data": {"feature_id": parent}})[0]

        def fail_parent_update(connection, cursor, statement, parameters, context, many):
            if statement.startswith("UPDATE ") and len(self.statements) == 3:
                raise RuntimeError("simulated cascade failure")

        event.listen(self.engine, "before_cursor_execute", fail_parent_update)
        try:
            with self.assertRaises(RuntimeError):
                self.repo.batch_delete_with_children("app_features", [parent], "app_feature_scenarios", "feature_id")
        finally:
            event.remove(self.engine, "before_cursor_execute", fail_parent_update)
        self.assertIsNotNone(self.repo.get("app_features", parent))
        self.assertIsNotNone(self.repo.get("app_feature_scenarios", child))

    def test_related_lookup_filters_status_namespace_and_deleted_rows(self):
        self.seed("api_flow_runs", status="running", data_json={"data": {"flow_id": 10}})
        self.seed("api_flow_runs", status="success", data_json={"data": {"flow_id": 10}})
        self.seed("api_flow_runs", status="queued", data_json={"data": {"flow_id": "10"}})
        self.seed("api_flow_runs", status="running", deleted=True, data_json={"data": {"flow_id": 10}})
        self.seed("app_scenario_runs", status="running", data_json={"data": {"flow_id": 10}})
        rows = self.repo.get_related("api_flow_runs", "flow_id", [10, 10], ["running", "queued"])
        self.assertEqual((len(rows), len(self.statements)), (2, 1))
        self.assertEqual(self.repo.get_related("api_flow_runs", "flow_id", [], ["running"]), [])
