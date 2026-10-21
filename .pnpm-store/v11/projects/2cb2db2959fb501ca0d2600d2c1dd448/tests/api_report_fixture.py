"""API reports combine scalar API summaries and scenario summaries, read-only."""

from copy import deepcopy
from urllib.parse import parse_qs, urlparse

from execution_evidence_fixture import EvidenceFixture


class ApiReportFixture(EvidenceFixture):
    def __init__(self):
        super().__init__()
        self.report_queries = []
        self.run_reads = []
        self.pending_reports = []
        self.hold_report = False
        self.fail_report = False
        self.fail_run = True
        base = {"key": "api:4:0", "kind": "api", "record_id": 4, "project_id": 10, "flow_id": None,
                "scenario_id": None, "source_name": "/business/warehouse", "method": "POST",
                "field_or_scene": "warehouseType", "test_point": "[枚举值] warehouseType = 1", "status": "failed",
                "passed": False, "executed_at": "2026-10-20T08:00:00"}
        self.report_rows = [base] + [
            {**base, "key": f"api:{100 + number}:0", "record_id": 100 + number, "field_or_scene": "stockQuantity", "test_point": f"库存校验 {number}"}
            for number in range(25)
        ]
        self.report_rows += [{**base, "key": "flow:800:2", "kind": "flow", "record_id": 800, "flow_id": 1,
                             "scenario_id": 102, "source_name": "库存核对", "field_or_scene": "审批通过",
                             "test_point": "通过后核对库存", "status": "success", "passed": True, "method": ""},
                            {**base, "key": "api:2000:0", "record_id": 2000, "project_id": 20}]
        node = {"key": "approve", "name": "审批节点", "status": "success", "duration_ms": 100,
                "request": {"path": "/approve", "headers": {"Authorization": "Bearer hidden-flow"}},
                "response_status": 200, "response_body": '{"code":200}', "assertions": [{"passed": True}]}
        self.batch = {"id": 800, "name": "库存核对历史批次", "status": "failed", "project_id": 10,
                      "data": {"flow_id": 1, "mode": "serial", "concurrency": 1, "template_version": 3,
                               "results": [{"scenario_id": 101, "name": "拒绝场景", "status": "failed", "nodes": []},
                                           {"scenario_id": 102, "name": "审批通过", "status": "success", "nodes": [node]}]}}

    def intercept(self, route):
        parsed = urlparse(route.request.url)
        endpoint = parsed.path.removeprefix("/api/v1")
        if route.request.method != "GET":
            return super().intercept(route)
        if endpoint == "/api-testing/reports":
            query = {key: values[0] for key, values in parse_qs(parsed.query).items()}
            self.report_queries.append(query)
            if self.fail_report:
                self.fail_report = False
                route.fulfill(status=503, json={"code": 503, "message": "Report temporarily unavailable"})
                return
            rows = [deepcopy(row) for row in self.report_rows
                    if (not query.get("project_id") or row["project_id"] == int(query["project_id"]))
                    and (not query.get("kind") or row["kind"] == query["kind"])
                    and (not query.get("status") or row["status"] == query["status"])
                    and query.get("keyword", "") in " ".join(str(row[key]) for key in ("source_name", "field_or_scene", "test_point"))]
            rows.sort(key=lambda row: -row["record_id"])
            page, size = int(query.get("page", 1)), int(query.get("pageSize", 20))
            data = {"items": rows[(page - 1) * size:page * size], "total": len(rows), "page": page, "pageSize": size}
            if self.hold_report:
                self.hold_report = False
                self.pending_reports.append((route, data))
                return
        elif endpoint == "/execution/flows/1/runs/800":
            self.run_reads.append(800)
            if self.fail_run:
                self.fail_run = False
                route.fulfill(status=503, json={"code": 503, "message": "Run temporarily unavailable"})
                return
            data = self.batch
        else:
            return super().intercept(route)
        self.fulfill(route, data)

    def release_reports(self):
        pending, self.pending_reports = self.pending_reports, []
        for route, data in pending:
            self.fulfill(route, data)
