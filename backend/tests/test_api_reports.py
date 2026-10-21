import json
from datetime import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.v1.api_reports import get_service, router
from app.models.resource_record import ResourceRecord
from app.repositories.sqlalchemy_api_report import report_statement
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.schemas.api_report import ApiReportQuery
from app.services.api_report_service import ApiReportService
from app.utils.api_report_metadata import case_report_metadata


@pytest.fixture
def reports():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    ResourceRecord.__table__.create(engine)
    with Session(engine) as db:
        for number in range(25):
            db.add(ResourceRecord(id=number + 1, table_name="execution_records", project_id=10,
                                  name=f"API 用例执行 - [枚举值] warehouseType = {number}", status="failed" if number % 2 else "success",
                                  created_at=datetime(2026, 10, 20, 8),
                                  data_json={"data": {"case_type": "API", "case_id": 100 + number,
                                                      "request": {"method": "POST", "path": "/business/warehouse",
                                                                  "headers": {"Authorization": "hidden-token"}},
                                                      "response_body": "hidden-body" * 5000}}))
        scene = {"scenario_id": 101, "name": "正常销售", "status": "success", "nodes": [{"response_body": "hidden-evidence" * 5000}],
                 "snapshot": {"flow": {"name": "历史销售流程"}, "scenario": {"description": "审批通过后核对库存"}}}
        db.add(ResourceRecord(id=100, table_name="api_flow_runs", project_id=10, name="历史批次", status="failed",
                              data_json={"data": {"flow_id": 88, "results": [scene, {**scene, "scenario_id": 102,
                                                    "name": "库存不足", "status": "failed", "test_point": "超库存销售被拒绝"}]}}))
        for item_id, table, project, deleted, data in [
            (101, "execution_records", 20, False, {"data": {"case_type": "API", "report": {
                "api_path": "/old/path", "field_name": "phone", "test_point": "手机校验"}}}),
            (102, "execution_records", 10, True, {"data": {"case_type": "API"}}),
            (103, "execution_records", 10, False, {"data": {"case_type": "WEB"}}),
            (104, "execution_records", 10, False, {"case_type": "API", "data": {"report": {"test_point": "历史接口"}}}),
            (105, "api_flow_runs", 10, False, {"data": {"flow_id": 88, "results": []}}),
        ]:
            db.add(ResourceRecord(id=item_id, table_name=table, project_id=project, deleted=deleted, data_json=data,
                                  name=f"Record {item_id}", status="running", created_at=datetime(2026, 10, 20, 8)))
        db.commit()
        repo = SqlAlchemyResourceRepository(db)
        service = ApiReportService(repo)
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_service] = lambda: service
        with TestClient(app) as client:
            yield client, service, db
    engine.dispose()


def test_merged_rows_have_correct_total_stable_id_order_and_no_payloads(reports):
    client, _, _ = reports
    response = client.get("/api-testing/reports", params={"project_id": 10, "pageSize": 100})
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["total"] == 28
    rows = result["items"]
    assert [row["record_id"] for row in rows[:3]] == [104, 100, 100]
    assert [row["scenario_id"] for row in rows[1:3]] == [101, 102]
    assert rows[1]["source_name"] == "历史销售流程" and rows[1]["test_point"] == "审批通过后核对库存"
    assert rows[2]["passed"] is False and rows[2]["test_point"] == "超库存销售被拒绝"
    assert rows[3]["field_or_scene"] == "warehouseType" and rows[3]["source_name"] == "/business/warehouse"
    assert rows[0]["passed"] is None and rows[0]["source_name"] == "未记录接口路径"
    assert len({row["key"] for row in rows}) == 28
    assert "hidden-" not in json.dumps(result) and "response_body" not in json.dumps(result)


@pytest.mark.parametrize(("params", "total"), [
    ({"kind": "api"}, 26), ({"kind": "flow"}, 2), ({"status": "failed"}, 13),
    ({"kind": "flow", "status": "success"}, 1), ({"keyword": "销售"}, 2),
    ({"keyword": "/business/warehouse"}, 25), ({"keyword": "warehouseType"}, 25),
    ({"keyword": "missing"}, 0), ({"keyword": "%"}, 0), ({"keyword": "_"}, 0),
])
def test_filters_apply_before_pagination(reports, params, total):
    client, _, _ = reports
    result = client.get("/api-testing/reports", params={"project_id": 10, **params, "pageSize": 1}).json()["data"]
    assert result["total"] == total
    assert len(result["items"]) == min(total, 1)


def test_project_filters_and_exact_pagination(reports):
    client, _, _ = reports
    other = client.get("/api-testing/reports", params={"project_id": 20}).json()["data"]
    assert other["total"] == 1 and other["items"][0]["field_or_scene"] == "phone"
    assert other["items"][0]["source_name"] == "/old/path"
    all_rows = client.get("/api-testing/reports", params={"pageSize": 100}).json()["data"]
    assert all_rows["total"] == 29
    pages = [client.get("/api-testing/reports", params={"project_id": 10, "pageSize": 10, "page": page}).json()["data"]
             for page in range(1, 4)]
    assert [len(page["items"]) for page in pages] == [10, 10, 8]
    keys = [row["key"] for page in pages for row in page["items"]]
    assert len(set(keys)) == 28


def test_query_count_does_not_grow_with_page_size(reports):
    _, service, db = reports
    statements = []

    def capture(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(statement)

    event.listen(db.get_bind(), "before_cursor_execute", capture)
    try:
        for size in (1, 100):
            statements.clear()
            rows, total = service.list(ApiReportQuery(project_id=10, page_size=size))
            assert len(statements) == 2 and total == 28
            assert len(json.dumps(rows)) < 20000
    finally:
        event.remove(db.get_bind(), "before_cursor_execute", capture)


def test_mysql_uses_json_table_scalar_projection(reports):
    _, _, db = reports
    db.get_bind().dialect = mysql.dialect()
    sql = str(report_statement(db, ApiReportQuery()).compile(dialect=mysql.dialect()))
    assert "JSON_TABLE" in sql and "FOR ORDINALITY" in sql
    assert "NULL ON ERROR" in sql and "response_body" not in sql and "assertions" not in sql
    assert "COLLATE utf8mb4_unicode_ci" in sql and "CHARACTER SET utf8mb4" in sql


@pytest.mark.parametrize("params", [{"page": 0}, {"pageSize": 101}, {"project_id": 0}, {"kind": "WEB"}])
def test_invalid_query_is_rejected(reports, params):
    client, _, _ = reports
    assert client.get("/api-testing/reports", params=params).status_code == 422


def test_execution_metadata_uses_snapshot_and_not_credentials():
    case = {"name": "[必填为空] customerName", "data": {"path": "/configured", "password": "hidden-password"}}
    result = case_report_metadata(case, {"path": "/actual", "headers": {"Authorization": "hidden-token"}})
    assert result == {"api_path": "/actual", "field_name": "customerName", "test_point": case["name"]}
