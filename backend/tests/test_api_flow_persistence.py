import tempfile
import time
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Event, Thread
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.dependencies import get_resource_repository
from app.api.exception_handlers import register_exception_handlers
from app.api.v1 import api_flow_runs, api_flow_scenarios, execution_flows
from app.models.resource_record import ResourceRecord
from app.models.test_case_record import ApiTestCaseRecord
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.services.api_flow_run_service import ApiFlowRunService
from app.services.api_flow_runner import ApiFlowRunner
from app.services.api_flow_scenario_service import ApiFlowScenarioService
from app.services.execution_flow_service import ExecutionFlowService
from tests.test_api_flows import FlowHandler


class ApiFlowPersistenceTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        url = f"sqlite:///{Path(self.directory.name) / 'flows.db'}"
        self.engine = create_engine(url, connect_args={"check_same_thread": False})
        ResourceRecord.__table__.create(self.engine)
        ApiTestCaseRecord.__table__.create(self.engine)
        self.sessions = sessionmaker(bind=self.engine)
        self.db = self.sessions()
        self.repo = SqlAlchemyResourceRepository(self.db)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FlowHandler)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        project = self.repo.create("projects", {"name": "Isolated test", "data": {"base_url": f"http://127.0.0.1:{self.server.server_port}"}})
        api = self.repo.create("api_interfaces", {"name": "Echo", "project_id": project["id"], "data": {"method": "POST", "path": "/echo"}})
        case = self.repo.create("api_test_cases", {"name": "Echo", "project_id": project["id"], "source_id": api["id"], "assertions": [{"type": "status", "expected": 200}]})
        self.flow = ExecutionFlowService(self.repo).create({"name": "Flow", "project_id": project["id"], "data": {"nodes": [
            {"key": "echo", "name": "Echo", "api_id": api["id"], "case_id": case["id"], "extracts": [{"name": "id", "path": "/data/id"}]}]}})
        self.scene = ApiFlowScenarioService(self.repo).create_for_flow(self.flow["id"], {"name": "Scenario"})

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.db.close()
        self.engine.dispose()
        self.directory.cleanup()

    def test_background_job_persists_sqlite_results(self):
        with patch("app.db.session.SessionLocal", self.sessions):
            batch = ApiFlowRunService(self.repo).create_batch(self.flow["id"], {
                "scenario_ids": [self.scene["id"]], "mode": "parallel", "concurrency": 2, "inputs": {}})
            finished = None
            for _ in range(100):
                with self.sessions() as db:
                    result = ApiFlowRunService(SqlAlchemyResourceRepository(db)).get_for_flow(self.flow["id"], batch["id"])
                if result["status"] not in {"queued", "running"}:
                    finished = result
                    break
                time.sleep(.05)
            self.assertIsNotNone(finished)
            self.assertEqual(finished["status"], "success", finished)
            self.assertEqual(finished["data"]["results"][0]["nodes"][0]["outputs"]["id"], 123)
            self.assertEqual(finished["data"]["results"][0]["path"], ["echo"])

    def test_routes_validate_ownership_and_template_versions(self):
        app = FastAPI()
        register_exception_handlers(app)
        for router in (execution_flows.router, api_flow_scenarios.router, api_flow_runs.router):
            app.include_router(router, prefix="/api/v1")
        app.dependency_overrides[get_resource_repository] = lambda: self.repo
        with TestClient(app) as client:
            prefix = f"/api/v1/execution/flows/{self.flow['id']}"
            response = client.get(prefix)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["data"]["data"]["nodes"][0]["key"], "echo")
            response = client.post(f"{prefix}/scenarios", json={"name": "New"})
            self.assertEqual(response.status_code, 200)
            scene_id = response.json()["data"]["id"]
            response = client.put(f"{prefix}/scenarios/{scene_id}", json={"data": {"nodes": {"missing": {"mode": "skip"}}}})
            self.assertEqual(response.status_code, 400)
            self.assertEqual(client.delete(f"{prefix}/scenarios/{scene_id}").status_code, 200)
            self.assertEqual(client.post(f"{prefix}/runs", json={"scenario_ids": [], "mode": "serial"}).status_code, 422)
            response = client.post(f"{prefix}/copy")
            self.assertEqual(response.status_code, 200)
            copied_id = response.json()["data"]["id"]
            self.assertEqual(client.get(f"/api/v1/execution/flows/{copied_id}/scenarios").json()["data"][0]["name"], "Scenario")

    def test_list_and_run_history_with_large_execution_evidence(self):
        for status in ("failed", "success"):
            self.repo.create("api_flow_runs", {
                "name": status, "project_id": self.flow["project_id"], "status": status,
                "data": {"flow_id": self.flow["id"], "results": [{"nodes": [{"response": "x" * 100_000}]}]},
            })
        app = FastAPI()
        register_exception_handlers(app)
        for router in (execution_flows.router, api_flow_runs.router):
            app.include_router(router, prefix="/api/v1")
        app.dependency_overrides[get_resource_repository] = lambda: self.repo
        with TestClient(app) as client:
            response = client.get("/api/v1/execution/flows", params={"project_id": self.flow["project_id"]})
            self.assertEqual(response.status_code, 200)
            page = response.json()["data"]
            self.assertEqual(page["total"], 1)
            data = page["items"][0]["data"]
            self.assertEqual(data["latest_status"], "通过")
            self.assertEqual(data["scenario_count"], 1)
            response = client.get(f"/api/v1/execution/flows/{self.flow['id']}/runs")
            self.assertEqual(response.status_code, 200)
            self.assertEqual([row["status"] for row in response.json()["data"]], ["success", "failed"])

    def wait_batch(self, batch_id):
        for _ in range(100):
            with self.sessions() as db:
                result = ApiFlowRunService(SqlAlchemyResourceRepository(db)).get_for_flow(self.flow["id"], batch_id)
            if result["status"] not in {"queued", "running"}:
                return result
            time.sleep(.05)
        self.fail("Batch did not finish")

    def test_parallel_failure_does_not_abort_other_scene(self):
        failed = ApiFlowScenarioService(self.repo).create_for_flow(self.flow["id"], {"name": "Expected failure", "data": {
            "nodes": {"echo": {"assertions": [{"type": "status", "expected": 401}]}}}})
        with patch("app.db.session.SessionLocal", self.sessions):
            batch = ApiFlowRunService(self.repo).create_batch(self.flow["id"], {
                "scenario_ids": [failed["id"], self.scene["id"]], "mode": "parallel", "concurrency": 2, "inputs": {}})
            result = self.wait_batch(batch["id"])
        self.assertEqual(result["status"], "failed")
        statuses = {row["scenario_id"]: row["status"] for row in result["data"]["results"]}
        self.assertEqual(statuses, {failed["id"]: "failed", self.scene["id"]: "success"})

    def test_cancellation_stops_before_next_node(self):
        data = self.flow["data"]
        data["nodes"].append({**data["nodes"][0], "key": "second", "name": "Second"})
        self.flow = ExecutionFlowService(self.repo).update(self.flow["id"], {"data": data})
        self.scene = ApiFlowScenarioService(self.repo).sync(self.flow["id"], self.scene["id"])
        entered, release = Event(), Event()
        execute = ApiFlowRunner._execute_node

        def delayed(runner, node, override):
            entered.set()
            release.wait(3)
            return execute(runner, node, override)

        with patch("app.db.session.SessionLocal", self.sessions), patch.object(ApiFlowRunner, "_execute_node", delayed):
            service = ApiFlowRunService(self.repo)
            batch = service.create_batch(self.flow["id"], {"scenario_ids": [self.scene["id"]], "mode": "serial", "concurrency": 1, "inputs": {}})
            self.assertTrue(entered.wait(3))
            self.assertTrue(service.cancel(self.flow["id"], batch["id"])["requested"])
            release.set()
            result = self.wait_batch(batch["id"])
        self.assertEqual(result["status"], "cancelled")
        scene = result["data"]["results"][0]
        self.assertEqual(scene["path"], ["echo"])
        self.assertEqual(scene["nodes"][1]["status"], "skipped")

    def test_abandoned_batch_is_marked_interrupted(self):
        service = ApiFlowRunService(self.repo)
        with patch("app.scheduler.jobs.api_flow_jobs.submit_api_flow_batch"):
            batch = service.create_batch(self.flow["id"], {"scenario_ids": [self.scene["id"]], "mode": "serial", "concurrency": 1, "inputs": {}})
        self.assertEqual(service.get_for_flow(self.flow["id"], batch["id"])["status"], "interrupted")


if __name__ == "__main__":
    unittest.main()
