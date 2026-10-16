import importlib.util
import json
import sys
import unittest
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.schemas.api_add_campaign import ApiAddCampaignRequest


class AddCampaignScriptsTest(unittest.TestCase):
    def setUp(self):
        self.scripts = Path(__file__).resolve().parents[2] / "scripts"
        sys.path.insert(0, str(self.scripts))
        self.addCleanup(lambda: sys.path.remove(str(self.scripts)))
        self.profiles = self.load("waiqin_add_profiles")
        self.database = self.load("api_add_database")
        self.report = self.load("api_add_report")

    def load(self, name):
        spec = importlib.util.spec_from_file_location(f"campaign_test_{name}", self.scripts / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def fixtures(self, apply_fields=None):
        return {"now": datetime(2026, 10, 14, 10, 0),
                "customer": {"customer_id": 21, "customer_name": "关联门店", "customer_type": "1"},
                "direct": {"customer_id": 22},
                "supervision_customer": {"customer_id": 23, "customer_name": "已审核门店", "customer_type": "1"},
                "user": {"user_id": 1, "nick_name": "负责人"},
                "stock": {"product_id": 935, "product_name": "商品", "warehouse_id": 31, "warehouse_name": "仓库",
                          "terminal_wholesale_price": Decimal("300.00")},
                "activity": {"activity_id": 51, "activity_type": "dish_cultivate"},
                "templates": {"apply": [], "execute": [], "payment": []}, "image": "https://example.com/photo.png",
                "apply_fields": apply_fields or [{"field_code": "customers", "is_required": "0"}]}

    def test_apply_inputs_follow_actual_template_and_date_parser(self):
        params, names = self.profiles.normal_inputs(self.fixtures())[12126]
        self.assertEqual(set(params), {"activityId", "customers", "startTime", "endTime"})
        self.assertEqual(names, [])
        self.assertEqual(params["startTime"], "2026-10-16 10:00:00")
        self.assertEqual(params["customers"][0]["customerId"], 21)

    def test_configured_apply_fields_are_not_discarded(self):
        fixtures = self.fixtures([{"field_code": "customers", "is_required": "1"},
                                  {"field_code": "expectedParticipants", "is_required": "1"},
                                  {"field_code": "remark", "is_required": "0"}])
        params, names = self.profiles.normal_inputs(fixtures)[12126]
        self.assertEqual(params["expectedParticipants"], 5)
        self.assertEqual(names, ["remark"])
        self.assertNotIn("estimatedMealFee", params)

    def test_normal_return_totals_and_server_generated_codes(self):
        inputs = self.profiles.normal_inputs(self.fixtures())
        params = inputs[12221][0]
        self.assertEqual(params["order"]["totalAmount"], 300)
        self.assertEqual(params["order"]["totalQuantity"], params["items"][0]["returnQuantity"])
        self.assertNotIn("warehouseCode", inputs[12186][0])
        self.assertNotIn("productCode", inputs[12102][0])
        self.assertNotIn("orderNo", inputs[12199][0])

    def test_database_never_falls_back_to_write_credentials(self):
        with patch.object(self.database, "dotenv_values", return_value={"DB_USERNAME": "writer"}), \
                patch.object(self.database, "create_engine") as create_engine:
            with self.assertRaises(ValueError), self.database.business_connection("unused.env"):
                pass
            create_engine.assert_not_called()

    def test_non_select_statements_are_rejected(self):
        connection = Mock()
        for query in ["UPDATE product SET status='0'", "SELECT 1; DELETE FROM product"]:
            with self.assertRaises(ValueError):
                self.database.select_rows(connection, query)
        connection.execute.assert_not_called()

    def test_reports_do_not_include_authentication_headers(self):
        case = {"id": 1, "source_id": 2, "name": "normal", "data": {"openapi_generation": {"fingerprint": "fp"}}}
        record = {"id": 3, "status": "success", "data": {"request": {
            "headers": {"Authorization": "private-bearer"}, "body": {"name": "normal"}},
            "response_body": '{"code":200,"msg":"ok"}', "response_status": 200}}
        result = self.report.execution_summary(case, record)
        self.assertNotIn("private-bearer", json.dumps(result))
        self.assertNotIn("headers", result)
        self.assertEqual(result["case_fingerprint"], "fp")

    def test_snapshot_scope_is_checked(self):
        runner = self.load("api_add_campaign")
        payload = ApiAddCampaignRequest(project_id=10, snapshot_id=11, campaign_key="test",
                                        profiles=[{"source_id": 1, "table_name": "warehouse", "params": {}}])
        with self.assertRaises(ValueError):
            runner._scope(SimpleNamespace(project_id=10, snapshot_id=99, campaign="test"), payload)


if __name__ == "__main__":
    unittest.main()
