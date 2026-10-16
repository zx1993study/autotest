import json
import unittest
from threading import Event

from pydantic import ValidationError

from app.schemas.execution_flow import FlowBinding, FlowExtract, FlowNode
from app.services.api_flow_runner import ApiFlowRunner
from app.services.api_flow_values import (
    EvidenceMask,
    apply_request_override,
    bind_value,
    response_value,
)
from tests import test_api_flows as flow_fixtures


class FlowParameterValuesTest(unittest.TestCase):
    def test_automatic_binding_preserves_native_type_and_prefers_api_params(self):
        request = {"params": {"ids": []}, "body": {"ids": "legacy"}}
        binding = FlowBinding(source="previous", name="result", target="auto", target_name="ids").model_dump()
        bind_value(request, binding, {"previous": {"result": [12, 34]}})
        self.assertEqual(request["params"]["ids"], [12, 34])
        self.assertEqual(request["body"]["ids"], "legacy")

    def test_automatic_binding_resolves_nested_fields_and_new_api_params(self):
        binding = FlowBinding(source="previous", name="result", target="auto", target_name="id").model_dump()
        request = {"body": {"customer": {"id": None}}}
        bind_value(request, binding, {"previous": {"result": 7}})
        self.assertEqual(request["body"]["customer"]["id"], 7)
        request = {}
        bind_value(request, binding, {"previous": {"result": 8}})
        self.assertEqual(request["params"]["id"], 8)

    def test_ambiguous_automatic_binding_fails_without_modifying_fields(self):
        request = {"body": {"first": {"id": 1}, "second": {"id": 2}}}
        binding = FlowBinding(source="previous", name="result", target="auto", target_name="id").model_dump()
        with self.assertRaisesRegex(ValueError, "存在多个同名字段"):
            bind_value(request, binding, {"previous": {"result": 9}})
        self.assertEqual(request["body"], {"first": {"id": 1}, "second": {"id": 2}})

    def test_legacy_binding_keeps_exact_target_and_prefix(self):
        request = {"headers": {}}
        binding = FlowBinding(source="previous", name="token", target="headers", path="/Authorization", prefix="Bearer ").model_dump()
        bind_value(request, binding, {"previous": {"token": "test-token"}})
        self.assertEqual(request["headers"]["Authorization"], "Bearer test-token")

    def test_multiple_exact_paths_preserve_order_and_types(self):
        response = {"body": json.dumps({"data": {"ids": [12, 34], "enabled": False, "customer": {"id": 7}}})}
        extraction = FlowExtract(name="values", mode="array", paths=["/data/ids/1", "/data/enabled", "/data/customer", "/data/ids"]).model_dump()
        self.assertEqual(response_value(response, extraction), [34, False, {"id": 7}, [12, 34]])
        self.assertIsNone(response_value(response, FlowExtract(name="id", path="/missing").model_dump()))

    def test_request_layers_support_removal_then_scenario_replacement(self):
        request = {"params": {"id": 1, "phone": "old", "a/b~c": 3}, "body": {"old": True}}
        apply_request_override(request, {"params": {"id": 2}, "request": {"body": [1, False]},
                                         "request_removals": ["/params/phone", "/params/a~1b~0c"]})
        apply_request_override(request, {"params": {"id": 4, "phone": None}})
        self.assertEqual(request, {"params": {"id": 4, "phone": None}, "body": [1, False]})

    def test_sensitive_array_members_are_masked_in_evidence(self):
        mask = EvidenceMask({})
        mask.add(["secret-one", {"nested": "secret-two"}])
        cleaned = mask.clean({"outputs": {"values": ["secret-one", "secret-two"]}})
        self.assertEqual(cleaned["outputs"]["values"], ["***", "***"])

    def test_invalid_binding_array_and_removal_configuration_are_rejected(self):
        with self.assertRaises(ValidationError):
            FlowBinding(name="id", target="auto", target_name=" ")
        with self.assertRaises(ValidationError):
            FlowExtract(name="ids", mode="array", paths=[])
        with self.assertRaises(ValidationError):
            FlowExtract(name="ids", mode="array", paths=[""])
        with self.assertRaises(ValidationError):
            FlowNode(key="query", name="Query", api_id=1, request_removals=["/assertions"])


class FlowParameterExecutionTest(unittest.TestCase):
    setUpClass = classmethod(flow_fixtures.ApiFlowsTest.setUpClass.__func__)
    tearDownClass = classmethod(flow_fixtures.ApiFlowsTest.tearDownClass.__func__)
    setUp = flow_fixtures.ApiFlowsTest.setUp
    snapshot = flow_fixtures.ApiFlowsTest.snapshot

    def test_array_outputs_are_sent_to_one_downstream_parameter(self):
        snapshot = self.snapshot()
        create, delete = snapshot["flow"]["data"]["nodes"][1:]
        create["extracts"] = [FlowExtract(name="ids", mode="array", paths=["/data/id", "/code"]).model_dump()]
        delete["bindings"] = [FlowBinding(source="create", name="ids", target="auto", target_name="id").model_dump()]
        result = ApiFlowRunner(snapshot, Event()).run()
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["nodes"][1]["outputs"]["ids"], [123, 0])
        self.assertEqual(result["nodes"][2]["request"]["body"]["id"], [123, 0])

    def test_required_array_fails_for_any_missing_path(self):
        snapshot = self.snapshot()
        node = snapshot["flow"]["data"]["nodes"][1]
        node["extracts"] = [FlowExtract(name="id", mode="array", paths=["/data/id", "/data/missing"]).model_dump()]
        result = ApiFlowRunner(snapshot, Event()).run()
        self.assertEqual(result["nodes"][1]["status"], "failed")
        self.assertIn("未提取到变量 id", result["nodes"][1]["error"])

    def test_optional_array_retains_missing_positions(self):
        snapshot = self.snapshot()
        node = snapshot["flow"]["data"]["nodes"][1]
        node["extracts"] = [FlowExtract(name="id", mode="array", required=False, paths=["/data/id", "/data/missing"]).model_dump()]
        result = ApiFlowRunner(snapshot, Event()).run()
        self.assertEqual(result["nodes"][1]["outputs"]["id"], [123, None])
        self.assertEqual(result["nodes"][2]["request"]["body"]["id"], [123, None])


if __name__ == "__main__":
    unittest.main()
