"""Batch orchestration tests use synthetic HTTP responses, never business APIs."""

from copy import deepcopy
from threading import Barrier, Lock, get_ident
from time import sleep
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.dependencies import get_resource_repository
from app.api.v1.api_cases import router
from app.core.exceptions import BusinessRuleError
from app.scheduler.jobs.api_case_executor import ApiCaseExecutor
from app.scheduler.jobs.case_execution_jobs import run_case_execution_job
from app.schemas.cases import ApiExecuteRequest
from app.schemas.testing import ApiExecuteCasesRequest
from tests.test_api_case_executor import FakeResourceRepository


class ThreadCheckedRepository(FakeResourceRepository):
    def __init__(self, count=6):
        super().__init__()
        self.owner = get_ident()
        self.reads = []
        self.items["api_test_cases"] = {
            index: {"id": index, "name": f"case-{index}", "project_id": 1, "source_id": 10,
                    "data": {"params": {"name": f"case-{index}"}}}
            for index in range(1, count + 1)
        }

    def get(self, table, item_id):
        assert get_ident() == self.owner, "Live repository read in HTTP worker"
        self.reads.append((table, item_id))
        return super().get(table, item_id)

    def list(self, table, **kwargs):
        assert get_ident() == self.owner, "Live repository query in HTTP worker"
        self.reads.append((table, kwargs))
        return super().list(table, **kwargs)

    def create(self, table, data):
        assert get_ident() == self.owner, "Live repository write in HTTP worker"
        return super().create(table, data)


def execute(repository, **config):
    return run_case_execution_job("API", {"case_ids": list(repository.items["api_test_cases"]),
                                          "config": config}, repository)


def ok_response(_request):
    return 200, {}, '{"code":0}'


def test_requests_overlap_with_bounded_workers_and_ordered_records():
    repository = ThreadCheckedRepository()
    barrier, lock = Barrier(2), Lock()
    active = maximum = 0
    worker_ids = set()

    def send(_request):
        nonlocal active, maximum
        with lock:
            worker_ids.add(get_ident())
            active += 1
            maximum = max(maximum, active)
        barrier.wait(timeout=3)
        sleep(0.01)
        with lock:
            active -= 1
        return ok_response(_request)

    with patch.object(ApiCaseExecutor, "_send_http_request", side_effect=send):
        result = execute(repository, concurrency=2)
    assert result["success_count"] == result["total"] == 6
    assert maximum == 2
    assert repository.owner not in worker_ids
    assert [record["data"]["case_id"] for record in result["records"]] == list(range(1, 7))
    assert len([read for read in repository.reads if read[0] == "api_fields"]) == 1
    assert repository.reads.count(("projects", 1)) == 1
    assert repository.reads.count(("api_interfaces", 10)) == 1


def test_default_concurrency_is_five():
    repository = ThreadCheckedRepository(5)
    barrier = Barrier(5)

    def send(request):
        barrier.wait(timeout=3)
        return ok_response(request)

    with patch.object(ApiCaseExecutor, "_send_http_request", side_effect=send):
        assert execute(repository)["success_count"] == 5


@pytest.mark.parametrize("count,concurrency", [(1, 5), (3, 1)])
def test_single_case_or_explicit_serial_stays_on_calling_thread(count, concurrency):
    repository = ThreadCheckedRepository(count)
    owners = []

    def send(request):
        owners.append(get_ident())
        return ok_response(request)

    with patch.object(ApiCaseExecutor, "_send_http_request", side_effect=send):
        assert execute(repository, concurrency=concurrency)["success_count"] == count
    assert owners == [repository.owner] * count


def test_http_failure_does_not_abort_other_cases():
    repository = ThreadCheckedRepository(3)

    def send(request):
        if request["body"]["name"] == "case-2":
            raise TimeoutError("synthetic timeout")
        return ok_response(request)

    with patch.object(ApiCaseExecutor, "_send_http_request", side_effect=send):
        result = execute(repository)
    assert result["success_count"] == 2 and result["failed_count"] == 1
    assert result["records"][1]["data"]["error"] == "synthetic timeout"
    assert len(repository.records) == 3


def test_unexpected_worker_failure_is_recorded():
    repository = ThreadCheckedRepository(2)
    with patch("app.scheduler.jobs.api_case_batch_jobs._execute_snapshot", side_effect=RuntimeError("worker error")):
        result = execute(repository)
    assert result["failed_count"] == 2
    assert all(record["data"]["error"] == "worker error" for record in result["records"])


