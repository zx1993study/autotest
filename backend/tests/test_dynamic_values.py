from __future__ import annotations

import json
import re
import unittest
from copy import deepcopy
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from app.api.v1.dynamic_values import DynamicValuePreview, preview_dynamic_value
from app.core.exceptions import BusinessRuleError
from app.scheduler.jobs.api_case_executor import ApiCaseExecutor
from app.scheduler.jobs.app_case_executor import AppCaseExecutor
from app.scheduler.jobs.web_case_executor import WebCaseExecutor
from tests.test_api_case_executor import FakeResourceRepository
from web_automation.compiler import ExecutionPlanCompiler
from web_automation.dynamic_values import DynamicValueContext, DynamicValueError, prepare_dynamic_execution


class DynamicValueContextTest(unittest.TestCase):
    def test_timestamp_suffix_and_date_are_frozen(self) -> None:
        context = DynamicValueContext(now_ms=1728000000123)
        self.assertEqual("customer_1728000000123", context.resolve("customer_{{timestamp_ms}}"))
        self.assertEqual("1728000000", context.resolve("{{timestamp}}"))
        self.assertRegex(context.resolve("{{datetime}}"), r"^\d{14}$")
        self.assertEqual(context.resolve("{{timestamp_ms}}"), context.resolve("{{timestamp_ms}}"))

    def test_phone_is_string_with_prefix_and_reused_across_fields(self) -> None:
        context = DynamicValueContext()
        resolved = context.resolve({"phone": "{{random_phone:139}}", "confirm": "{{random_phone:139}}"})
        self.assertRegex(resolved["phone"], r"^139\d{8}$")
        self.assertEqual(resolved["phone"], resolved["confirm"])
        self.assertEqual(11, len(resolved["phone"]))

    def test_named_variables_and_native_types(self) -> None:
        context = DynamicValueContext({"phone": {"generator": "phone", "prefix": "138"}, "count": 3, "enabled": False,
                                       "label": "customer_{{timestamp_ms}}", "alias": "{{phone}}"})
        self.assertEqual(context.resolve("{{phone}}"), context.resolve("{{alias}}"))
        self.assertEqual(3, context.resolve("{{count}}"))
        self.assertIs(False, context.resolve("{{enabled}}"))
        self.assertTrue(context.resolve("{{label}}").startswith("customer_"))

    def test_separate_variables_and_batch_reservations_avoid_duplicate_phones(self) -> None:
        reserved: set[str] = set()
        definitions = {"a": {"generator": "phone"}, "b": {"generator": "phone"}}
        with patch("web_automation.dynamic_values.secrets.randbelow", side_effect=[0] * 8 + [0] * 8 + [1] * 8 + [2] * 8):
            first = DynamicValueContext(definitions, used_phones=reserved)
            a, b = first.value("a"), first.value("b")
            c = DynamicValueContext(used_phones=reserved).value("random_phone")
        self.assertEqual(3, len({a, b, c}))
        self.assertEqual({a, b, c}, reserved)

    def test_snapshot_preserves_values_for_retry(self) -> None:
        first = DynamicValueContext(now_ms=1234)
        phone = first.value("random_phone")
        snapshot = first.snapshot()
        restored = DynamicValueContext(snapshot=snapshot, now_ms=9999)
        self.assertEqual(phone, restored.value("random_phone"))
        self.assertEqual("1234", restored.value("timestamp_ms"))
        snapshot["values"]["random_phone"] = "changed"
        self.assertEqual(phone, first.value("random_phone"))

    def test_invalid_tokens_and_definitions_fail_explicitly(self) -> None:
        for template in ("{{missing}}", "{{random_phone:12}}", "{{random_digits:0}}", "{{random_digits:65}}", "{{random_digits:1.5}}"):
            with self.subTest(template=template), self.assertRaises(DynamicValueError):
                DynamicValueContext().resolve(template)
        with self.assertRaisesRegex(DynamicValueError, "Circular"):
            DynamicValueContext({"a": "{{b}}", "b": "{{a}}"}).value("a")
        with self.assertRaises(DynamicValueError):
            DynamicValueContext({"a": {"generator": "phone", "prefixes": ["138", "12"]}}).value("a")
        with self.assertRaises(DynamicValueError):
            DynamicValueContext({"a": [1]}).resolve("prefix_{{a}}")

    def test_escaped_template_remains_literal(self) -> None:
        self.assertEqual("{{random_phone}}", DynamicValueContext().resolve(r"\{{random_phone}}"))
        self.assertRegex(DynamicValueContext().resolve("{{random_digits:6}}"), r"^\d{6}$")

    def test_prepare_does_not_mutate_saved_templates_or_runtime_overrides(self) -> None:
        case = {"data": {"variables": {"phone": {"generator": "phone"}}, "params": {"phone": "{{phone}}"}},
                "steps": [{"value": "{{phone}}"}], "assertions": [{"expected": "{{phone}}"}]}
        payload = {"config": {"variables": {"phone": {"generator": "phone", "prefix": "139"}}, "params": {"phone": "{{phone}}"}}}
        original = deepcopy((case, payload))
        resolved, execution, _ = prepare_dynamic_execution(case, payload)
        phone = resolved["data"]["params"]["phone"]
        self.assertRegex(phone, r"^139\d{8}$")
        self.assertEqual(phone, resolved["steps"][0]["value"])
        self.assertEqual(phone, resolved["assertions"][0]["expected"])
        self.assertEqual(phone, execution["config"]["params"]["phone"])
        self.assertEqual(original, (case, payload))

    def test_preview_uses_same_rules_and_validates_unreferenced_variables(self) -> None:
        result = preview_dynamic_value(DynamicValuePreview(value={"phone": "{{random_phone}}"}))
        self.assertRegex(result["data"]["resolved"]["phone"], r"^138\d{8}$")
        with self.assertRaises(BusinessRuleError):
            preview_dynamic_value(DynamicValuePreview(value="fixed", variables={"a": {"generator": "unknown"}}))
        for variables in ([1], {"bad-name": 1}):
            with self.assertRaises(DynamicValueError):
                prepare_dynamic_execution({"data": {"variables": variables}}, {})


