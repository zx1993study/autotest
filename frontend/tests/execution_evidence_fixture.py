"""Read-only fixtures for historical execution evidence and API case dialogs."""

import json
import re
from copy import deepcopy
from urllib.parse import parse_qs, urlparse

from check_api_detail_navigation_ui import NavigationFixture
from check_report_record_filters_ui import RecordFixture


class EvidenceFixture(RecordFixture):
    def __init__(self):
        super().__init__()
        self.navigation = NavigationFixture()
        self.details = []
        self.case_queries = []
        self.fail_once = {6}
        self.pending = []
        self.hold_case = False
        self.fail_case_once = False
        for row in self.rows:
            row.update(created_at="2026-10-20T08:00:00", updated_at="2026-10-20T08:00:00")
        self.records = {row["id"]: deepcopy(row) for row in self.rows}
        self.records[4]["data"] = {
            "case_id": 101, "case_type": "API", "duration_ms": 417,
            "request": {"method": "POST", "url": "https://example.test/customers?access_token=hidden-query",
                        "headers": {"Authorization": "Bearer hidden-header", "Content-Type": "application/json"},
                        "body": {"name": "Historical customer", "password": "hidden-password"}, "query": {"page": 1}},
            "response_status": 200, "response_headers": {"Set-Cookie": "hidden-cookie", "Content-Type": "application/json"},
            "response_body": json.dumps({"code": 500, "msg": "库存不足", "token": "hidden-response",
                                         "rows": [{"name": f"Customer {number}"} for number in range(30)]}, ensure_ascii=False),
            "assertions": [{"type": "status", "expected": 200, "actual": 200, "passed": True},
                           {"type": "json", "path": "$.code", "expected": 200, "actual": 500, "passed": False,
                            "message": "库存不足"}],
        }
        self.records[2]["data"] = {"case_type": "API", "response_body": "Plain upstream response", "assertions": []}
        self.records[3]["data"] = {"case_type": "API", "assertions": []}
        self.records[5]["data"] = {"case_type": "WEB", "input_snapshot": {"username": "test-user", "password": "hidden-web"},
                                  "steps": [{"action": "assert_text", "expected": "customer"}],
                                  "assertions": [{"type": "text", "expected": "customer"}], "error": "页面元素未找到"}
        self.records[6]["data"] = {"case_type": "APP", "step_timeline": [{"action": "click", "status": "failed"}],
                                  "error": "设备离线", "assertions": []}
        for number in (899, 900):
            self.records[number] = {**deepcopy(self.records[4]), "id": number, "name": f"Evidence {number}"}
        self.latest = {**deepcopy(self.records[4]), "id": 700, "name": "Latest execution"}
        self.latest["data"]["request"]["body"]["name"] = "Latest customer"
        case = self.navigation.cases[101]
        case["data"] = {"request": {"method": "POST", "path": "/customers", "body": {"password": "hidden-case"}}}
        case["assertions"] = [{"type": "status", "expected": 200}]
        self.navigation.cases[102]["assertions"] = case["assertions"]
        self.draft = {**deepcopy(case), "id": 201, "name": "客户新增草稿", "status": "draft"}

    def intercept(self, route):
        request = route.request
        parsed = urlparse(request.url)
        endpoint = parsed.path.removeprefix("/api/v1")
        if request.method != "GET":
            return super().intercept(route)
        if match := re.fullmatch(r"/reports/records/(\d+)", endpoint):
            number = int(match[1])
            self.details.append(number)
            if number == 899:
                self.pending.append((route, self.records[number]))
                return
            if number in self.fail_once:
                self.fail_once.remove(number)
                route.fulfill(status=503, json={"code": 503, "message": "Temporary record read error"})
                return
            data = self.records.get(number, {**self.records[4], "id": number})
        elif endpoint == "/reports/records" and "case_id" in parse_qs(parsed.query):
            query = {key: values[0] for key, values in parse_qs(parsed.query).items()}
            self.case_queries.append(query)
            if self.fail_case_once:
                self.fail_case_once = False
                route.fulfill(status=503, json={"code": 503, "message": "Temporary latest record error"})
                return
            data = self.navigation.page([self.latest] if query["case_id"] == "101" else [])
            if self.hold_case and query["case_id"] == "101":
                self.pending.append((route, data))
                self.hold_case = False
                return
        elif endpoint == "/api-testing/case-drafts":
            data = self.navigation.page([self.draft])
        elif endpoint.startswith(("/api-testing/", "/project-auth/")):
            return self.navigation.intercept(route)
        else:
            return super().intercept(route)
        self.fulfill(route, data)

    @staticmethod
    def fulfill(route, data):
        route.fulfill(json={"code": 0, "message": "success", "data": data})

    def release(self):
        pending, self.pending = self.pending, []
        for route, data in pending:
            self.fulfill(route, data)