@pytest.mark.parametrize("auth_id", ["invalid", 999])
def test_bad_saved_auth_does_not_abort_batch(auth_id):
    repository = ThreadCheckedRepository(2)
    repository.items["api_test_cases"][1]["data"]["auth_id"] = auth_id
    with patch.object(ApiCaseExecutor, "_send_http_request", side_effect=ok_response):
        result = execute(repository)
    assert result["total"] == 2 and result["failed_count"] == result["success_count"] == 1
    assert result["records"][0]["data"]["error"]


def test_interface_auth_and_import_base_path_are_preloaded_once():
    repository = ThreadCheckedRepository(2)
    repository.items["api_interfaces"][10]["data"]["auth_id"] = 80
    repository.items["project_auth"] = {80: {"id": 80, "data": {"auth_type": "bearer", "token": "mock-token"}}}
    repository.items["api_import_tasks"] = {90: {"id": 90, "project_id": 1, "data": {
        "source_type": "url", "source": "https://example.test/v3/openapi.json"}}}
    with patch.object(ApiCaseExecutor, "_send_http_request", side_effect=ok_response):
        result = execute(repository)
    assert result["success_count"] == 2
    for record in result["records"]:
        assert record["data"]["request"]["url"] == "https://example.test/v3/warehouses"
        assert record["data"]["request"]["headers"]["Authorization"] == "Bearer mock-token"
    assert repository.reads.count(("project_auth", 80)) == 1
    assert len([read for read in repository.reads if read[0] == "api_import_tasks"]) == 1


def test_dynamic_values_are_unique_and_escaped_templates_resolve_only_once():
    repository = ThreadCheckedRepository(2)
    for case in repository.items["api_test_cases"].values():
        case["data"]["params"] = {"phone": "{{random_phone}}", "literal": r"\{{random_phone}}"}
    original = deepcopy(repository.items)
    with patch.object(ApiCaseExecutor, "_send_http_request", side_effect=ok_response), \
         patch("web_automation.dynamic_values.secrets.randbelow", side_effect=[0] * 16 + [1] * 8):
        result = execute(repository)
    assert result["success_count"] == 2
    bodies = [record["data"]["request"]["body"] for record in result["records"]]
    assert len({body["phone"] for body in bodies}) == 2
    assert all(body["literal"] == "{{random_phone}}" for body in bodies)
    assert repository.items == original


def test_runtime_overrides_auth_and_multiple_projects_survive_snapshot():
    repository = ThreadCheckedRepository(3)
    repository.items["project_auth"] = {80: {"id": 80, "project_id": 1, "data": {"auth_type": "bearer", "token": "mock-token"}}}
    repository.items["projects"][2] = {"id": 2, "data": {"base_url": "https://other.test", "api_base_path": "/v2"}}
    repository.items["api_test_cases"][3]["project_id"] = 2
    repository.items["api_test_cases"][3]["data"]["skip_auth"] = True
    payload = {"case_ids": [1, 2, 3, 1], "auth_id": 80, "config": {"params": {"name": "override"}, "timeout": 7}}
    with patch.object(ApiCaseExecutor, "_send_http_request", side_effect=ok_response):
        result = run_case_execution_job("API", payload, repository)
    assert result["total"] == result["success_count"] == 3
    requests = [record["data"]["request"] for record in result["records"]]
    assert all(request["timeout"] == 7 and request["body"]["name"] == "override" for request in requests)
    assert requests[0]["headers"]["Authorization"] == "Bearer mock-token"
    assert "Authorization" not in requests[2]["headers"]
    assert requests[2]["url"] == "https://other.test/v2/warehouses"
    assert repository.reads.count(("project_auth", 80)) == 1


@pytest.mark.parametrize("model", [ApiExecuteRequest, ApiExecuteCasesRequest])
@pytest.mark.parametrize("config", [{"concurrency": 0}, {"concurrency": 11}, {"timeout": 0}, {"timeout": 301}])
def test_request_config_boundaries(model, config):
    with pytest.raises(ValidationError):
        model(case_ids=[1], config=config)


def test_direct_scheduler_rejects_invalid_config():
    with pytest.raises(BusinessRuleError):
        execute(ThreadCheckedRepository(2), concurrency=20)


@pytest.mark.parametrize("path", ["/run", "/execute"])
def test_both_api_entry_points_accept_config_and_reject_invalid_concurrency(path):
    repository = FakeResourceRepository()
    repository.items["api_test_cases"] = ThreadCheckedRepository(2).items["api_test_cases"]
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_resource_repository] = lambda: repository
    with TestClient(app) as client, patch.object(ApiCaseExecutor, "_send_http_request", side_effect=ok_response):
        response = client.post(f"/api-testing/cases{path}", json={"case_ids": [1, 2], "config": {"concurrency": 2}})
        assert response.json()["data"]["success_count"] == 2
        response = client.post(f"/api-testing/cases{path}", json={"case_ids": [1, 2], "config": {"concurrency": 11}})
        assert response.status_code == 422
