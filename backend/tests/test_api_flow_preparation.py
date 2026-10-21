import unittest
from copy import deepcopy
from threading import Event
from unittest.mock import patch

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.core.exceptions import BusinessRuleError
from app.models.resource_record import ResourceRecord
from app.models.test_case_record import ApiTestCaseRecord
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.services.api_flow_preparation_service import ApiFlowPreparationService
from app.services.api_flow_run_service import ApiFlowRunService
from app.services.api_flow_runner import ApiFlowRunner
from app.services.api_flow_validation import parse_definition


class FlowPreparationTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        ResourceRecord.__table__.create(self.engine)
        ApiTestCaseRecord.__table__.create(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.repo = SqlAlchemyResourceRepository(self.db)
        self.project = self.repo.create("projects", {"name": "Project", "data": {"base_url": "http://example.invalid"}})
        project_id = self.project["id"]
        self.auth = self.repo.create("project_auth", {"name": "Reviewer", "project_id": project_id,
                                                   "data": {"auth_type": "bearer", "token": "test-secret"}})
        self.api = self.repo.create("api_interfaces", {"name": "Echo", "project_id": project_id,
                                                       "data": {"method": "GET", "path": "/echo"}})
        self.repo.create("api_fields", {"name": "search", "project_id": project_id,
            "data": {"interface_id": self.api["id"], "name": "search", "location": "query"}})
        self.repo.create("api_fields", {"name": "unused", "project_id": project_id,
            "data": {"interface_id": 999999, "name": "unused", "location": "query"}})
        self.repo.create("api_import_tasks", {"name": "Schema", "project_id": project_id,
            "data": {"source_type": "url", "source": "http://example.invalid/openapi.json"}})
        nodes = []
        for index in range(91):
            case = self.repo.create("api_test_cases", {"name": f"Case {index}", "project_id": project_id,
                "source_id": self.api["id"], "data": {"auth_id": self.auth["id"]},
                "assertions": [{"type": "status", "expected": 200}]})
            nodes.append({"key": f"node_{index}", "name": f"Node {index}", "api_id": self.api["id"],
                          "case_id": case["id"], "auth_id": self.auth["id"]})
        self.flow = self.repo.create("execution_flows", {"name": "Flow", "project_id": project_id,
                                                        "data": parse_definition({"nodes": nodes})})
        self.scenes = [self.repo.create("api_flow_scenarios", {"name": f"Scene {index}", "project_id": project_id,
            "data": {"flow_id": self.flow["id"], "template_version": 1, "inputs": {"marker": index},
                     "nodes": {node["key"]: {"mode": "skip"} for node in nodes[5:]},
                     "expected_end": "auto", "failure_policy": "stop"}}) for index in range(3)]
        self.statements = []
        event.listen(self.engine, "before_cursor_execute", self.record_statement)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def record_statement(self, connection, cursor, statement, parameters, context, executemany):
        self.statements.append(statement)

    def prepare(self, scenes=None):
        return ApiFlowPreparationService(self.repo).build(self.flow, scenes or self.scenes, {})

    def test_many_scenarios_share_bounded_database_reads_and_auth_file_read(self):
        with patch("app.services.api_flow_snapshot_service.ProjectAuthService.auth_headers",
                   return_value={"Authorization": "Bearer test-secret"}) as headers:
            snapshots = self.prepare()
        self.assertEqual(len(self.statements), 10)
        self.assertTrue(all(statement.lstrip().startswith("SELECT") for statement in self.statements))
        self.assertEqual(headers.call_count, 1)
        self.assertEqual(len(snapshots), 3)
        for snapshot in snapshots:
            self.assertEqual(set(snapshot["cases"]), {f"node_{index}" for index in range(5)})
            self.assertEqual(len(snapshot["references"]["api_interfaces"]), 1)
            self.assertEqual([field["name"] for field in snapshot["references"]["api_fields"]], ["search"])
        snapshots[0]["cases"]["node_0"]["data"]["headers"]["Authorization"] = "changed"
        self.assertEqual(snapshots[1]["cases"]["node_0"]["data"]["headers"]["Authorization"], "Bearer test-secret")
        self.assertNotIn("headers", self.repo.get("api_test_cases", 1)["data"])

    def test_skipped_case_auth_is_not_prepared_but_nodes_remain_in_evidence(self):
        node = self.flow["data"]["nodes"][-1]
        self.repo.update("api_test_cases", node["case_id"], {"data": {"auth_id": 999999}})
        snapshot = self.prepare([self.scenes[0]])[0]
        progress = []
        runner = ApiFlowRunner(snapshot, Event(), progress.append)
        with patch.object(runner.executor, "_send_http_request", return_value=(200, {}, '{}')) as send:
            result = runner.run()
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["nodes"]), 91)
        self.assertEqual(result["nodes"][-1]["status"], "skipped")
        self.assertEqual(send.call_count, 5)
        self.assertEqual(len(progress), 6)
        self.assertEqual(len(progress[-1]["nodes"]), 5)

    def test_case_override_is_loaded_and_project_and_api_ownership_are_checked(self):
        override = self.repo.create("api_test_cases", {"name": "Override", "project_id": self.project["id"],
                                                     "source_id": self.api["id"]})
        scene = deepcopy(self.scenes[0])
        scene["data"]["nodes"]["node_0"] = {"case_id": override["id"]}
        self.assertEqual(self.prepare([scene])[0]["cases"]["node_0"]["id"], override["id"])
        for payload in ({"project_id": 999}, {"source_id": 999}, {"status": "disabled"}):
            with self.subTest(payload=payload):
                self.repo.update("api_test_cases", override["id"], {"project_id": self.project["id"],
                    "source_id": self.api["id"], "status": "active", **payload})
                with self.assertRaises(BusinessRuleError):
                    self.prepare([scene])

    def test_missing_references_fail_before_creating_or_submitting_batch(self):
        self.repo.delete("api_test_cases", self.flow["data"]["nodes"][0]["case_id"])
        with patch("app.scheduler.jobs.api_flow_jobs.submit_api_flow_batch") as submit, self.assertRaises(BusinessRuleError):
            ApiFlowRunService(self.repo).create_batch(self.flow["id"], {
                "scenario_ids": [self.scenes[0]["id"]], "mode": "serial", "concurrency": 1})
        submit.assert_not_called()
        self.assertEqual(self.repo.list("api_flow_runs")[1], 0)

    def test_snapshot_uses_frozen_case_and_auth_after_configuration_changes(self):
        snapshot = self.prepare([self.scenes[0]])[0]
        self.repo.update("api_test_cases", self.flow["data"]["nodes"][0]["case_id"], {"data": {"params": {"changed": True}}})
        self.repo.update("project_auth", self.auth["id"], {"data": {"token": "new-secret"}})
        self.assertNotIn("params", snapshot["cases"]["node_0"]["data"])
        self.assertEqual(snapshot["cases"]["node_0"]["data"]["headers"]["Authorization"], "Bearer test-secret")


if __name__ == "__main__":
    unittest.main()