class DynamicExecutionTest(unittest.TestCase):
    def case(self) -> dict:
        return {"id": 1, "name": "Create customer", "project_id": 1, "source_id": 10,
                "data": {"method": "POST", "path": "/customers", "skip_auth": True,
                         "params": {"name": "customer_{{timestamp_ms}}", "phone": "{{random_phone}}"}},
                "assertions": [{"type": "body_contains", "expected": "{{random_phone}}"}]}

    def test_api_resolves_request_assertion_and_records_without_mutating_case(self) -> None:
        repository = FakeResourceRepository()
        executor = ApiCaseExecutor(repository)
        case = self.case()
        original = deepcopy(case)
        with patch.object(executor, "_send_http_request", side_effect=lambda request: (200, {}, json.dumps(request["body"]))) as send:
            record = executor.execute(case, {})
        self.assertEqual("success", record["status"], record["description"])
        self.assertEqual(1, send.call_count)
        body = record["data"]["request"]["body"]
        self.assertRegex(body["phone"], r"^138\d{8}$")
        self.assertEqual(body["phone"], record["data"]["assertions"][0]["expected"])
        self.assertEqual(body["phone"], record["data"]["dynamic_values"]["values"]["random_phone"])
        self.assertEqual(original, case)

    def test_api_regenerates_on_next_execution_and_resolves_overrides(self) -> None:
        executor = ApiCaseExecutor(FakeResourceRepository())
        case = self.case()
        case["assertions"] = []
        with patch.object(executor, "_send_http_request", return_value=(200, {}, "ok")), patch("web_automation.dynamic_values.secrets.randbelow", side_effect=[0] * 8 + [1] * 8):
            first = executor.execute(case, {})
            second = executor.execute(case, {"config": {"params": {"phone": "{{random_phone}}"}}})
        self.assertNotEqual(first["data"]["request"]["body"]["phone"], second["data"]["request"]["body"]["phone"])

    def test_invalid_api_template_and_length_do_not_send_http(self) -> None:
        repository = FakeResourceRepository()
        executor = ApiCaseExecutor(repository)
        for template, error in (("{{unknown}}", "Unknown"), ("customer_{{timestamp_ms}}", "maxLength")):
            case = self.case()
            case["data"]["params"]["name"] = template
            repository.fields[0]["data"]["schema"] = {"type": "string", "maxLength": 6}
            with patch.object(executor, "_send_http_request") as send:
                record = executor.execute(case, {})
            self.assertEqual("failed", record["status"])
            self.assertIn(error, record["data"]["error"])
            send.assert_not_called()

    def test_dynamic_text_is_rejected_for_numeric_api_fields(self) -> None:
        repository = FakeResourceRepository()
        repository.fields[0]["data"]["schema"] = {"type": "integer"}
        executor = ApiCaseExecutor(repository)
        with patch.object(executor, "_send_http_request") as send:
            record = executor.execute(self.case(), {})
        self.assertIn("field type is integer", record["data"]["error"])
        send.assert_not_called()

    def test_web_element_defaults_and_steps_share_values(self) -> None:
        case = {"id": 1, "name": "Web input", "data": {}, "steps": [{"element_id": 1}, {"action": "fill", "value": "{{random_phone}}"}]}
        context = {"elements": [{"id": 1, "data": {"element_type": "input", "default_value": "{{random_phone}}"}}]}
        compiled = ExecutionPlanCompiler().compile_case(case, context)
        self.assertEqual(compiled.steps[0]["value"], compiled.steps[1]["value"])
        self.assertRegex(compiled.steps[0]["value"], r"^138\d{8}$")
        self.assertEqual({}, case["data"])

    def test_invalid_web_case_does_not_block_batch_or_start_browser(self) -> None:
        invalid = {"id": 1, "name": "Bad", "steps": [{"action": "fill", "value": "{{unknown}}"}]}
        valid = {"id": 2, "name": "Good", "steps": [{"action": "fill", "value": "{{random_phone}}"}]}
        plan = ExecutionPlanCompiler().compile({"cases": [invalid, valid]})
        self.assertIn("Unknown", plan.cases[0].raw["_dynamic_error"])
        self.assertRegex(plan.cases[1].steps[0]["value"], r"^138\d{8}$")
        executor = WebCaseExecutor(FakeResourceRepository())
        with patch.object(executor, "_run_async_web_steps") as run:
            record = executor.execute(invalid, {})
        self.assertEqual("failed", record["status"])
        self.assertIn("Unknown", record["data"]["error"])
        run.assert_not_called()

    def test_app_and_miniapp_use_shared_values_in_inputs_and_steps(self) -> None:
        for case_type in ("APP", "MINIAPP"):
            with self.subTest(case_type=case_type):
                executor = AppCaseExecutor(FakeResourceRepository(), case_type)
                case = {"id": 1, "name": "App input", "data": {"input_info": {"phone": {"value": "{{random_phone}}"}}},
                        "steps": [{"action": "input", "value": "{{random_phone}}"}]}
                with patch.object(executor, "_preflight_checks", return_value={}), patch.object(executor, "_run_app_steps", return_value={"step_count": 1}) as run:
                    record = executor.execute(case, {})
                self.assertEqual("success", record["status"], record["description"])
                phone = record["data"]["input_snapshot"]["phone"]["value"]
                self.assertEqual(phone, run.call_args.args[1][0]["value"])
                self.assertEqual("{{random_phone}}", case["steps"][0]["value"])

    def test_wda_python_script_receives_resolved_input(self) -> None:
        executor = AppCaseExecutor(FakeResourceRepository())
        case = {"id": 1, "name": "WDA input", "data": {"execution_mode": "python_script", "script_path": str(Path(__file__).resolve()),
                "script_arg_map": {"phone": "--phone"}, "input_info": {"phone": {"value": "{{random_phone:139}}"}}}}
        with patch.object(executor, "_preflight_checks", return_value={}), patch("app.scheduler.jobs.app_case_executor.subprocess.run", return_value=CompletedProcess([], 0, "", "")) as run:
            record = executor.execute(case, {})
        self.assertEqual("success", record["status"], record["description"])
        command = run.call_args.args[0]
        self.assertRegex(command[command.index("--phone") + 1], r"^139\d{8}$")
        self.assertEqual(record["data"]["input_snapshot"]["phone"]["value"], command[command.index("--phone") + 1])

    def test_miniapp_element_default_is_resolved_once(self) -> None:
        executor = AppCaseExecutor(FakeResourceRepository(), "MINIAPP")
        element = {"id": 2, "name": "phone", "data": {"element_type": "input", "default_value": "{{random_phone}}"}}
        case = {"id": 1, "name": "MiniApp", "data": {}, "steps": [{"element_id": 2}]}
        with patch.object(executor, "_elements_for_case", return_value=({"phone": element}, {2: element})), patch.object(executor, "_preflight_checks", return_value={}), patch.object(executor, "_run_app_steps", return_value={}):
            record = executor.execute(case, {})
        self.assertRegex(record["data"]["steps"][0]["value"], r"^138\d{8}$")
        self.assertEqual("{{random_phone}}", element["data"]["default_value"])


if __name__ == "__main__":
    unittest.main()
