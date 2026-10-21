import importlib
import json
import unittest
from copy import deepcopy
from threading import Event
from unittest.mock import patch

from app.services.api_flow_preparation_service import ApiFlowPreparationService
from app.services.api_flow_runner import ApiFlowRunner
from app.services.api_flow_scenario_service import ApiFlowScenarioService
from app.services.execution_flow_service import ExecutionFlowService
from tests import test_api_approval_campaign as approval_fixtures
from tests.api_approval_fixtures import ApprovalHTTP


class CustomerStatusApprovalTest(unittest.TestCase):
    def setUp(self):
        fixture = approval_fixtures.ApprovalCampaignTest()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.generate()
        self.repo = fixture.repo
        self.builder = fixture.builder
        self.module = importlib.import_module("waiqin_customer_status")
        self.approval = ExecutionFlowService(self.repo).get(11775)
        source = {node["key"]: node for node in self.approval["data"]["nodes"]}
        create, locate = deepcopy(source["terminal_create"]), deepcopy(source["terminal_locate"])
        create["key"], locate["key"] = "create", "locate"
        fixture.put("api_interfaces", 12099, data={"method": "PUT", "path": "/fixture/12099"})
        status_case = self.repo.create("api_test_cases", {"name": "Disable newly approved customer", "project_id": 10,
            "source_id": 12099, "data": {"params": {"customerType": "1", "status": "2"}},
            "assertions": [{"type": "status", "expected": 200}, {"type": "json_pointer", "path": "/code", "expected": 200}]})
        verify_case = self.repo.create("api_test_cases", {"name": "Verify disabled customer", "project_id": 10,
            "source_id": 12098, "data": {}, "assertions": [{"type": "status", "expected": 200},
                {"type": "json_pointer", "path": "/code", "expected": 200},
                {"type": "json_pointer", "path": "/data/customerId", "expected": "{{bound_owned_id}}"},
                {"type": "json_pointer", "path": "/data/status", "expected": "2"}]})
        binding = {"source": "locate", "name": "owned_id", "target": "params", "path": "/customerId"}
        nodes = [create, locate,
            {"key": "change_status", "name": "Disable", "api_id": 12099, "case_id": status_case["id"],
             "auth_id": 10015, "bindings": [binding]},
            {"key": "verify_status", "name": "Verify", "api_id": 12098, "case_id": verify_case["id"],
             "auth_id": 10015, "bindings": [{**binding, "path": "/customer_id"}]}]
        self.flow = ExecutionFlowService(self.repo).create({"name": "Customer", "project_id": 10,
            "data": {"inputs": {"record_marker": "New customer_{{timestamp_ms}}_{{random_digits:6}}"}, "nodes": nodes}})
        self.scene = ApiFlowScenarioService(self.repo).create_for_flow(self.flow["id"], {"name": "Customer status"})

    def configured(self):
        definition = self.module.status_flow_definition(self.flow, self.approval)
        flow = ExecutionFlowService(self.repo).update(self.flow["id"], {"data": definition})
        self.flow = flow
        service = ApiFlowScenarioService(self.repo)
        scene = service.sync(flow["id"], self.scene["id"])
        scene = service.update_for_flow(flow["id"], scene["id"], {"data": self.module.status_scenario_data(flow, scene)})
        return flow, scene

    def run_scene(self, fault=""):
        flow, scene = self.configured()
        snapshot = ApiFlowPreparationService(self.repo).build(flow, [scene], {})[0]
        server = ApprovalHTTP(self.builder.BUSINESSES, fault)
        changes = []
        def send(request):
            if request["path"] == "/fixture/12099":
                customer = server.records["terminal"]
                self.assertEqual(customer["status"], "1")
                self.assertEqual(customer["customerId"], request["body"]["customerId"])
                self.assertEqual(request["body"]["status"], "2")
                changes.append(deepcopy(request))
                customer["status"] = "2"
                return 200, {}, '{"code":200}'
            status, headers, body = server.send(request)
            if fault == "missing_instance" and request["path"].startswith("/fixture/12098"):
                payload = json.loads(body)
                payload.pop("approvalProcess", None)
                body = json.dumps(payload)
            return status, headers, body
        runner = ApiFlowRunner(snapshot, Event())
        with patch.object(runner.executor, "_send_http_request", side_effect=send):
            result = runner.run()
        return result, server, changes

    def test_approval_completes_before_customer_is_disabled(self):
        result, server, changes = self.run_scene()
        self.assertEqual(result["status"], "success", result)
        self.assertEqual(result["path"], ["create", "locate", *self.module.STATUS_APPROVAL_KEYS.values(),
                                          "change_status", "verify_status"])
        self.assertEqual(len(changes), 1)
        self.assertEqual(server.records["terminal"]["status"], "2")
        self.assertEqual(result["expected_end"], "verify_status")

    def test_invalid_approval_evidence_never_reaches_status_change(self):
        for fault in ("wrong_business", "wrong_approver", "not_current", "auto_skipped", "multiple_nodes", "missing_instance"):
            with self.subTest(fault=fault):
                result, server, changes = self.run_scene(fault)
                self.assertEqual(result["status"], "failed")
                self.assertEqual(changes, [])
                self.assertFalse(any(request["path"] == "/fixture/12182" for request in server.calls))

    def test_wrong_status_after_approval_stops_before_disabling(self):
        result, _server, changes = self.run_scene("wrong_final_status")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(changes, [])
        self.assertEqual(result["nodes"][6]["key"], "status_approval_verify_detail")
        self.assertEqual(result["nodes"][6]["status"], "failed")

    def test_patch_is_idempotent_preserves_source_and_skips_unrelated_nodes(self):
        original = deepcopy(self.approval)
        flow, scene = self.configured()
        self.assertEqual(self.module.status_flow_definition(flow, self.approval), flow["data"])
        self.assertEqual(self.approval, original)
        flow["data"]["nodes"].append({**flow["data"]["nodes"][0], "key": "unrelated"})
        data = self.module.status_scenario_data(flow, scene)
        self.assertEqual(data["nodes"]["unrelated"], {"mode": "skip"})
        self.assertEqual(data["inputs"]["decision"], "1")
        self.assertEqual(data["inputs"]["business_status"], "1")
        with self.assertRaises(ValueError):
            self.module.status_flow_definition(flow, {**self.approval, "project_id": 99})


if __name__ == "__main__":
    unittest.main()
