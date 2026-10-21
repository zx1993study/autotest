import json
import unittest
from unittest.mock import patch

from app.schemas.execution_flow import FlowExtract
from app.services.api_flow_values import response_value
from pydantic import ValidationError
from tests.test_api_case_executor import FakeResourceRepository, StubApiCaseExecutor


class RegressionIsolationTest(unittest.TestCase):
    def test_selection_ignores_empty_fields_and_other_customer_types(self):
        rows = [{"kind": "3", "name": "kol"}, {"kind": "1", "name": " "},
                {"kind": "1", "name": None}, {"kind": "1", "name": "terminal"}]
        spec = FlowExtract(name="name", path="/name", selection={
            "path": "/rows", "non_empty": ["/name"], "equals": {"/kind": "1"}}).model_dump()
        self.assertEqual(response_value({"body": json.dumps({"rows": rows})}, spec), "terminal")
        self.assertIsNone(response_value({"body": json.dumps({"rows": rows[:3]})}, spec))

    def test_selection_keeps_zero_and_false_and_array_members_from_same_row(self):
        spec = FlowExtract(name="values", mode="array", paths=["/id", "/enabled"], selection={
            "path": "/rows", "non_empty": ["/id", "/enabled"]}).model_dump()
        self.assertEqual(response_value({"body": '{"rows":[{"id":0,"enabled":false}]}'}, spec), [0, False])

    def test_selection_rejects_implicit_first_row_invalid_pointer_and_non_body(self):
        for kwargs in ({"selection": {"path": "/rows"}},
                       {"selection": {"path": "rows", "non_empty": ["/name"]}},
                       {"source": "header", "selection": {"path": "/rows", "non_empty": ["/name"]}}):
            with self.assertRaises(ValidationError):
                FlowExtract(name="name", **kwargs)

    def test_flow_case_cannot_send_http_from_standalone_or_payload_override(self):
        executor = StubApiCaseExecutor(FakeResourceRepository())
        case = {"id": 1, "name": "owned", "data": {"requires_flow": True}}
        with patch.object(executor, "_send_http_request") as send:
            record = executor.execute(case, {"flow_context": True}, persist_record=False)
        send.assert_not_called()
        self.assertEqual(record["status"], "failed")
        self.assertIn("隔离前置", record["data"]["error"])

    def test_missing_is_distinct_from_null_and_invalid_json(self):
        executor = StubApiCaseExecutor(FakeResourceRepository())
        assertion = [{"type": "json_pointer_exists", "path": "/data", "expected": False}]
        for body, expected in (("{}", True), ('{"data":null}', False), ("invalid", False)):
            result = executor._assert_response(assertion, 200, {}, 1, body)
            self.assertEqual(result[0]["passed"], expected)
        self.assertFalse(executor._assert_response([
            {"type": "json_pointer_exists", "path": "invalid", "expected": False}], 200, {}, 1, "{}")[0]["passed"])


if __name__ == "__main__":
    unittest.main()
