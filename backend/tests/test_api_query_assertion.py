import json
import unittest

from app.scheduler.jobs.api_case_executor import ApiCaseExecutor
from app.utils.api_query_assertion import assert_query_result


class QueryAssertionTest(unittest.TestCase):
    def check(self, rows, **options):
        return assert_query_result(json.dumps({"rows": rows}), {"path": "/rows", **options})

    def test_all_rows_not_only_first_are_checked(self):
        rule = {"paths": ["/status"], "operator": "eq", "expected": "1"}
        self.assertTrue(self.check([{"status": 1}, {"status": "1"}], rules=[rule])["passed"])
        result = self.check([{"status": "1"}, {"status": "2"}], rules=[rule])
        self.assertFalse(result["passed"])
        self.assertEqual(result["actual"]["mismatched_indices"], [1])

    def test_empty_matches_are_explicit_and_missing_paths_fail(self):
        self.assertFalse(self.check([])["passed"])
        self.assertTrue(self.check([], min_items=0, max_items=0)["passed"])
        self.assertFalse(self.check([{}], min_items=0, max_items=0)["passed"])
        self.assertFalse(assert_query_result('{}', {"path": "/rows", "min_items": 0})["passed"])
        self.assertFalse(self.check({}, min_items=0)["passed"])

    def test_keywords_tokens_dates_and_missing_fields(self):
        rules = [{"paths": ["/name", "/alias"], "operator": "contains", "expected": "门店"},
                 {"paths": ["/ids"], "operator": "tokens", "expected": 2},
                 {"paths": ["/time"], "operator": "date_ge", "expected": "2026-10-14 00:00:00"}]
        self.assertTrue(self.check([{"alias": "江城门店", "ids": [1, 2], "time": "2026-10-15 10:00:00"}], rules=rules)["passed"])
        self.assertFalse(self.check([{"alias": "门店", "ids": [1], "time": "bad"}], rules=rules)["passed"])
        self.assertFalse(self.check([{}], rules=rules)["passed"])
        self.assertFalse(self.check([{"status": True}], rules=[{"paths": ["/status"], "operator": "eq", "expected": 1}])["passed"])

    def test_invalid_configuration_fails_even_for_empty_results(self):
        for options in ({"max_items": -1}, {"min_items": True}, {"rules": [{}]},
                        {"rules": [{"paths": ["/x"], "operator": "execute"}]}, {"rules": "invalid"}):
            self.assertFalse(self.check([], min_items=0, **{k: v for k, v in options.items() if k != "min_items"})["passed"]
                             if "min_items" not in options else self.check([], **options)["passed"])

    def test_executor_dispatches_and_invalid_json_is_evidence(self):
        assertion = {"type": "json_query_result", "path": "/rows", "min_items": 0, "max_items": 2}
        result = ApiCaseExecutor(None)._assert_response([assertion], 200, {}, 1, '{"rows":[{},{}]}')
        self.assertTrue(result[0]["passed"])
        self.assertFalse(assert_query_result("not json", assertion)["passed"])

    def test_date_only_bounds_include_the_entire_calendar_day(self):
        rule = {"paths": ["/time"], "operator": "date_le", "expected": "2026-10-15"}
        self.assertTrue(self.check([{"time": "2026-10-15 23:59:59"}], rules=[rule])["passed"])
        self.assertFalse(self.check([{"time": "2026-10-16 00:00:00"}], rules=[rule])["passed"])
