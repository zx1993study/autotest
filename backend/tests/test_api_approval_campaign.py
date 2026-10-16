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

from app.scheduler.jobs.api_case_executor import ApiCaseExecutor
from app.services.api_flow_runner import ApiFlowRunner
from app.services.api_flow_scenario_service import ApiFlowScenarioService
from app.services.api_flow_snapshot_service import ApiFlowSnapshotService
from app.services.execution_flow_service import ExecutionFlowService
from tests.api_approval_fixtures import PATHS, ApprovalHTTP
from tests.test_api_flows import MemoryRepository


class ApprovalCampaignTest(unittest.TestCase):
    def setUp(self):
        scripts = str(Path(__file__).resolve().parents[2] / "scripts")
        sys.path.insert(0, scripts)
        self.addCleanup(lambda: sys.path.remove(scripts))
        self.campaign = importlib.import_module("waiqin_approval_campaign")
        self.builder = importlib.import_module("waiqin_approval_builder")
        self.repo = MemoryRepository()
        self.repo.counter = 20000
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.args = SimpleNamespace(project_id=10, snapshot_id=11942, flow_id=11775, auth_id=10015, output=Path(self.temp.name))
        self.put("projects", 10, data={"base_url": "http://example.invalid"})
        self.put("project_auth", 10015, data={"auth_type": "bearer", "token": "private-reviewer"})
        self.put("execution_flows", 11775, name="审批流程", data={"version": 1, "inputs": {}, "nodes": []})
        for api, (method, field) in PATHS.items():
            self.put("api_interfaces", api, data={"method": method, "path": f"/fixture/{api}" + ("/{" + field + "}" if field else ""),
                                                "schema_snapshot_id": 11942, "content_type": "application/json"})
            if field:
                self.put("api_fields", api, name=field, data={"name": field, "interface_id": api, "location": "path"})
        self.inventory = self.make_inventory()
        self.contracts = {"business": {"instances": [{"business_type": "visit_plan"}]}, "responses": {"field_library": {"process": {
            "apply": [{"fieldCode": code, "fieldLabel": code, "sort": n, "component": "textarea"}
                      for n, code in enumerate(("customers", "remark"))]}}}}
        self.fixtures = {"inputs": {"start_time": "2026-10-16T10:00:00", "end_time": "2026-10-17T10:00:00",
                                    "activity_start_time": "2026-10-14T10:00:00", "activity_end_time": "2026-11-16T10:00:00"},
                         "direct_customer": {"customer_id": 6, "customer_name": "approved-direct"},
                         "baselines": {12086: {"managerIds": [1], "cooperationStatus": "正在合作"},
                                       12205: {"order": {"salesType": "2"}, "items": []}, 12221: {"order": {}, "items": []},
                                       12199: {"warehouseId": 1, "items": []}, 12110: {"productScope": "all"},
                                       12126: {"customers": [{"customerId": 5}]}}}

    def put(self, table, item_id, **payload):
        self.repo.tables.setdefault(table, {})[item_id] = {"id": item_id, "name": "fixture", "project_id": 10,
                                                         "status": "active", "data": {}, **payload}

    def make_inventory(self):
        ids = {"terminal": 1, "direct": 5, "kol": 6, "sales": 12, "sales_direct": 24, "return": 13, "purchase": 11}
        definitions, nodes = [], []
        for spec in self.builder.BUSINESSES:
            if spec.key not in ids:
                continue
            role = {"purchase": 2, "sales_direct": 112}.get(spec.key)
            definitions.append({"flow_id": ids[spec.key], "business_type": spec.business_type, "status": "0", "activity_type": None,
                                "creator_role_id": role, "is_default": "0" if role else "1"})
            nodes.append({"flow_id": ids[spec.key], "approver_type": "1", "approver_ids": "1"})
        return {"project_id": 10, "platform": {"auth": [{"id": 10015, "username": "admin"}]}, "business": {
            "test_users": [{"user_id": 1, "user_name": "admin", "status": "0", "del_flag": "0"}],
            "test_user_roles": [{"user_id": 1, "role_id": 1}], "approval_flow_definition": {"configuration": definitions},
            "approval_flow_node": {"configuration": nodes}}}

    def generate(self):
        return self.campaign.generate(self.repo, self.args, self.inventory, self.contracts, self.fixtures)

    def snapshot(self, scene_name):
        self.generate()
        flow = ExecutionFlowService(self.repo).get(11775)
        scene = next(row for row in ApiFlowScenarioService(self.repo).list_for_flow(11775) if row["name"] == scene_name)
        with patch("app.services.api_flow_snapshot_service.ProjectAuthService.auth_headers",
                   return_value={"Authorization": "Bearer private-reviewer"}):
            return ApiFlowSnapshotService(self.repo).build(flow, scene, {})

    def run_scene(self, name, fault=""):
        runner = ApiFlowRunner(self.snapshot(name), Event())
        server = ApprovalHTTP(self.builder.BUSINESSES, fault)
        with patch.object(runner.executor, "_send_http_request", side_effect=server.send):
            result = runner.run()
        return result, server

    def test_generation_is_idempotent_without_any_business_http(self):
        with patch.object(ApiCaseExecutor, "_send_http_request") as send:
            first = self.generate()
            tables = deepcopy(self.repo.tables)
            second = self.generate()
        send.assert_not_called()
        self.assertEqual(first, second)
        self.assertEqual(tables, self.repo.tables)
        self.assertEqual(first["formal_cases"], 75)
        self.assertEqual(len(first["scenarios"]), 18)
        self.assertEqual(sum(row["status"] == "active" for row in first["scenarios"]), 14)
        self.assertFalse(first["executed_business_mutations"])
        self.assertEqual(first["historical_only"], ["visit_plan"])

    def test_all_pass_reject_contracts_run_with_new_ids_and_no_token_leaks(self):
        for spec in self.builder.BUSINESSES:
            for result_name in ("通过", "拒绝"):
                with self.subTest(business=spec.key, result=result_name):
                    result, server = self.run_scene(spec.name + "审批-" + result_name)
                    self.assertEqual(result["status"], "success", [(n["key"], n.get("error"), n.get("assertions")) for n in result["nodes"] if n["status"] == "failed"])
                    self.assertNotIn("private-reviewer", json.dumps(result))
                    self.assertNotIn("{{", json.dumps(server.calls))
                    approvals = [call for call in server.calls if call["method"] == "PUT"]
                    self.assertEqual(len(approvals), 2 if spec.key == "apply" else 1)
                    self.assertEqual(approvals[-1]["body"]["approveResult"], "1" if result_name == "通过" else "2")

    def test_unsafe_process_or_wrong_owner_never_reaches_approval(self):
        for fault in ("wrong_owner", "wrong_business", "wrong_approver", "not_current", "auto_skipped", "multiple_nodes"):
            with self.subTest(fault=fault):
                result, server = self.run_scene("前端客户审批-通过", fault)
                self.assertEqual(result["status"], "failed")
                self.assertFalse(any(call["method"] == "PUT" for call in server.calls))

    def test_wrong_business_rejection_status_is_not_http_200_success(self):
        result, _ = self.run_scene("前端客户审批-拒绝", "wrong_final_status")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["path"][-1], "terminal_verify_detail")

    def test_standalone_node_case_fails_before_sending_http(self):
        self.generate()
        case = next(row for row in self.repo.tables["api_test_cases"].values() if row["data"]["generation_key"] == "purchase_create")
        with patch.object(ApiCaseExecutor, "_send_http_request") as send:
            result = ApiCaseExecutor(self.repo).execute(case, {}, persist_record=False)
        self.assertEqual(result["status"], "failed")
        send.assert_not_called()

    def test_invalid_scope_fails_before_platform_writes(self):
        for failure in ("identity", "snapshot", "flow"):
            with self.subTest(failure=failure):
                original = deepcopy(self.repo.tables)
                if failure == "identity":
                    self.inventory["platform"]["auth"][0]["username"] = "another-user"
                elif failure == "snapshot":
                    self.repo.tables["api_interfaces"][12182]["data"]["schema_snapshot_id"] = 1
                else:
                    self.repo.tables["execution_flows"][11775]["name"] = "another-flow"
                before = deepcopy(self.repo.tables)
                with self.assertRaises(ValueError):
                    self.generate()
                self.assertEqual(before, self.repo.tables)
                self.repo.tables = original
                self.inventory = self.make_inventory()

    def test_activity_workflow_is_isolated_and_apply_depends_on_approved_activity(self):
        result, server = self.run_scene("活动申请审批-拒绝")
        self.assertEqual(result["status"], "success")
        self.assertEqual({row["businessType"] for row in server.flows.values()}, {"activity", "activity_apply"})
        self.assertTrue(all(row["isDefault"] == "0" and row["creatorRoleId"] == 1 for row in server.flows.values()))
        self.assertEqual(server.records["activity"]["approvalStatus"], "1")
        self.assertEqual(server.records["apply"]["status"], "2")

    def test_obsolete_legacy_nodes_are_backed_up_unbound_and_skipped(self):
        legacy = {"steps": [{"api_id": 7392, "case_id": 8, "auth_id": 10015, "api_label": "Old list"},
                            {"api_id": 7395, "case_id": 7, "auth_id": 10015, "api_label": "Old approve",
                             "case_json": {"nodeInstanceId": 1}}]}
        self.repo.tables["execution_flows"][11775]["data"] = legacy
        self.generate()
        backup = json.loads((self.args.output / "backup-flow-11775.json").read_text(encoding="utf-8"))
        self.assertEqual(backup["data"], legacy)
        flow = self.repo.get("execution_flows", 11775)
        self.assertEqual([step["api_id"] for step in flow["data"]["nodes"][:2]], [12179, 12182])
        self.assertTrue(all(step["case_id"] is None and not step["params"] for step in flow["data"]["nodes"][:2]))
        for scene in ApiFlowScenarioService(self.repo).list_for_flow(11775):
            self.assertEqual(scene["data"]["nodes"]["node_1"]["mode"], "skip")
            self.assertEqual(scene["data"]["nodes"]["node_2"]["mode"], "skip")

    def add_creator_auth(self):
        self.fixtures["creator_auth"] = {}
        for key, role, user_id, auth_id in (("purchase", 2, 251, 17001), ("sales_direct", 112, 252, 17002)):
            username = "qa_" + key
            self.inventory["business"]["test_users"].append({"user_id": user_id, "user_name": username, "status": "0", "del_flag": "0"})
            self.inventory["business"]["test_user_roles"].append({"user_id": user_id, "role_id": role})
            self.put("api_test_cases", auth_id + 10, source_id=11943, data={"params": {"username": username}, "skip_auth": True})
            self.put("project_auth", auth_id, data={"business_user_id": user_id, "role_ids": [role],
                "identity_verified_at": "2026-10-15T00:00:00+00:00", "login_case_type": "API", "login_case_id": auth_id + 10,
                "approval_identity_key": key, "username": username})
            self.fixtures["creator_auth"][key] = {"auth_id": auth_id, "user_id": user_id, "username": username}

    def test_verified_creator_roles_enable_all_scenarios_with_split_auth(self):
        self.add_creator_auth()
        result = self.generate()
        self.assertTrue(all(row["status"] == "active" for row in result["scenarios"]))
        flow = ExecutionFlowService(self.repo).get(11775)
        for step in flow["data"]["nodes"]:
            key = next((key for key in self.fixtures["creator_auth"] if step["key"].startswith(key + "_")), None)
            if not key:
                continue
            expected = 10015 if step["key"].endswith(("_process", "_approve")) else self.fixtures["creator_auth"][key]["auth_id"]
            self.assertEqual(step["auth_id"], expected)
            case = self.repo.get("api_test_cases", step["case_id"])
            self.assertEqual(case["data"]["auth_id"], expected)
            if step["key"] == "sales_direct_create":
                self.assertEqual(case["data"]["params"]["order"]["salesUserId"], 252)

    def test_invalid_creator_auth_fails_before_platform_writes(self):
        for failure in ("role", "project", "username", "disabled", "proof", "observed_roles"):
            with self.subTest(failure=failure):
                self.inventory = self.make_inventory()
                self.add_creator_auth()
                auth = self.repo.tables["project_auth"][17001]
                if failure == "role":
                    auth["data"]["role_ids"] = [1]
                elif failure == "project":
                    auth["project_id"] = 20
                elif failure == "username":
                    self.repo.tables["api_test_cases"][17011]["data"]["params"]["username"] = "admin"
                elif failure == "disabled":
                    self.inventory["business"]["test_users"][-2]["status"] = "1"
                elif failure == "proof":
                    auth["data"].pop("identity_verified_at")
                else:
                    self.inventory["business"]["test_user_roles"] = [{"user_id": 1, "role_id": 1}]
                before = deepcopy(self.repo.tables)
                with self.assertRaises(ValueError):
                    self.generate()
                self.assertEqual(before, self.repo.tables)

    def test_runtime_uses_creator_token_for_creation_and_reviewer_for_approval(self):
        self.add_creator_auth()
        self.generate()
        flow = ExecutionFlowService(self.repo).get(11775)
        scenes = ApiFlowScenarioService(self.repo).list_for_flow(11775)
        for name, auth_id in (("采购入库单审批-通过", 17001), ("直营销售订单审批-拒绝", 17002)):
            with self.subTest(name=name):
                scene = next(row for row in scenes if row["name"] == name)
                def headers(value):
                    return {"Authorization": "Bearer " + ("private-reviewer" if value == 10015 else f"private-creator-{value}")}
                with patch("app.services.api_flow_snapshot_service.ProjectAuthService.auth_headers", side_effect=headers):
                    snapshot = ApiFlowSnapshotService(self.repo).build(flow, scene, {})
                runner, server = ApiFlowRunner(snapshot, Event()), ApprovalHTTP(self.builder.BUSINESSES)
                with patch.object(runner.executor, "_send_http_request", side_effect=server.send):
                    result = runner.run()
                self.assertEqual(result["status"], "success")
                creates = [call for call in server.calls if call["method"] == "POST"]
                self.assertTrue(creates)
                self.assertTrue(all(call["headers"]["Authorization"] == f"Bearer private-creator-{auth_id}" for call in creates))
                self.assertNotIn("private-creator", json.dumps(result))

    def test_readback_verifies_both_node_and_formal_case_auth(self):
        self.add_creator_auth()
        manifest = self.generate()
        report = importlib.import_module("waiqin_approval_report")
        result = report.verify_configuration(self.repo, manifest)
        self.assertEqual(result["active"], 18)
        self.assertTrue(result["auth_bindings_valid"])
        flow = self.repo.tables["execution_flows"][11775]
        step = next(row for row in flow["data"]["nodes"] if row["key"] == "purchase_create")
        for target in (step, self.repo.tables["api_test_cases"][step["case_id"]]["data"]):
            with self.subTest(target="node" if target is step else "case"):
                original = target["auth_id"]
                target["auth_id"] = 10015
                with self.assertRaisesRegex(ValueError, "incorrectly bound"):
                    report.verify_configuration(self.repo, manifest)
                target["auth_id"] = original


if __name__ == "__main__":
    unittest.main()
