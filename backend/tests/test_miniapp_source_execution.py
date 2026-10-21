from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.resource_record import ResourceRecord
from app.models.test_case_record import MiniappTestCaseRecord
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.scheduler.jobs.miniapp_source_executor import execute_source_case
from app.services.miniapp_source_run_service import MiniappSourceRunService
from app.services.report_statistics_service import ReportStatisticsService
from tests.test_miniapp_source import catalog as catalog  # noqa: PLC0414 - explicit pytest fixture export
from tests.test_miniapp_source import imported
from tests.test_miniapp_source import repository as repository  # noqa: PLC0414 - explicit pytest fixture export
from tests.test_report_statistics_service import FakeResourceRepository


class SourcePageHandler(BaseHTTPRequestHandler):
    writes = 0

    def do_GET(self):
        body = b'<div class="login">Login</div><button onclick="fetch(\'/write\',{method:\'POST\'})">Write</button>'
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        type(self).writes += 1
        self.send_response(200)
        self.end_headers()

    def log_message(self, *_):
        pass


def test_real_browser_runs_readonly_and_blocks_write_before_it_reaches_server(repository, catalog):
    case = imported(repository, catalog)
    SourcePageHandler.writes = 0
    server = ThreadingHTTPServer(("127.0.0.1", 0), SourcePageHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}"
        result = execute_source_case(case, "h5", url)
        assert result["status"] == "success", result
        case["data"]["definition"]["operations"].append({"action": "click", "selector": "button"})
        result = execute_source_case(case, "h5", url)
        assert result["status"] == "failed" and "拦截" in result["reason"]
        assert SourcePageHandler.writes == 0
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.mark.parametrize("url", [123, "http://[bad", "https://user:password@example.test"])
def test_invalid_project_h5_configuration_is_blocked_not_interrupted(repository, catalog, url):
    result = execute_source_case(imported(repository, catalog), "h5", url)
    assert result["status"] == "blocked" and result["reason"] == "miniapp_h5_url 配置无效"


def test_run_evidence_roundtrips_through_real_repository():
    engine = create_engine("sqlite:///:memory:")
    ResourceRecord.__table__.create(engine)
    MiniappTestCaseRecord.__table__.create(engine)
    with Session(engine) as db:
        repo = SqlAlchemyResourceRepository(db)
        run = repo.create("miniapp_source_runs", {"name": "Source test", "project_id": 10,
                                                "data": {"platform": "mp-weixin", "case_count": 1}})
        results = [{"case_id": 3, "name": "Page", "status": "blocked", "executed": False,
                    "reason": "Missing device", "definition": {"steps": ["Open"], "expected": ["Visible"]}}]
        service = MiniappSourceRunService(repo)
        service.finish(run["id"], results)
        assert service.get_run(run["id"])["data"]["results"] == results
        record = repo.list("execution_records", project_id=10)[0][0]
        assert record["data"]["executed"] is False and record["status"] == "blocked"
    engine.dispose()


def test_blocked_records_are_visible_but_excluded_from_measured_pass_rate():
    repo = FakeResourceRepository({"execution_records": [
        {"id": index, "project_id": 10, "status": status, "data": {"case_type": "MINIAPP"}}
        for index, status in enumerate(["success", "failed", "blocked", "interrupted"], 1)]})
    summary = ReportStatisticsService(repo).overview(10)
    statuses = {item["status"]: item["count"] for item in summary["status_distribution"]}
    assert statuses["blocked"] == statuses["interrupted"] == 1
    assert summary["summary"]["execution_total"] == 4
    assert summary["summary"]["pass_rate"] == 50
