from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_resource_repository
from app.api.v1.api_cases import router
from app.db.base import Base
from app.models.resource_record import ResourceRecord
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.scheduler.jobs.api_case_executor import ApiCaseExecutor
from app.services.test_case_service import TestCaseService
from app.utils.api_response import extract_response_code


class ApiCaseManagementTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)()
        self.repository = SqlAlchemyResourceRepository(self.session)
        self.service = TestCaseService("API", self.repository)
        self.case = self.service.create({"name": "缺失字段", "project_id": 1, "source_id": 30})
        self.other = self.service.create({"name": "未执行", "project_id": 1, "source_id": 30})
        self.now = datetime(2026, 10, 14, 12, 0)

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def record(self, *, case_id=None, status="success", project_id=1, case_type="API", at=None, deleted=False, **data):
        row = ResourceRecord(table_name="execution_records", name="测试执行", status=status, project_id=project_id,
            data_json={"data": {"case_id": case_id or self.case["id"], "case_type": case_type, **data}},
            created_at=at or self.now, updated_at=self.now, deleted=deleted)
        self.session.add(row)
        self.session.commit()
        return row

    def summaries(self, project_id=1):
        rows, _ = self.service.list(None, project_id, 1, 20, source_id=30, include_latest_execution=True)
        return {row["id"]: row["latest_execution"] for row in rows}

    def test_latest_is_by_execution_creation_time_then_id_not_last_edit(self):
        newest = self.record(status="failed", response_body='{"code": 4001}', response_status=200)
        old = self.record(at=self.now - timedelta(days=1), response_body='{"code": 0}')
        old.updated_at = self.now + timedelta(days=2)
        self.session.commit()
        result = self.summaries()
        self.assertEqual(result[self.case["id"]]["record_id"], newest.id)
        self.assertEqual(result[self.case["id"]]["status"], "failed")
        self.assertEqual(result[self.case["id"]]["response_code"], 4001)
        self.assertIsNone(result[self.other["id"]])
        tied = self.record(response_body='{"code": 0}')
        self.assertEqual(self.summaries()[self.case["id"]]["record_id"], tied.id)

    def test_deleted_other_domain_and_other_project_records_do_not_replace_latest(self):
        valid = self.record(response_body='{"code": 0}')
        self.record(case_type="WEB", at=self.now + timedelta(days=1), response_body='{"code": 3}')
        self.record(project_id=2, at=self.now + timedelta(days=1), response_body='{"code": 4}')
        self.record(deleted=True, at=self.now + timedelta(days=1), response_body='{"code": 5}')
        result = self.summaries(project_id=None)[self.case["id"]]
        self.assertEqual(result["record_id"], valid.id)
        self.assertEqual(result["response_code"], 0)

    def test_runtime_errors_are_exceptions_not_assertion_failures(self):
        self.record(status="failed", error="连接超时", response_status=None)
        result = self.summaries()[self.case["id"]]
        self.assertEqual(result["status"], "exception")
        self.assertEqual(result["error"], "连接超时")
        self.assertIsNone(result["response_code"])

    def test_response_code_handles_zero_false_strings_and_non_json(self):
        for body, expected in [(' {"code": 0}', 0), ('{"code": false}', False), ('{"code":"E_BAD"}', "E_BAD"),
                               ('{"code":""}', ""), ('{"data":{"code":7}}', None), ('<html/>', None), ('[]', None)]:
            with self.subTest(body=body):
                self.assertEqual(extract_response_code(body), expected)
        self.record(status="success", response_body="not json", response_status=200)
        self.assertIsNone(self.summaries()[self.case["id"]]["response_code"])

    def test_latest_lookup_uses_one_query_and_is_opt_in(self):
        self.record(response_body='{"code":0}')
        queries = []
        def capture(_connection, _cursor, statement, _parameters, _context, _many):
            queries.append(statement)
        event.listen(self.engine, "before_cursor_execute", capture)
        rows = self.repository.latest_execution_records("API", [self.case["id"], self.other["id"]], 1)
        event.remove(self.engine, "before_cursor_execute", capture)
        self.assertEqual(len(queries), 1)
        self.assertEqual(len(rows), 1)
        plain, _ = self.service.list(None, 1, 1, 20)
        self.assertTrue(all("latest_execution" not in row for row in plain))
        self.assertEqual(self.repository.latest_execution_records("API", [], 1), [])

    def test_code_is_saved_before_large_response_body_is_truncated(self):
        body = json.dumps({"padding": "x" * 30000, "code": "TAIL"})
        executor = ApiCaseExecutor(self.repository)
        with patch.object(executor, "prepare_execution", return_value=(self.case, {})), \
             patch.object(executor, "_build_api_request", return_value={}), \
             patch.object(executor, "_send_http_request", return_value=(200, {}, body)), \
             patch.object(executor, "_assert_response", return_value=[{"passed": True}]):
            record = executor.execute(self.case, {})
        self.assertNotEqual(record["data"]["response_body"], body)
        self.assertEqual(record["data"]["response_code"], "TAIL")
        self.assertEqual(self.summaries()[self.case["id"]]["response_code"], "TAIL")

    def test_single_and_batch_delete_hide_cases_but_keep_execution_history(self):
        record = self.record(response_body='{"code":0}')
        self.assertTrue(self.service.delete(self.case["id"]))
        self.assertIsNone(self.repository.get("api_test_cases", self.case["id"]))
        self.assertIsNotNone(self.repository.get("execution_records", record.id))
        result = self.service.batch_delete([self.other["id"], self.other["id"]])
        self.assertEqual(result["deleted_count"], 1)
        self.assertEqual(self.service.list(None, 1, 1, 20)[1], 0)

    def test_api_list_returns_summary_when_requested(self):
        self.record(response_body='{"code":0}', response_status=200)
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_resource_repository] = lambda: self.repository
        with TestClient(app) as client:
            result = client.get("/api-testing/cases", params={"project_id": 1, "include_latest_execution": True}).json()
        rows = result["data"]["items"]
        selected = next(row for row in rows if row["id"] == self.case["id"])
        self.assertEqual(selected["latest_execution"]["response_code"], 0)
        self.assertEqual(selected["latest_execution"]["status"], "success")


if __name__ == "__main__":
    unittest.main()
