"""Validate batch snapshots and caller-thread persistence against a real repository."""

from threading import Barrier, get_ident
from unittest.mock import patch

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.scheduler.jobs.api_case_executor import ApiCaseExecutor
from app.scheduler.jobs.case_execution_jobs import run_case_execution_job


def test_sql_queries_stay_on_caller_thread_and_field_locations_survive_snapshot():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    sql_threads = []
    try:
        with sessionmaker(bind=engine)() as session:
            repository = SqlAlchemyResourceRepository(session)
            project = repository.create("projects", {"name": "Mock project", "data": {"base_url": "https://mock.test"}})
            project_id = project["id"]
            interface = repository.create("api_interfaces", {"name": "Mock API", "project_id": project_id,
                "data": {"method": "POST", "path": "/mock"}})
            repository.create("api_fields", {"name": "tenant", "project_id": project_id,
                "data": {"interface_id": interface["id"], "name": "tenant", "location": "header"}})
            repository.create("api_fields", {"name": "tenant", "project_id": project_id,
                "data": {"interface_id": 999999, "name": "tenant", "location": "query"}})
            cases = [repository.create("api_test_cases", {"name": f"case-{index}", "project_id": project_id,
                "source_id": interface["id"], "data": {"params": {"tenant": "mock-value"}}}) for index in range(2)]
            event.listen(engine, "before_cursor_execute", lambda *_: sql_threads.append(get_ident()))
            barrier = Barrier(2)

            def send(request):
                assert request["headers"]["tenant"] == "mock-value"
                assert "tenant" not in request["body"] and not request["query"]
                barrier.wait(timeout=3)
                return 200, {}, '{"code":0}'

            with patch.object(ApiCaseExecutor, "_send_http_request", side_effect=send):
                result = run_case_execution_job("API", {"case_ids": [case["id"] for case in cases]}, repository)
            assert result["success_count"] == 2
            assert set(sql_threads) == {get_ident()}
            stored, total = repository.list("execution_records", project_id=project_id)
            assert total == len(stored) == 2
            assert {record["data"]["case_id"] for record in stored} == {case["id"] for case in cases}
    finally:
        engine.dispose()
