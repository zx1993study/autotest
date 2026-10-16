import json
import unittest
from copy import deepcopy

from app.core.exceptions import BusinessRuleError
from app.scheduler.jobs.api_case_executor import ApiCaseExecutor
from app.schemas.api_add_campaign import ApiAddCampaignRequest
from app.services.api_add_case_generation_service import ApiAddCaseGenerationService
from app.services.api_case_template_builder import ApiCaseTemplateBuilder
from app.services.api_natural_input_service import timestamp_text
from tests.test_openapi_case_generation import FakeResourceRepository


class AddCampaignTest(unittest.TestCase):
    def setUp(self):
        self.repository = FakeResourceRepository()
        self.snapshot = self.repository.create("api_schema_snapshots", {
            "project_id": 10, "data": {"schema_hash": "snapshot-hash", "schema": {}}})
        self.interface = self.repository.create("api_interfaces", {
            "name": "Add Product", "project_id": 10,
            "data": {"method": "POST", "path": "/business/product", "schema_snapshot_id": self.snapshot["id"],
                     "security": [{"bearerAuth": []}]}})
        for name, schema, required in [
            ("productName", {"type": "string"}, True),
            ("unit", {"type": "string", "enum": ["瓶", "件"]}, False),
            ("customerName", {"type": "string"}, False),
            ("visitDate", {"type": "string", "format": "date-time"}, False),
            ("productId", {"type": "integer"}, False),
        ]:
            self.repository.create("api_fields", {"name": name, "project_id": 10,
                "data": {"name": name, "interface_id": self.interface["id"], "location": "body",
                         "schema": schema, "field_type": schema["type"], "required": required}})
        self.payload = ApiAddCampaignRequest(project_id=10, snapshot_id=self.snapshot["id"], campaign_key="add-check",
            profiles=[{"source_id": self.interface["id"], "table_name": "product",
                       "params": {"productName": "晨露矿泉水", "unit": "瓶", "customerName": "关联门店",
                                  "visitDate": "2026-10-16T10:00:00"},
                       "unique_text_fields": ["productName"], "required_fields": ["productName"],
                       "field_constraints": {"productName": {"maxLength": 50, "minLength": 1}},
                       "excluded_fields": ["productId"]}])
        self.service = ApiAddCaseGenerationService(self.repository)

    def test_verified_baseline_and_business_assertions(self):
        cases = self.service.generate(self.payload)
        normal = next(case for case in cases if case["data"]["openapi_scenario"]["strategy"] == "normal")
        params = normal["data"]["params"]
        self.assertIn("{{timestamp_ms}}", params["productName"])
        self.assertNotIn("productId", params)
        self.assertEqual(params["unit"], "瓶")
        self.assertEqual(params["customerName"], "关联门店")
        self.assertEqual(params["visitDate"], "2026-10-16T10:00:00")
        self.assertEqual(normal["assertions"], [{"type": "status", "expected": 200},
                                              {"type": "json_pointer", "path": "/code", "expected": 200}])
        self.assertEqual(normal["data"]["input_baseline"]["schema_hash"], "snapshot-hash")
        auth = next(case for case in cases if case["data"]["openapi_scenario"]["strategy"] == "auth")
        self.assertTrue(auth["data"]["skip_auth"])
        self.assertEqual(auth["assertions"], [{"type": "api_rejection", "expected": "auth"}])

    def test_mutated_field_is_not_replaced_by_unique_name(self):
        cases = self.service.generate(self.payload)
        missing = next(case for case in cases if case["data"]["openapi_scenario"]["strategy"] == "required")
        self.assertNotIn("productName", missing["data"]["params"])
        invalid = next(case for case in cases if case["data"]["openapi_scenario"]["key"] ==
                       "type:body.productName:invalid")
        self.assertNotIsInstance(invalid["data"]["params"]["productName"], str)
        self.assertEqual(invalid["assertions"][0]["type"], "api_rejection")

    def test_rerun_updates_only_owned_cases(self):
        unrelated = self.repository.create("api_test_cases", {"project_id": 10, "name": "Existing case", "data": {}})
        first = self.service.generate(self.payload)
        second = self.service.generate(self.payload)
        self.assertEqual([row["id"] for row in first], [row["id"] for row in second])
        self.assertEqual(self.repository.get("api_test_cases", unrelated["id"]), unrelated)
        self.assertEqual(len(self.repository.tables["api_test_cases"]), len(first) + 1)

    def test_invalid_scope_is_rejected_before_writes(self):
        for change in [{"method": "GET"}, {"schema_snapshot_id": 999}]:
            with self.subTest(change=change):
                original = deepcopy(self.interface["data"])
                self.interface["data"].update(change)
                with self.assertRaises(BusinessRuleError):
                    self.service.generate(self.payload)
                self.interface["data"] = original
        self.assertNotIn("api_test_cases", self.repository.tables)

    def test_unknown_or_excluded_input_is_rejected(self):
        self.payload.profiles[0].params["productId"] = 1
        with self.assertRaises(BusinessRuleError):
            self.service.generate(self.payload)
        self.assertNotIn("api_test_cases", self.repository.tables)

    def test_timestamp_fits_and_scenarios_have_distinct_names(self):
        first = timestamp_text("自然添加名称" * 10, 30, "case-1")
        second = timestamp_text("自然添加名称" * 10, 30, "case-2")
        self.assertNotEqual(first, second)
        self.assertEqual(len(first.replace("{{timestamp_ms}}", "1791969556508")), 30)
        with self.assertRaises(ValueError):
            timestamp_text("名称", 10, "case")

    def test_legacy_builder_remains_usable(self):
        cases = ApiCaseTemplateBuilder().build(self.interface, [], "normal", [])
        self.assertEqual(cases[0]["name"], "[正常]")

    def test_removed_inputs_deactivate_only_obsolete_owned_scenarios(self):
        first = self.service.generate(self.payload)
        unit_cases = [case for case in first if case["data"]["openapi_scenario"]["field"] == "body.unit"]
        self.payload.profiles[0].params.pop("unit")
        second = self.service.generate(self.payload)
        self.assertTrue(unit_cases)
        self.assertTrue(all(case["status"] == "inactive" for case in unit_cases))
        self.assertTrue(all(case["status"] == "active" for case in second))

    def test_array_boundary_retains_verified_reference_ids(self):
        field = {"name": "items", "data": {"name": "items", "location": "body", "field_type": "array",
                 "schema": {"type": "array", "minItems": 1, "items": {"type": "object",
                            "properties": {"productId": {"type": "integer"}}}}}}
        baseline = {"params": {"items": [{"productId": 935, "quantity": 1}]}}
        cases = ApiCaseTemplateBuilder().build_from_openapi(self.interface, [field], {"boundary"},
                                                           normal_request=baseline)
        valid = next(case for case in cases if case["openapi_scenario"]["variant"] == "min-items-valid")
        invalid = next(case for case in cases if case["openapi_scenario"]["variant"] == "min-items-invalid")
        self.assertEqual(valid["params"]["items"], [{"productId": 935, "quantity": 1}])
        self.assertEqual(invalid["params"]["items"], [])
        valid["params"]["items"][0]["productId"] = 1
        self.assertEqual(baseline["params"]["items"][0]["productId"], 935)


