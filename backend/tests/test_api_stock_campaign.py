import importlib
import json
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from threading import Event
from unittest.mock import patch

from app.scheduler.jobs.api_case_executor import ApiCaseExecutor
from app.services.api_flow_runner import ApiFlowRunner
from app.services.api_flow_scenario_service import ApiFlowScenarioService
from app.services.api_flow_snapshot_service import ApiFlowSnapshotService
from app.services.execution_flow_service import ExecutionFlowService
from tests.api_stock_fixtures import PATHS, StockHTTP, inventory_fixture
from tests.test_api_flows import MemoryRepository


class StockCampaignTest(unittest.TestCase):
    def setUp(self):
        scripts = str(Path(__file__).resolve().parents[2] / "scripts")
        sys.path.insert(0, scripts)
        self.addCleanup(lambda: sys.path.remove(scripts))
        self.campaign = importlib.import_module("waiqin_stock_campaign")
        self.repo, self.apis = MemoryRepository(), []
        self.repo.counter = 30000
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name)
        self.put("projects", 10, data={"base_url": "http://example.invalid"})
        for aid in (10015, 16306, 16307):
            self.put("project_auth", aid)
        for aid, (method, path) in PATHS.items():
            row = self.put("api_interfaces", aid, data={"method": method,
                "path": f"/fixture/{aid}" + ("/{" + path + "}" if path else ""), "schema_snapshot_id": 11942,
                "schema_hash": "verified", "content_type": "application/json"})
            self.apis.append(row)
            if path:
                self.put("api_fields", aid, name=path, data={"name": path, "interface_id": aid, "location": "path"})
        self.inventory = inventory_fixture(self.apis)
        self.plans = self.campaign.build_plans(self.inventory)

    def put(self, table, item_id, **payload):
        row = {"id": item_id, "name": "fixture", "project_id": 10, "status": "active", "data": {}, **payload}
        self.repo.tables.setdefault(table, {})[item_id] = row
        return row

    def generate(self):
        return self.campaign.generate(self.repo, self.output, self.inventory, self.plans)

    def snapshot(self, flow_id, scene):
        def headers(aid):
            return {"Authorization": {10015: "Bearer private-reviewer", 16306: "Bearer private-creator", 16307: "Bearer private-outsider"}[aid]}
        flow = ExecutionFlowService(self.repo).get(flow_id)
        with patch("app.services.api_flow_snapshot_service.ProjectAuthService.auth_headers", side_effect=headers):
            return ApiFlowSnapshotService(self.repo).build(flow, scene, {})

    def run_scene(self, entry, scene_key, fault=""):
        scene = next(row for row in ApiFlowScenarioService(self.repo).list_for_flow(entry["id"])
                     if row["data"]["inputs"]["stock_scene_key"] == scene_key)
        runner, server = ApiFlowRunner(self.snapshot(entry["id"], scene), Event()), StockHTTP(fault)
        with patch.object(runner.executor, "_send_http_request", side_effect=server.send):
            result = runner.run()
        return result, server

    def test_generation_is_idempotent_and_never_executes_business_http(self):
        with patch.object(ApiCaseExecutor, "_send_http_request") as send:
            first = self.generate()
            before = deepcopy(self.repo.tables)
            second = self.generate()
        send.assert_not_called()
        self.assertEqual(first, second)
        self.assertEqual(before, self.repo.tables)
        self.assertEqual(sum(len(flow["scenes"]) for flow in first["flows"]), 49)
        self.assertEqual(sum(scene["status"] == "disabled" for flow in first["flows"] for scene in flow["scenes"]), 1)

    def test_all_enabled_stock_return_and_conversion_scenarios(self):
        manifest = self.generate()
        for entry in manifest["flows"]:
            for scene in entry["scenes"]:
                if scene["status"] != "active":
                    continue
                with self.subTest(flow=entry["name"], scene=scene["key"]):
                    result, server = self.run_scene(entry, scene["key"])
                    failures = [(row["key"], row.get("error"), row.get("assertions")) for row in result["nodes"] if row["status"] == "failed"]
                    self.assertEqual(result["status"], "success", failures)
                    self.assertEqual(server.stock[5], {"quantity": 200, "lockedQuantity": 20})
                    self.assertNotIn("private-", json.dumps(result))
                    self.assertNotIn("{{", json.dumps(server.calls))

    def test_receipt_owner_product_and_quantity_mismatch_prevent_confirmation(self):
        entry = self.generate()["flows"][0]
        for fault in ("wrong_receipt_owner", "wrong_receipt_product", "wrong_receipt_quantity"):
            with self.subTest(fault=fault):
                result, server = self.run_scene(entry, "sales_ship", fault)
                self.assertEqual(result["status"], "failed")
                self.assertFalse(any("/12214" in call["path"] for call in server.calls))

    def test_wrong_lock_quantity_fails_before_shipping(self):
        entry = self.generate()["flows"][0]
        result, server = self.run_scene(entry, "sales_ship", "wrong_lock")
        self.assertEqual(result["status"], "failed")
        self.assertFalse(any("/12214" in call["path"] for call in server.calls))

    def test_standalone_formal_case_never_sends_a_request(self):
        self.generate()
        for case in self.repo.tables["api_test_cases"].values():
            with self.subTest(api=case["source_id"]), patch.object(ApiCaseExecutor, "_send_http_request") as send:
                result = ApiCaseExecutor(self.repo).execute(case, {}, persist_record=False)
                self.assertEqual(result["status"], "failed")
                send.assert_not_called()

    def test_invalid_scope_or_running_flow_fails_before_writes(self):
        self.generate()
        entry = self.campaign.existing_flow(self.repo, self.plans[0])
        for failure in ("role", "schema", "warehouse", "running"):
            with self.subTest(failure=failure):
                original, inventory = deepcopy(self.repo.tables), deepcopy(self.inventory)
                if failure == "role":
                    next(row for row in self.inventory["business"]["test_user_roles"] if row["user_id"] == 251)["role_id"] = 1
                elif failure == "schema":
                    self.repo.tables["api_interfaces"][12195]["data"]["schema_hash"] = "changed"
                elif failure == "warehouse":
                    self.inventory["fixtures"]["warehouse"]["admin_user_id"] = 2
                else:
                    self.put("api_flow_runs", 40000, status="running", data={"flow_id": entry["id"]})
                before = deepcopy(self.repo.tables)
                with self.assertRaises(ValueError):
                    self.generate()
                self.assertEqual(before, self.repo.tables)
                self.repo.tables, self.inventory = original, inventory

    def test_readback_verification(self):
        manifest = self.generate()
        report = importlib.import_module("waiqin_stock_report")
        result = report.verify_configuration(self.repo, manifest)
        self.assertEqual((result["scenes"], result["active"], result["disabled"]), (49, 48, 1))
        self.assertTrue(result["references_valid"])
        report.write_report(self.output, manifest, result)
        self.assertIn("采购独立确认", (self.output / "report.md").read_text(encoding="utf-8"))

    def test_duplicate_scene_name_or_key_is_rejected_before_writes(self):
        for field in ("name", "key"):
            with self.subTest(field=field):
                plans = deepcopy(self.plans)
                plans[0]["scenes"][1][field] = plans[0]["scenes"][0][field]
                before = deepcopy(self.repo.tables)
                with self.assertRaises(ValueError):
                    self.campaign.generate(self.repo, self.output, self.inventory, plans)
                self.assertEqual(before, self.repo.tables)

    def test_stock_generation_has_no_permission_scenarios_or_outsider_auth(self):
        for plan in self.plans:
            for scene in plan["scenes"]:
                self.assertNotIn("权限", scene["name"])
                for step in scene["nodes"]:
                    self.assertNotEqual(step.get("auth_id"), 16307)
                    self.assertFalse(any(row.get("type") == "api_rejection" and row.get("expected") == "auth"
                                         for row in step["assertions"]))

    def legacy_permissions(self):
        cleanup = importlib.import_module("waiqin_stock_cleanup")
        originals = deepcopy(self.plans)
        for plan, normal in zip(self.plans, ("sales_ship", "direct_pass", "unpack"), strict=True):
            retired, _ = cleanup.RETIRED[plan["key"]]
            legacy = deepcopy(next(row for row in plan["scenes"] if row["key"] == normal))
            legacy.update(key=retired, name="permission-" + plan["key"])
            prefix = "return_receipt" if plan["key"] == "return" else "receipt"
            for step in legacy["nodes"]:
                if step["key"] in {"convert", prefix + "_confirm"}:
                    if step["key"] != "convert":
                        step["key"] = prefix + "_wrong_user"
                    step.update(auth_id=16307, assertions=[{"type": "api_rejection", "expected": "auth"}])
                elif step["key"] == prefix + "_verified":
                    step["key"] = prefix + "_still_pending"
            plan["scenes"].append(legacy)
        manifest = self.generate()
        self.plans = originals
        return manifest

    def test_permission_cleanup_preserves_quantity_scenarios_history_and_auth(self):
        manifest = self.legacy_permissions()
        cleanup = importlib.import_module("waiqin_stock_cleanup")
        history = self.put("api_flow_runs", 40000, status="failed", data={"flow_id": manifest["flows"][2]["id"],
                           "results": [{"scenario_id": manifest["flows"][2]["scenes"][-1]["id"], "status": "failed"}]})
        kept = {row["id"]: deepcopy(row) for row in self.repo.tables["api_flow_scenarios"].values()
                if not row["name"].startswith("permission-")}
        with patch.object(ApiCaseExecutor, "_send_http_request") as send:
            result = cleanup.remove_permissions(self.repo, self.output, manifest)
        send.assert_not_called()
        self.assertEqual(len(result["removed_scenes"]), 3)
        self.assertEqual(len(result["removed_case_ids"]), 5)
        self.assertEqual(result["verification"]["scenes"], 49)
        self.assertEqual(result["verification"]["formal_cases"], sum(row["formal_cases"] for row in manifest["flows"]) - 5)
        self.assertEqual(self.repo.get("api_flow_runs", 40000), history)
        self.assertIsNotNone(self.repo.get("project_auth", 16307))
        for scene_id, previous in kept.items():
            actual = self.repo.get("api_flow_scenarios", scene_id)
            self.assertEqual(actual["name"], previous["name"])
            self.assertEqual(actual["status"], previous["status"])
            self.assertEqual(actual["data"]["inputs"], previous["data"]["inputs"])
            for key, override in actual["data"]["nodes"].items():
                self.assertEqual(override, previous["data"]["nodes"][key])
        current = json.loads((self.output / "manifest.json").read_text(encoding="utf-8"))
        before = deepcopy(self.repo.tables)
        again = cleanup.remove_permissions(self.repo, self.output, current)
        self.assertEqual(again["removed_scenes"], [])
        self.assertEqual(again["removed_case_ids"], [])
        self.assertEqual(before, self.repo.tables)

    def test_permission_cleanup_rejects_any_running_flow_before_writes(self):
        manifest = self.legacy_permissions()
        self.put("api_flow_runs", 40000, status="running", data={"flow_id": manifest["flows"][-1]["id"]})
        before = deepcopy(self.repo.tables)
        with self.assertRaises(ValueError):
            importlib.import_module("waiqin_stock_cleanup").remove_permissions(self.repo, self.output, manifest)
        self.assertEqual(before, self.repo.tables)

    def test_permission_cleanup_keeps_cases_referenced_by_other_flows(self):
        manifest = self.legacy_permissions()
        scene = next(row for row in self.repo.tables["api_flow_scenarios"].values()
                     if row["name"] == "permission-convert")
        case_id = scene["data"]["nodes"]["convert"]["case_id"]
        external = self.put("execution_flows", 40000, data={"nodes": [{"case_id": case_id}]})
        result = importlib.import_module("waiqin_stock_cleanup").remove_permissions(self.repo, self.output, manifest)
        self.assertIn(case_id, result["preserved_case_ids"])
        self.assertIsNotNone(self.repo.get("api_test_cases", case_id))
        self.assertEqual(self.repo.get("execution_flows", 40000), external)

    def test_preparation_uses_purchase_and_never_inventory_upsert_or_resubmit(self):
        for plan in self.plans:
            for scene in plan["scenes"]:
                self.assertFalse(any(step["api_id"] in {12193, 12203} for step in scene["nodes"]))
        server = StockHTTP()
        server.products[2001] = {"productId": 2001}
        response = server.dispatch(12193, {"body": {"productId": 2001, "quantity": 10}, "query": {}, "headers": {}}, "230")
        self.assertEqual(response["code"], 500)
        self.assertNotIn(2001, server.stock)


if __name__ == "__main__":
    unittest.main()
