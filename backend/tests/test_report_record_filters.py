"""Execution record filters use the persisted status, with SQL pagination."""

import pytest
from app.api.v1.report_records import get_execution_record_service, router
from app.models.resource_record import ResourceRecord
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.services.resource_service import ResourceService
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

STATUSES = ("queued", "running", "success", "failed", "blocked", "interrupted")


@pytest.fixture
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    ResourceRecord.__table__.create(engine)
    with Session(engine) as session:
        session.add_all([
            ResourceRecord(table_name="execution_records", name=f"Run {status}", project_id=10,
                           status=status, data_json={"data": {"status": "not-the-record-status"}})
            for status in STATUSES
        ])
        session.add_all([
            ResourceRecord(table_name="execution_records", name=f"Login {number}", project_id=10,
                           status="failed", data_json={}) for number in range(2)
        ])
        session.add_all([
            ResourceRecord(table_name="execution_records", name="Login other project", project_id=20,
                           status="failed", data_json={}),
            ResourceRecord(table_name="execution_records", name="Login deleted", project_id=10,
                           status="failed", deleted=True, data_json={}),
            ResourceRecord(table_name="agent_tasks", name="Login other table", project_id=10,
                           status="failed", data_json={}),
        ])
        session.commit()
        app = FastAPI()
        app.include_router(router)
        service = ResourceService("execution_records", SqlAlchemyResourceRepository(session))
        app.dependency_overrides[get_execution_record_service] = lambda: service
        with TestClient(app) as test_client:
            yield test_client
    engine.dispose()


@pytest.mark.parametrize("status", STATUSES)
def test_filter_each_status(client, status):
    response = client.get("/reports/records", params={"project_id": 10, "status": status})
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["total"] == (3 if status == "failed" else 1)
    assert all(row["status"] == status and row["project_id"] == 10 for row in result["items"])


def test_status_combines_with_project_keyword_and_pagination(client):
    params = {"project_id": 10, "status": "failed", "keyword": "Login", "pageSize": 1}
    pages = [client.get("/reports/records", params={**params, "page": page}).json()["data"]
             for page in (1, 2)]
    assert [page["total"] for page in pages] == [2, 2]
    assert [page["page"] for page in pages] == [1, 2]
    rows = [page["items"][0] for page in pages]
    assert {row["name"] for row in rows} == {"Login 0", "Login 1"}
    assert all(row["project_id"] == 10 and row["status"] == "failed" for row in rows)


@pytest.mark.parametrize("params", [{"project_id": 10}, {"project_id": 10, "status": ""}])
def test_all_statuses_removes_only_the_status_filter(client, params):
    result = client.get("/reports/records", params=params).json()["data"]
    assert result["total"] == 8
    assert {row["status"] for row in result["items"]} == set(STATUSES)
    assert all(row["project_id"] == 10 for row in result["items"])


def test_status_without_project_and_empty_results(client):
    result = client.get("/reports/records", params={"status": "failed"}).json()["data"]
    assert result["total"] == 4
    assert {row["project_id"] for row in result["items"]} == {10, 20}
    empty = client.get("/reports/records", params={"status": "success", "keyword": "Login"}).json()["data"]
    assert empty["items"] == [] and empty["total"] == 0


def test_record_detail_returns_selected_snapshot_not_latest_case_result(client):
    service = client.app.dependency_overrides[get_execution_record_service]()
    data = {"case_id": 101, "case_type": "API", "request": {"body": {"name": "Historical customer"}},
            "response_status": 200, "response_body": '{"code":500}',
            "assertions": [{"type": "json", "expected": 200, "actual": 500, "passed": False}]}
    old = service.create({"name": "Old run", "status": "failed", "data": data})
    latest = service.create({"name": "New run", "status": "success", "data": {
        **data, "request": {"body": {"name": "Latest customer"}}, "response_body": '{"code":200}',
        "assertions": [{"type": "json", "expected": 200, "actual": 200, "passed": True}]
    }})
    selected = client.get(f"/reports/records/{old['id']}").json()["data"]
    assert selected["id"] != latest["id"] and selected["status"] == "failed"
    assert selected["data"] == data
