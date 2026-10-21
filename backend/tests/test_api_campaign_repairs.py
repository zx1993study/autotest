import importlib
import sys
import tempfile
import unittest
from pathlib import Path

from tests.test_api_flows import MemoryRepository


class CampaignRepairsTest(unittest.TestCase):
    def setUp(self):
        path = str(Path(__file__).resolve().parents[2] / "scripts")
        sys.path.insert(0, path)
        self.addCleanup(lambda: sys.path.remove(path))
        self.staging = importlib.import_module("api_campaign_staging")
        self.isolation = importlib.import_module("waiqin_regression_isolation")
        self.data = importlib.import_module("waiqin_regression_data_repair")

    def test_order_rebase_preserves_invalid_and_missing_fields(self):
        baseline = {"items": [{"productId": 0, "quantity": 1}], "warehouseId": 230}
        for params in ({"items": []}, {"items": {"not": "array"}}):
            case = {"data": {"params": params, "openapi_scenario": {"field": "body.items"}}}
            result = self.isolation.rebase_order_case(case, baseline)
            self.assertEqual(result["items"], params["items"])
            self.assertEqual(result["warehouseId"], 230)
        case = {"data": {"params": {}, "openapi_scenario": {"field": "body.warehouseId"}}}
        self.assertNotIn("warehouseId", self.isolation.rebase_order_case(case, baseline))

    def test_valid_item_boundary_does_not_reuse_historical_product(self):
        case = {"data": {"params": {"items": [{"productId": 16}]},
                         "openapi_scenario": {"field": "body.items"}}}
        result = self.isolation.rebase_order_case(case, {"items": [{"productId": 0, "quantity": 1}]})
        self.assertEqual(result["items"], [{"productId": 0, "quantity": 1}])

    def test_rebased_parameters_cannot_resurrect_legacy_body_targets(self):
        definitions = importlib.import_module("waiqin_regression_definitions")
        original = {"body": {"nodeInstanceId": 1, "approveResult": "1"},
                    "request": {"body": {"nodeInstanceId": 1}, "params": {"nodeInstanceId": 1},
                                "skip_auth": True}, "auth_id": 10015}
        actual = definitions.canonical_params(original, {"approveResult": -999999})
        self.assertEqual(actual["body"], {})
        self.assertEqual(actual["params"], {"approveResult": -999999})
        self.assertEqual(actual["request"], {"skip_auth": True})
        self.assertEqual(original["body"]["nodeInstanceId"], 1)

    def test_staging_does_not_write_and_rejects_concurrent_config_edits(self):
        repo = MemoryRepository()
        before = repo.create("api_test_cases", {"name": "original", "project_id": 10, "data": {}})
        staged = self.staging.StagingRepository({"api_test_cases": [before]}, repo)
        staged.update("api_test_cases", before["id"], {"name": "repaired"})
        self.assertEqual(repo.get("api_test_cases", before["id"])["name"], "original")
        repo.update("api_test_cases", before["id"], {"name": "human edit"})
        with tempfile.TemporaryDirectory() as folder, self.assertRaisesRegex(ValueError, "changed after planning"):
            self.staging.apply_changes(repo, staged.changes(), Path(folder))
        self.assertEqual(repo.get("api_test_cases", before["id"])["name"], "human edit")

    def test_auth_repair_preserves_deliberate_no_auth_and_existing_role(self):
        repo = MemoryRepository()
        repo.tables["project_auth"] = {10015: {"id": 10015, "project_id": 10, "status": "active"}}
        for case_id, data in ((1, {"skip_auth": True}), (2, {"auth_id": 16307}), (3, {})):
            repo.tables.setdefault("api_test_cases", {})[case_id] = {
                "id": case_id, "source_id": 12102, "project_id": 10, "data": data}
        result = self.data.repair_auth(repo, [{"id": i} for i in (1, 2, 3)])
        self.assertEqual(result, [3])
        self.assertTrue(repo.get("api_test_cases", 1)["data"]["skip_auth"])
        self.assertEqual(repo.get("api_test_cases", 2)["data"]["auth_id"], 16307)


if __name__ == "__main__":
    unittest.main()