class RejectionAssertionTest(unittest.TestCase):
    def test_only_explicit_business_messages_allow_code_500(self):
        executor = ApiCaseExecutor(FakeResourceRepository())
        assertion = {"type": "api_rejection", "expected": "validation",
                     "allowed_business_errors": ["活动类型名称不能为空", "IntegrityError"]}
        for message, expected in [("活动类型名称不能为空", True), ("审批失败", False), ("IntegrityError", False)]:
            result = executor._assert_response([assertion], 200, {}, 10, json.dumps({"code": 500, "msg": message}))
            self.assertEqual(result[0]["passed"], expected)

    def test_validation_rejections_and_internal_failures(self):
        executor = ApiCaseExecutor(FakeResourceRepository())
        for status, response, expected, passed in [
            (422, {"detail": []}, "validation", True),
            (200, {"code": 400, "msg": "参数不合法"}, "validation", True),
            (200, {"code": 200}, "validation", False),
            (200, {}, "validation", False),
            (500, {"code": 500}, "validation", False),
            (200, {"code": 500, "msg": "invalid keyword argument for Warehouse"}, "validation", False),
            (400, {"msg": "pymysql IntegrityError"}, "validation", False),
            (401, {}, "auth", True),
            (200, {"code": 403}, "auth", True),
            (422, {}, "auth", False),
            (401, {}, "validation", False),
        ]:
            with self.subTest(status=status, response=response, expected=expected):
                result = executor._assert_response([{"type": "api_rejection", "expected": expected}],
                                                   status, {}, 10, json.dumps(response))
                self.assertEqual(result[0]["passed"], passed)


if __name__ == "__main__":
    unittest.main()
