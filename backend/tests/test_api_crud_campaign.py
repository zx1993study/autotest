import importlib
import json
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from threading import Event
from types import SimpleNamespace
from unittest.mock import patch

from app.services.api_flow_runner import ApiFlowRunner
from app.services.api_flow_scenario_service import ApiFlowScenarioService
from app.services.api_flow_snapshot_service import ApiFlowSnapshotService
from app.services.execution_flow_service import ExecutionFlowService
from tests.test_api_flows import MemoryRepository


class CrudCampaignTest(unittest.TestCase):
    def setUp(self):
        scripts = str(Path(__file__).resolve().parents[2] / "scripts")
        sys.path.insert(0, scripts)
        self.addCleanup(lambda: sys.path.remove(scripts))
        self.campaign = importlib.import_module("api_crud_campaign")
        self.definitions = importlib.import_module("waiqin_crud_definitions")
        self.repo = MemoryRepository()
        self.repo.counter = 20000
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.args = SimpleNamespace(project_id=10, snapshot_id=9, auth_id=10015, campaign="unit-crud",
                                    profiles=Path(self.temp.name) / "profiles.json", output=Path(self.temp.name))
        self.put("projects", 10, name="Unit", data={"base_url": "http://example.invalid"})
        self.put("project_auth", 10015, data={"token": "private-token", "auth_type": "bearer"})
        self.put("api_modules", 1, name="业务管理-测试")
        self.profiles = []
        for module in self.definitions.MODULES:
            params = {"warehouseName": "仓库", "customerId": 1, "visitorUserId": 1, "visitorUserName": "员工",
                      "visitPlans": [{"customerId": 1}], "order": {"customerId": 1}, "items": [],
                      "weeklyData": {"1": [1]}, "templates": {"apply": []}}
            self.profiles.append({"source_id": module.create, "params": params})
            for kind in ("create", "listing", "detail", "edit", "delete"):
                aid = getattr(module, kind)
                if aid:
                    self.api(aid, kind)
        for _, _, listing, detail, _ in self.definitions.QUERY_MODULES:
            self.api(listing, "listing")
            if detail:
                self.api(detail, "detail" if detail != 12227 else "listing")
        self.save_profiles()

    def put(self, table, item_id, **payload):
        self.repo.tables.setdefault(table, {})[item_id] = {
            "id": item_id, "name": "fixture", "project_id": 10, "status": "active", "data": {}, **payload}

    def api(self, aid, kind):
        method = {"create": "POST", "edit": "PUT", "delete": "DELETE"}.get(kind, "GET")
        path = f"/business/fixture/{aid}"
        if kind in {"detail", "delete"}:
            path += "/{record_id}"
            self.put("api_fields", aid, name="record_id", data={"interface_id": aid, "name": "record_id", "location": "path"})
        self.put("api_interfaces", aid, data={"method": method, "path": path, "module_id": 1,
                                              "schema_snapshot_id": 9, "content_type": "application/json"})

    def save_profiles(self, project_id=10):
        self.args.profiles.write_text(json.dumps({"project_id": project_id, "snapshot_id": 9,
                                                  "profiles": self.profiles}), encoding="utf-8")

    def generate(self):
        return self.campaign.generate(self.repo, self.args)

    def warehouse_snapshot(self, failure_policy="stop"):
        manifest = self.generate()
        flow_id = manifest["flows"][0]["id"]
        flow = ExecutionFlowService(self.repo).get(flow_id)
        scene = ApiFlowScenarioService(self.repo).list_for_flow(flow_id)[0]
        scene["data"]["failure_policy"] = failure_policy
        with patch("app.services.api_flow_snapshot_service.ProjectAuthService.auth_headers",
                   return_value={"Authorization": "Bearer private-token"}):
            return ApiFlowSnapshotService(self.repo).build(flow, scene, {})

    def warehouse_http(self, wrong_owner=False):
        state = {"calls": [], "record": {}}

        def send(request):
            state["calls"].append(deepcopy(request))
            method = request["method"]
            if method == "POST":
                state["record"] = {"warehouseId": 77, "warehouseName": request["body"]["warehouseName"]}
                payload = {"code": 200}
            elif method == "PUT":
                self.assertEqual(request["body"]["warehouseId"], 77)
                state["record"].update(warehouseName=request["body"]["warehouseName"])
                payload = {"code": 200}
            elif method == "DELETE":
                self.assertTrue(request["path"].endswith("/77"))
                state["record"] = {"warehouseId": None}
                payload = {"code": 200}
            elif "12184" in request["path"]:
                row = {**state["record"], **({"warehouseName": "existing-business-data"} if wrong_owner else {})}
                payload = {"code": 200, "rows": [row]}
            else:
                self.assertTrue(request["path"].endswith("/77"))
                payload = {"code": 200, "data": dict(state["record"])}
            return 200, {"Content-Type": "application/json"}, json.dumps(payload)

        return state, send

    def test_creation_is_complete_idempotent_and_never_sends_http(self):
        original = self.repo.create("execution_flows", {"name": "Existing", "project_id": 10, "data": {"nodes": []}})
        with patch("app.scheduler.jobs.api_case_executor.ApiCaseExecutor._send_http_request") as send:
            first = self.generate()
            counts = {key: len(value) for key, value in self.repo.tables.items()}
            second = self.generate()
        send.assert_not_called()
        self.assertEqual(len(first["flows"]), 19)
        self.assertEqual(first, second)
        self.assertEqual(counts, {key: len(value) for key, value in self.repo.tables.items()})
        self.assertEqual(self.repo.get("execution_flows", original["id"]), original)
        self.assertFalse(first["executed_business_mutations"])
        self.assertTrue(all(self.repo.get("execution_flows", row["id"])["data"]["version"] == 1 for row in first["flows"]))

    def test_wrong_project_or_endpoint_method_fails_before_any_write(self):
        counts = {key: len(value) for key, value in self.repo.tables.items()}
        self.save_profiles(project_id=11)
        with self.assertRaises(ValueError):
            self.generate()
        self.save_profiles()
        self.repo.tables["api_interfaces"][12190]["data"]["method"] = "POST"
        with self.assertRaises(ValueError):
            self.generate()
        self.assertEqual(counts, {key: len(value) for key, value in self.repo.tables.items()})

    def test_missing_capabilities_are_not_substituted_and_apply_delete_is_disabled(self):
        manifest = self.generate()
        by_key = {row["key"]: row for row in manifest["flows"]}
        self.assertFalse(by_key["supervision"]["capabilities"]["delete"])
        self.assertFalse(by_key["purchase"]["capabilities"]["edit"])
        self.assertEqual([row["status"] for row in by_key["activity_apply"]["scenarios"]], ["disabled", "active"])
        for key in ("stock_in", "outbound", "todo", "transaction", "terminal_inventory"):
            for step in by_key[key]["nodes"]:
                self.assertEqual(self.repo.get("api_interfaces", step["api_id"])["data"]["method"], "GET")

    def test_mock_http_runs_ownership_checked_crud_with_one_frozen_marker(self):
        snapshot = self.warehouse_snapshot()
        state, send = self.warehouse_http()
        runner = ApiFlowRunner(snapshot, Event())
        with patch.object(runner.executor, "_send_http_request", side_effect=send):
            result = runner.run()
        self.assertEqual(result["status"], "success", result)
        self.assertEqual(len(state["calls"]), 7)
        self.assertNotIn("{{", json.dumps(state["calls"]))
        marker = result["inputs"]["record_marker"]
        self.assertEqual(state["calls"][0]["body"]["warehouseName"], marker)
        self.assertEqual(state["calls"][1]["query"]["warehouseName"], marker)
        self.assertEqual(state["calls"][3]["body"]["warehouseName"], result["inputs"]["updated_marker"])
        self.assertNotIn("private-token", json.dumps(result))
        self.assertEqual(result["nodes"][2]["assertions"][-2]["expected"], 77)

    def test_failed_owner_check_cannot_feed_ids_even_with_continue_policy(self):
        snapshot = self.warehouse_snapshot(failure_policy="continue")
        state, send = self.warehouse_http(wrong_owner=True)
        runner = ApiFlowRunner(snapshot, Event())
        with patch.object(runner.executor, "_send_http_request", side_effect=send):
            result = runner.run()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(len(state["calls"]), 2)
        self.assertNotIn("locate", runner.variables)
        self.assertTrue(all(call["method"] not in {"PUT", "DELETE"} for call in state["calls"]))

    def test_partial_required_extraction_failure_publishes_no_ids(self):
        snapshot = self.warehouse_snapshot(failure_policy="continue")
        locate = snapshot["flow"]["data"]["nodes"][1]
        locate["extracts"].append({"name": "missing", "source": "body", "path": "/missing",
                                   "required": True, "sensitive": False})
        state, send = self.warehouse_http()
        runner = ApiFlowRunner(snapshot, Event())
        with patch.object(runner.executor, "_send_http_request", side_effect=send):
            result = runner.run()
        self.assertEqual(result["status"], "failed")
        self.assertNotIn("locate", runner.variables)
        self.assertEqual(len(state["calls"]), 2)

    def test_legacy_input_names_and_null_case_variables_remain_compatible(self):
        snapshot = self.warehouse_snapshot()
        snapshot["flow"]["data"]["inputs"].update({"中文备注": "原有场景输入", "old-name": "legacy"})
        for case in snapshot["cases"].values():
            case["data"]["variables"] = None
        state, send = self.warehouse_http()
        runner = ApiFlowRunner(snapshot, Event())
        with patch.object(runner.executor, "_send_http_request", side_effect=send):
            result = runner.run()
        self.assertEqual(result["status"], "success", result)
        self.assertEqual(len(state["calls"]), 7)

    def test_edit_and_delete_cases_contain_no_historical_target_ids(self):
        manifest = self.generate()
        for flow in manifest["flows"]:
            template = self.repo.get("execution_flows", flow["id"])
            for node in template["data"]["nodes"]:
                if node["key"] not in {"edit", "delete"}:
                    continue
                case = self.repo.get("api_test_cases", node["case_id"])
                self.assertIn("{{owned_id}}", json.dumps(case["data"]["params"]))
                self.assertTrue(any(link["name"] == "owned_id" and link["source"] in {"create", "locate"}
                                    for link in node["bindings"]))

    def test_query_scene_does_not_create_apply_or_require_marker(self):
        flow_info = next(row for row in self.generate()["flows"] if row["key"] == "activity_apply")
        flow = ExecutionFlowService(self.repo).get(flow_info["id"])
        scenes = ApiFlowScenarioService(self.repo).list_for_flow(flow["id"])
        scene = next(row for row in scenes if row["status"] == "active")
        with patch("app.services.api_flow_snapshot_service.ProjectAuthService.auth_headers",
                   return_value={"Authorization": "Bearer private-token"}):
            snapshot = ApiFlowSnapshotService(self.repo).build(flow, scene, {})
        runner = ApiFlowRunner(snapshot, Event())
        with patch.object(runner.executor, "_send_http_request", return_value=(200, {}, '{"code":200,"rows":[]}')) as send:
            result = runner.run()
        self.assertEqual(result["status"], "success", result)
        self.assertEqual(send.call_count, 1)
        self.assertEqual(send.call_args.args[0]["method"], "GET")
        self.assertNotIn("remark", send.call_args.args[0]["query"])


if __name__ == "__main__":
    unittest.main()
