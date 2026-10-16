import importlib
import json
import unittest
from unittest.mock import patch

from app.scheduler.jobs.api_case_executor import ApiCaseExecutor
from tests import test_api_stock_campaign as campaign_tests
from tests.api_stock_fixtures import StockHTTP


class StockExecutionTest(unittest.TestCase):
    def setUp(self):
        self.harness = campaign_tests.StockCampaignTest()
        self.harness.setUp()
        self.addCleanup(self.harness.doCleanups)
        self.repo = self.harness.repo
        self.manifest = self.harness.generate()
        self.module = importlib.import_module("waiqin_stock_execute")
        self.repo.tables["projects"][10]["data"]["base_url"] = "https://test.waiqin.yios.cn/"
        self.output = self.harness.output / "execution"

    def run_with(self, keys, server, sender=None):
        auth = {10015: "Bearer private-reviewer", 16306: "Bearer private-creator", 16307: "Bearer private-outsider"}
        with patch.object(self.module, "verify_live_auth"), patch(
            "app.services.api_flow_snapshot_service.ProjectAuthService.auth_headers", side_effect=lambda aid: {"Authorization": auth[aid]}
        ), patch.object(ApiCaseExecutor, "_send_http_request", side_effect=sender or server.send):
            return self.module.execute(self.repo, self.manifest, self.output, keys)

    def test_test_host_and_enabled_scene_prechecks_run_before_http(self):
        for host, keys in (("https://production.invalid", {"unpack"}), ("https://test.waiqin.yios.cn", {"convert_wrong_user"})):
            with self.subTest(host=host, keys=keys), patch.object(ApiCaseExecutor, "_send_http_request") as send:
                self.repo.tables["projects"][10]["data"]["base_url"] = host
                with self.assertRaises(ValueError):
                    self.module.execute(self.repo, self.manifest, self.output, keys)
                send.assert_not_called()
        self.assertNotIn("api_flow_runs", self.repo.tables)

    def test_completed_execution_is_persisted_and_secrets_are_masked(self):
        server = StockHTTP()
        state = self.run_with({"unpack"}, server)
        self.assertEqual((state["passed"], state["failed"], state["blocked"]), (1, 0, []))
        info = state["results"][0]
        run = self.repo.get("api_flow_runs", info["batch_id"])
        self.assertEqual(run["status"], "success")
        scene = self.repo.get("api_flow_scenarios", info["scenario_id"])
        self.assertEqual(scene["data"]["latest_run_id"], info["batch_id"])
        self.assertEqual(scene["data"]["latest_status"], "success")
        for path in self.output.glob("*.json"):
            self.assertNotIn("private-", path.read_text(encoding="utf-8"))
        self.assertEqual(server.stock[5], {"quantity": 200, "lockedQuantity": 20})

    def test_shared_purchase_failure_blocks_other_dependent_scenes(self):
        server = StockHTTP()
        def send(request):
            if "/12199" in request["path"]:
                return 200, {}, json.dumps({"code": 500, "msg": "Purchase unavailable"})
            return server.send(request)
        state = self.run_with({"sales_over_stock", "unpack"}, server, send)
        self.assertEqual((state["passed"], state["failed"], len(state["blocked"])), (0, 1, 1))
        self.assertEqual(state["results"][0]["failure"]["node"], "product_seed_create")
        self.assertEqual(len(self.repo.tables["api_flow_runs"]), 1)
        self.assertFalse(any("/12195" in row["path"] for row in server.calls))

    def test_read_only_evidence_separates_inventory_and_assertion_failures(self):
        evidence = importlib.import_module("waiqin_stock_evidence")
        info = {"status": "failed", "inputs": {"stock_scene_key": "sales_approve"}, "failure": {
            "node": "sales_verify_detail", "http_status": 200, "business_code": 200,
            "assertions": [{"actual": "5", "expected": "3"}]}}
        self.assertEqual(evidence.category(info), "sales_auto_shipping_expectation")
        info["inputs"]["stock_scene_key"] = "sales_qty_negative"
        self.assertEqual(evidence.category(info), "invalid_sales_quantity_accepted")
        self.assertTrue(evidence.unchanged({"quantity": "10.0", "locked_quantity": "0"},
                                           {"quantity": "10.00", "locked_quantity": "0.00"}))
        self.assertFalse(evidence.unchanged(None, {"quantity": 0, "locked_quantity": 0}))
        result = {"inputs": {"record_marker": "owned"}, "nodes": [
            {"key": "product_locate", "status": "success", "outputs": {"product_id": 99}},
            {"key": "inventory_before", "status": "success", "request": {
                "path": "/warehouse/230/inventory", "query": {"productId": 99}}, "response_body": '{"rows": []}'},
            {"key": "convert", "status": "failed"},
            {"key": "inventory_final", "status": "skipped"}]}
        self.assertEqual(evidence.baseline(result), ({"product": 99}, {99: None}, {"owned"}))


if __name__ == "__main__":
    unittest.main()
