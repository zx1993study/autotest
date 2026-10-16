import copy
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from app.core.exceptions import BusinessRuleError, ResourceNotFoundError
from app.schemas.web_features import WebFeatureSave
from app.services.agent_task_service import AgentTaskService
from app.services.web_feature_testing_service import VERSIONS, WebFeatureTestingService
from app.services.web_page_management_service import WebPageManagementService
from app.services.web_vision_discovery_service import FeatureCapture
from pydantic import ValidationError
from test_web_page_management_service import FakeResourceRepository
from web_automation.compiler import ExecutionPlanCompiler


class WebFeatureTestingTest(unittest.TestCase):
    def setUp(self):
        self.repo = FakeResourceRepository()
        self.repo.rows = {}
        self.group = WebPageManagementService(self.repo).create_group({"name": "Customers", "project_id": 1, "url": "https://example.test/customers"})
        self.service = WebFeatureTestingService(self.repo)
        self.parameter = {"key": "name", "label": "Name", "type": "text", "required": True, "default_value": "Default"}
        self.feature = self.service.save_feature(self.group["id"], {"name": "Add customer", "feature_type": "add", "parameters": [self.parameter]})
        self.candidate = {"name": "Add customer", "input_info": {"name": "Default"}, "steps": [
            {"name": "Name", "action": "fill", "locator_type": "label", "locator": "Name", "value": "{{name}}"},
            {"name": "Verify", "action": "assert", "locator_type": "text", "locator": "Ready", "expected": "Ready"}]}
        self.version = self.service.save_version(self.feature["id"], self.candidate)

    def test_feature_input_cases_are_scoped_and_versioned(self):
        case = self.service.save_case(self.feature["id"], {"name": "Case one", "input_info": {"name": "First"}})
        changed = copy.deepcopy(self.candidate)
        changed["steps"][0]["locator"] = "Customer name"
        new = self.service.save_version(self.feature["id"], changed)
        self.assertNotEqual(self.version["id"], new["id"])
        self.assertEqual(self.version["id"], case["data"]["script_version"])
        self.assertEqual("Name", case["steps"][0]["locator"])
        self.assertEqual("First", case["data"]["request"]["variables"]["name"])
        compiled = ExecutionPlanCompiler().compile({"cases": [case]})
        self.assertNotIn("_dynamic_error", compiled.cases[0].raw)
        self.assertEqual("First", compiled.cases[0].steps[0]["value"])

    def test_copy_is_a_new_case_and_does_not_change_original(self):
        first = self.service.save_case(self.feature["id"], {"name": "Original", "input_info": {"name": "First"}})
        second = self.service.save_case(self.feature["id"], {"name": "Copy", "input_info": {"name": "Second"}})
        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual("First", first["data"]["input_info"]["name"])

    def test_invalid_candidate_does_not_modify_feature(self):
        revision = self.service.feature(self.feature["id"])["data"]["revision"]
        with self.assertRaises(BusinessRuleError):
            self.service.save_feature(self.group["id"], {"name": "Changed", "candidate": {"name": "Bad", "steps": []}}, self.feature["id"])
        self.assertEqual("Add customer", self.service.feature(self.feature["id"])["name"])
        self.assertEqual(revision, self.service.feature(self.feature["id"])["data"]["revision"])

    def test_revision_conflict_and_foreign_auth_are_rejected(self):
        with self.assertRaises(BusinessRuleError):
            self.service.save_feature(self.group["id"], {"name": "Changed", "expected_revision": 0}, self.feature["id"])
        auth = self.repo.create("project_auth", {"name": "Foreign", "project_id": 2})
        with self.assertRaises(BusinessRuleError):
            self.service.save_feature(self.group["id"], {"name": "Changed", "auth_id": auth["id"]}, self.feature["id"])

    def test_case_and_version_cannot_be_used_across_features(self):
        other = self.service.save_feature(self.group["id"], {"name": "Other"})
        case = self.service.save_case(self.feature["id"], {"name": "Case"})
        with self.assertRaises(ResourceNotFoundError):
            self.service.delete_case(other["id"], case["id"])
        with self.assertRaises(BusinessRuleError):
            self.service.activate_version(other["id"], self.version["id"])

    def test_expected_results_cannot_add_business_actions(self):
        with self.assertRaises(BusinessRuleError):
            self.service.save_case(self.feature["id"], {"name": "Bad", "expected_steps": [{"action": "click"}]})
        with self.assertRaises(BusinessRuleError):
            self.service.save_case(self.feature["id"], {"name": "Bad", "expected_steps": [{"action": "assert", "locator_type": "text", "locator": "Ready", "expected": ""}]})

    def test_missing_required_and_conditional_values(self):
        with self.assertRaises(BusinessRuleError):
            self.service._check_inputs([{**self.parameter, "default_value": None}], {}, True)
        self.service._check_inputs([{**self.parameter, "default_value": None, "condition": {"key": "kind", "equals": "company"}}], {"kind": "person"}, True)
        self.service._check_inputs([{"key": "flag", "label": "Flag", "type": "boolean", "required": True}], {"flag": False}, True)

    def test_typed_values_and_dynamic_values(self):
        for parameter, value in (({"type": "number"}, "not a number"), ({"type": "select", "options": ["a", "b"]}, "c"), ({"type": "date"}, "bad-date"), ({"type": "text", "validation": {"max_length": 3}}, "long")):
            with self.assertRaises(BusinessRuleError):
                self.service._check_inputs([{**self.parameter, **parameter}], {"name": value}, True)
        self.service._check_inputs([{**self.parameter, "type": "number"}], {"name": "{{timestamp}}"}, True)

    def test_manual_input_and_duplicate_keys_are_rejected(self):
        with self.assertRaises(ValidationError):
            WebFeatureSave(name="Test", parameters=[self.parameter, self.parameter])
        with self.assertRaises(ValidationError):
            WebFeatureSave(name="Test", parameters=[{**self.parameter, "type": "manual"}])

    def test_invalid_parameter_rules_are_rejected_before_save(self):
        for rules in ({"min": "bad"}, {"min_length": -1}, {"min": 3, "max": 2}, {"pattern": "unsupported"}):
            with self.assertRaises(ValidationError):
                WebFeatureSave(name="Test", parameters=[{**self.parameter, "validation": rules}])

    def test_conditional_field_is_not_filled_and_boolean_false_is_unchecked(self):
        params = [self.parameter, {"key": "flag", "label": "Flag", "type": "boolean"}, {"key": "extra", "label": "Extra", "type": "text", "condition": {"key": "flag", "equals": True}}]
        candidate = copy.deepcopy(self.candidate)
        candidate["steps"].insert(1, {"name": "Flag", "action": "check", "locator_type": "label", "locator": "Flag", "value": "{{flag}}"})
        candidate["steps"].insert(2, {"name": "Extra", "action": "fill", "locator_type": "label", "locator": "Extra", "value": "{{extra}}"})
        version = self.service.save_version(self.feature["id"], candidate, params)
        case = self.service.save_case(self.feature["id"], {"name": "Conditional", "input_info": {"name": "Name", "flag": False}, "script_version": version["id"]})
        self.assertEqual(["fill", "uncheck", "assert"], [s["action"] for s in case["steps"]])

    def test_empty_pinned_parameters_do_not_fall_back_to_new_feature_parameters(self):
        version = self.service.save_version(self.feature["id"], {"name": "Read", "steps": [self.candidate["steps"][-1]]}, [])
        self.service.save_feature(self.group["id"], {"name": "Changed", "parameters": [self.parameter]}, self.feature["id"])
        case = self.service.save_case(self.feature["id"], {"name": "Pinned", "script_version": version["id"]})
        self.assertEqual({}, case["data"]["input_info"])

    def test_negative_case_does_not_restore_missing_field_default(self):
        case = self.service.save_case(self.feature["id"], {"name": "Missing name", "input_info": {}, "allow_invalid_inputs": True})
        self.assertNotIn("name", case["data"]["input_info"])
        self.assertEqual("", case["steps"][0]["value"])

    def test_discovery_is_reviewable_and_does_not_overwrite_script(self):
        original = copy.deepcopy(self.service.feature(self.feature["id"])["data"]["candidate"])
        changed = copy.deepcopy(self.candidate)
        changed["steps"][0]["locator"] = "New name"
        capture = FeatureCapture("f1", self.feature["name"], "fixture.png", None)
        self.service.persist_discovery(self.service.feature(self.feature["id"]), capture, {"parameters": [self.parameter], "candidate": changed}, [])
        self.assertEqual(original, self.service.feature(self.feature["id"])["data"]["candidate"])
        self.assertEqual("New name", self.service.feature(self.feature["id"])["data"]["discovery_proposal"]["candidate"]["steps"][0]["locator"])
        self.service.accept_discovery(self.feature["id"])
        self.assertEqual("New name", self.service.feature(self.feature["id"])["data"]["candidate"]["steps"][0]["locator"])

    def test_network_relation_requires_matching_project_method_and_path(self):
        own = self.repo.create("api_interfaces", {"name": "Own", "project_id": 1, "data": {"method": "GET", "path": "/options"}})
        foreign = self.repo.create("api_interfaces", {"name": "Foreign", "project_id": 2, "data": {"method": "GET", "path": "/options"}})
        capture = FeatureCapture("f1", self.feature["name"], "fixture.png", None, ({"method": "GET", "path": "/dev-api/options"},))
        self.service.persist_discovery(self.feature, capture, {"parameters": [self.parameter]}, [])
        ids = [r["data"]["interface_id"] for r in self.repo.rows["web_page_api_relations"]]
        self.assertEqual([own["id"]], ids)
        self.assertNotIn(foreign["id"], ids)

    def test_active_task_blocks_edit_and_delete(self):
        self.repo.create("agent_tasks", {"status": "running", "data": {"payload": {"cases": [{"source_id": self.feature["id"], "project_id": 1}]}}})
        with self.assertRaises(BusinessRuleError):
            self.service.delete_feature(self.feature["id"])
        with self.assertRaises(BusinessRuleError):
            self.service.save_version(self.feature["id"], self.candidate)

    def test_delete_removes_function_configuration_but_keeps_execution_history(self):
        self.service.save_case(self.feature["id"], {"name": "Case"})
        self.repo.create("execution_records", {"project_id": 1, "data": {"case_type": "WEB", "case_id": 99}})
        self.assertTrue(self.service.delete_feature(self.feature["id"]))
        self.assertFalse(self.repo.rows["web_test_cases"])
        self.assertFalse(self.repo.rows[VERSIONS])
        self.assertTrue(self.repo.rows["execution_records"])

    def test_execution_requires_approval_and_sends_plain_playwright(self):
        case = self.service.save_case(self.feature["id"], {"name": "Case"})
        self.repo.create("agent_nodes", {"name": "Local", "status": "active", "data": {"node_key": "local", "agent_status": "online", "capabilities": ["case_execution"], "last_seen_at": datetime.now(UTC).isoformat()}})
        payload = {"case_ids": [case["id"]], "headless": False, "node_key": "local"}
        with self.assertRaises(BusinessRuleError):
            self.service.run(self.feature["id"], payload)
        with patch.object(AgentTaskService, "create_case_execution_task", return_value={"id": 900, "status": "pending"}) as queue:
            self.service.run(self.feature["id"], {**payload, "approve_side_effects": True})
            execution = queue.call_args.args[1]
            self.assertEqual("playwright", execution["config"]["engine"])
            self.assertFalse(execution["config"]["headless"])
            self.assertEqual(0, execution["config"]["max_ai_calls_per_case"])

    def test_user_supplied_verification_metadata_cannot_mark_verified(self):
        value = {**self.candidate, "generation_meta": {"verification": {"status": "verified"}}}
        self.assertEqual("draft", self.service.save_version(self.feature["id"], value)["status"])

    def test_success_verifies_exact_script_snapshot_only(self):
        case = self.service.save_case(self.feature["id"], {"name": "Case"})
        task = {"id": 9, "status": "success", "data": {"task_type": "case_execution", "payload": {"case_type": "WEB", "cases": [case]}, "result": {"records": [{"status": "success", "data": {"case_id": case["id"]}}]}}}
        self.service.finish(task)
        self.assertEqual("verified", self.repo.get(VERSIONS, self.version["id"])["status"])

    def test_old_web_pages_are_physically_removed(self):
        root = Path(__file__).resolve().parents[2]
        for name in ("WebCaseDraftsPage.vue", "WebCasesPage.vue", "WebPageDetailPage.vue"):
            self.assertFalse((root / "frontend/src/views/web-testing" / name).exists())
        router = (root / "frontend/src/router.ts").read_text(encoding="utf-8")
        self.assertNotIn("path: 'web/case-drafts'", router)
        self.assertNotIn("path: 'web/cases'", router)


if __name__ == "__main__":
    unittest.main()
