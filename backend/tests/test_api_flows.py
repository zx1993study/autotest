import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Event, Thread
from unittest.mock import patch

from app.core.exceptions import BusinessRuleError
from app.services.api_flow_run_service import ApiFlowRunService
from app.services.api_flow_runner import ApiFlowRunner
from app.services.api_flow_scenario_service import ApiFlowScenarioService
from app.services.api_flow_snapshot_service import ApiFlowSnapshotService
from app.services.execution_flow_service import ExecutionFlowService


class MemoryRepository:
    def __init__(self):
        self.tables = {}
        self.counter = 0

    def get(self, table, item_id):
        return deepcopy(self.tables.get(table, {}).get(item_id))

    def get_many(self, table, item_ids):
        return [self.get(table, item_id) for item_id in set(item_ids) if item_id in self.tables.get(table, {})]

    def list(self, table, keyword=None, project_id=None, page=1, page_size=20, data_filters=None):
        rows = list(self.tables.get(table, {}).values())
        rows = [row for row in rows if project_id is None or row.get("project_id") == project_id]
        rows = [row for row in rows if all((row["status"] if key == "status" else row["data"].get(key)) == value
                                          for key, value in (data_filters or {}).items())]
        return deepcopy(rows[(page - 1) * page_size:page * page_size]), len(rows)

    def create(self, table, payload):
        self.counter += 1
        row = {"id": self.counter, "description": None, "status": "active", "data": {}, **deepcopy(payload)}
        self.tables.setdefault(table, {})[row["id"]] = row
        return deepcopy(row)

    def update(self, table, item_id, payload):
        row = self.tables[table][item_id]
        row.update(deepcopy(payload))
        return deepcopy(row)

    def delete(self, table, item_id):
        return bool(self.tables.get(table, {}).pop(item_id, None))

    def batch_delete(self, table, ids):
        return sum(self.delete(table, item_id) for item_id in ids)


class FlowHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))) or "{}")
        if self.path == "/login":
            denied = body.get("password") == "wrong"
            self.send_json(401 if denied else 200, {"code": 401 if denied else 0,
                                                   "data": {} if denied else {"token": "private-token"}})
        else:
            self.send_json(200, {"code": 0, "data": {"id": body.get("id", 123), "name": body.get("name"),
                                                       "auth": self.headers.get("Authorization")}})

    def send_json(self, status, payload):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())

    def log_message(self, *_):
        pass


class ApiFlowsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), FlowHandler)
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        self.repo = MemoryRepository()
        self.project = self.repo.create("projects", {"name": "Project", "data": {"base_url": f"http://127.0.0.1:{self.server.server_port}"}})
        self.apis, self.cases = [], []
        for path in ("/login", "/echo"):
            api = self.repo.create("api_interfaces", {"name": path, "project_id": self.project["id"], "data": {"method": "POST", "path": path}})
            case = self.repo.create("api_test_cases", {"name": path, "source_id": api["id"], "project_id": self.project["id"], "data": {"params": {}},
                                                      "assertions": [{"type": "status", "expected": 200}]})
            self.apis.append(api)
            self.cases.append(case)
        self.flows = ExecutionFlowService(self.repo)
        self.scenes = ApiFlowScenarioService(self.repo)
        self.flow = self.flows.create({"name": "Lifecycle", "project_id": self.project["id"], "data": {"inputs": {"name": "Alice", "cleanup": False}, "nodes": [
            {"key": "login", "name": "Login", "api_id": self.apis[0]["id"], "case_id": self.cases[0]["id"],
             "params": {"password": "correct"}, "extracts": [{"name": "token", "path": "/data/token", "sensitive": True}],
             "routes": [{"source": "status", "path": "", "value": 401, "target": "end"}]},
            {"key": "create", "name": "Create", "api_id": self.apis[1]["id"], "case_id": self.cases[1]["id"],
             "bindings": [{"source": "login", "name": "token", "target": "headers", "path": "/Authorization", "prefix": "Bearer "},
                          {"source": "global", "name": "name", "target": "params", "path": "/name"}],
             "extracts": [{"name": "id", "path": "/data/id"}]},
            {"key": "delete", "name": "Delete", "api_id": self.apis[1]["id"], "case_id": self.cases[1]["id"],
             "bindings": [{"source": "create", "name": "id", "target": "params", "path": "/id"}]}]}})

    def snapshot(self, data=None):
        scene = self.scenes.create_for_flow(self.flow["id"], {"name": "Normal", "data": data or {}})
        return ApiFlowSnapshotService(self.repo).build(self.flow, scene, {})

    def test_actual_http_transfers_typed_values_and_masks_secrets(self):
        progress = []
        result = ApiFlowRunner(self.snapshot(), Event(), progress.append).run()
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["path"], ["login", "create", "delete"])
        self.assertEqual(result["nodes"][2]["request"]["body"]["id"], 123)
        self.assertIsInstance(result["nodes"][2]["request"]["body"]["id"], int)
        self.assertNotIn("private-token", json.dumps(result))
        self.assertNotIn("correct", json.dumps(result))
        self.assertGreater(len(progress), 1)
        self.assertNotIn("private-token", json.dumps(progress))

    def test_expected_rejection_is_passed_and_ends_branch(self):
        data = {"nodes": {"login": {"params": {"password": "wrong"}, "extracts": [],
                                    "assertions": [{"type": "status", "expected": 401}, {"type": "json_pointer", "path": "/code", "expected": 401}]}},
                "expected_end": "login"}
        result = ApiFlowRunner(self.snapshot(data), Event()).run()
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["path"], ["login"])
        self.assertEqual(result["nodes"][1]["status"], "skipped")

    def test_scene_node_names_apply_to_progress_failure_and_skipped_without_changing_template(self):
        snapshot = self.snapshot({"nodes": {"login": {"name": "Supervisor rejects order", "params": {"password": "wrong"}},
                                             "create": {"name": "Create meeting - weekly"}}})
        progress = []
        result = ApiFlowRunner(snapshot, Event(), progress.append).run()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["nodes"][0]["name"], "Supervisor rejects order")
        self.assertEqual(result["nodes"][1]["name"], "Create meeting - weekly")
        self.assertEqual(result["nodes"][1]["status"], "skipped")
        self.assertEqual(snapshot["flow"]["data"]["nodes"][0]["name"], "Login")
        self.assertEqual(result["nodes"][2]["name"], "Delete")
        ApiFlowRunner(self.snapshot({"nodes": {"login": {"name": "Supervisor approves order"}}}), Event(), progress.append).run()
        self.assertEqual(progress[-1]["nodes"][0]["name"], "Supervisor approves order")

    def test_condition_skip_and_missing_dependency_failure(self):
        result = ApiFlowRunner(self.snapshot({"nodes": {"delete": {"mode": "condition", "condition": {"source": "global", "name": "cleanup", "value": True}}}}), Event()).run()
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["nodes"][2]["status"], "skipped")
        result = ApiFlowRunner(self.snapshot({"nodes": {"login": {"mode": "skip"}}}), Event()).run()
        self.assertEqual(result["status"], "failed")
        self.assertIn("login.token", result["nodes"][1]["error"])

    def test_cancellation_and_variable_isolation(self):
        event = Event()
        event.set()
        self.assertEqual(ApiFlowRunner(self.snapshot(), event).run()["status"], "cancelled")
        snapshots = [self.snapshot({"inputs": {"name": name}}) for name in ("Alice", "Bob")]
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda snap: ApiFlowRunner(snap, Event()).run(), snapshots))
        self.assertEqual([row["nodes"][1]["request"]["body"]["name"] for row in results], ["Alice", "Bob"])

    def test_versions_sync_and_invalid_routes(self):
        snapshot = self.snapshot()
        data = deepcopy(self.flow["data"])
        data["inputs"]["name"] = "changed"
        self.flows.update(self.flow["id"], {"data": data})
        request = {"scenario_ids": [snapshot["scenario"]["id"]], "mode": "serial", "concurrency": 1}
        with self.assertRaises(BusinessRuleError):
            ApiFlowRunService(self.repo).create_batch(self.flow["id"], request)
        synced = self.scenes.sync(self.flow["id"], snapshot["scenario"]["id"])
        self.assertEqual(synced["data"]["template_version"], 2)
        self.assertEqual(ApiFlowRunner(snapshot, Event()).run()["nodes"][1]["request"]["body"]["name"], "Alice")
        data["nodes"][2]["next"] = "login"
        with self.assertRaises(BusinessRuleError):
            self.flows.update(self.flow["id"], {"data": data})

    def test_batch_freezes_before_submission_and_checks_project(self):
        snapshot = self.snapshot()
        request = {"scenario_ids": [snapshot["scenario"]["id"]], "mode": "parallel", "concurrency": 2}
        with patch("app.scheduler.jobs.api_flow_jobs.submit_api_flow_batch") as submit:
            batch = ApiFlowRunService(self.repo).create_batch(self.flow["id"], request)
        self.assertEqual(batch["status"], "queued")
        self.assertEqual(submit.call_args.args[2], 2)
        self.assertNotIn("password", json.dumps(batch))
        other_project = self.repo.create("projects", {"name": "Other"})
        with self.assertRaises(BusinessRuleError):
            self.flows.create({"name": "Bad", "project_id": other_project["id"], "data": self.flow["data"]})


if __name__ == "__main__":
    unittest.main()
