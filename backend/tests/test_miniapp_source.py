from copy import deepcopy
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.dependencies import get_resource_repository
from app.api.exception_handlers import register_exception_handlers
from app.api.v1.miniapp_source_actions import router
from app.core.exceptions import BusinessRuleError
from app.scheduler.jobs.miniapp_source_executor import execute_source_case
from app.schemas.miniapp_source import (
    SourceBusinessBinding,
    SourceCatalogImport,
    SourceRunRequest,
)
from app.services.case_execution_dispatcher import CaseExecutionDispatcher
from app.services.miniapp_source_run_service import MiniappSourceRunService
from app.services.miniapp_source_service import MiniappSourceService
from tests.test_api_flows import MemoryRepository


@pytest.fixture
def repository():
    repo = MemoryRepository()
    repo.create_many = lambda table, rows: [repo.create(table, row) for row in rows]
    repo.create("projects", {"name": "Test project", "data": {}})
    return repo


@pytest.fixture
def catalog():
    return {"project_id": 1, "metadata": {"schema_version": 1, "source": {
        "repository": "https://github.com/example/miniapp", "revision": "a" * 40}}, "cases": [{
            "id": "login-render", "title": "Login render", "route": "pages/login/index", "platforms": ["h5", "mp-weixin"],
            "category": "render", "automation": "scripted", "requires_auth": False, "requires_fixture": False,
            "risk": "read", "steps": ["Open login"], "expected": ["Root visible"],
            "operations": [{"action": "visible", "selector": ".login"}]}]}


def imported(repository, catalog):
    result = MiniappSourceService(repository).import_catalog(SourceCatalogImport.model_validate(catalog))
    return repository.get("miniapp_test_cases", result["case_ids"][0])


def test_import_is_idempotent_and_preserves_existing_changes(repository, catalog):
    service = MiniappSourceService(repository)
    first = service.import_catalog(SourceCatalogImport.model_validate(catalog))
    case_id = first["case_ids"][0]
    repository.update("miniapp_test_cases", case_id, {"name": "User edit"})
    second = service.import_catalog(SourceCatalogImport.model_validate(catalog))
    assert first["created_pages"] == first["created_cases"] == 1
    assert second["created_cases"] == 0 and second["skipped_cases"] == 1
    assert repository.get("miniapp_test_cases", case_id)["name"] == "User edit"
    changed = deepcopy(catalog)
    changed["cases"][0]["expected"] = ["New assertion"]
    assert service.import_catalog(SourceCatalogImport.model_validate(changed))["conflicts"] == [
        {"source_id": "login-render", "case_id": case_id}]


def test_same_route_uses_one_page_and_project_imports_remain_separate(repository, catalog):
    catalog["cases"].append({**catalog["cases"][0], "id": "second"})
    first = MiniappSourceService(repository).import_catalog(SourceCatalogImport.model_validate(catalog))
    assert first["created_pages"] == 1 and first["created_cases"] == 2
    other = repository.create("projects", {"name": "Other"})
    catalog["project_id"] = other["id"]
    assert MiniappSourceService(repository).import_catalog(SourceCatalogImport.model_validate(catalog))["created_cases"] == 2


@pytest.mark.parametrize("change", ["duplicate", "route", "action", "missing-operations", "revision"])
def test_invalid_catalog_is_rejected(catalog, change):
    if change == "duplicate":
        catalog["cases"].append(catalog["cases"][0])
    elif change == "route":
        catalog["cases"][0]["route"] = "../../other"
    elif change == "action":
        catalog["cases"][0]["operations"][0]["action"] = "evaluate"
    elif change == "missing-operations":
        catalog["cases"][0]["operations"] = []
    else:
        catalog["metadata"]["source"]["revision"] = "latest"
    with pytest.raises(ValidationError):
        SourceCatalogImport.model_validate(catalog)


@pytest.mark.parametrize("platform,base_url,field,value,reason", [
    ("mp-weixin", None, None, None, "uni-automator"),
    ("h5", None, None, None, "miniapp_h5_url"),
    ("h5", "file:///tmp/", None, None, "配置无效"),
    ("h5", "http://localhost", "requires_auth", True, "登录态"),
    ("h5", "http://localhost", "requires_fixture", True, "归属"),
    ("h5", "http://localhost", "risk", "write", "业务写入"),
    ("h5", "http://localhost", "automation", "manual", "人工步骤"),
])
def test_missing_prerequisites_never_count_as_pass(repository, catalog, platform, base_url, field, value, reason):
    if field:
        catalog["cases"][0][field] = value
    case = imported(repository, catalog)
    with patch("app.scheduler.jobs.miniapp_source_executor._run_h5") as browser:
        result = execute_source_case(case, platform, base_url)
    assert result["status"] == "blocked" and result["executed"] is False
    assert reason in result["reason"]
    browser.assert_not_called()


def test_ui_assertion_failure_and_secrets_are_not_silently_passed(repository, catalog):
    case = imported(repository, catalog)
    with patch("app.scheduler.jobs.miniapp_source_executor._run_h5", side_effect=RuntimeError("secret=private")):
        result = execute_source_case(case, "h5", "http://localhost")
    assert result["status"] == "failed"
    assert "private" not in result["reason"]
    with patch("app.scheduler.jobs.miniapp_source_executor._run_h5"):
        assert execute_source_case(case, "h5", "http://localhost")["status"] == "success"


def test_legacy_executor_refuses_source_catalog(repository, catalog):
    case = imported(repository, catalog)
    with pytest.raises(BusinessRuleError, match="Appium"):
        CaseExecutionDispatcher(repository).execute("MINIAPP", {"case_ids": [case["id"]]})


def test_run_snapshots_and_blocked_records_are_persisted(repository, catalog):
    case = imported(repository, catalog)
    service = MiniappSourceRunService(repository)
    with patch("app.scheduler.jobs.miniapp_source_jobs.submit_source_run") as submit:
        batch = service.create_run(SourceRunRequest(project_id=1, case_ids=[case["id"], case["id"]]))
        snapshots = submit.call_args.args[1]
    assert len(snapshots) == 1
    repository.update("miniapp_test_cases", case["id"], {"name": "Changed later"})
    result = execute_source_case(snapshots[0], "mp-weixin", None)
    saved = service.finish(batch["id"], [result])
    assert saved["status"] == "blocked" and saved["data"]["counts"] == {"blocked": 1}
    assert saved["data"]["results"][0]["name"] == "Login render"
    assert repository.list("execution_records")[0][0]["status"] == "blocked"


def test_business_binding_validates_project(repository, catalog):
    case = imported(repository, catalog)
    flow = repository.create("execution_flows", {"name": "Flow", "project_id": 1, "data": {"version": 1, "nodes": []}})
    scene = repository.create("api_flow_scenarios", {"name": "Scene", "project_id": 1, "data": {"flow_id": flow["id"]}})
    service = MiniappSourceService(repository)
    payload = SourceBusinessBinding(flow_id=flow["id"], scenario_id=scene["id"])
    saved = service.bind_business(case["id"], payload)
    assert saved["data"]["api_business"]["scenario_id"] == scene["id"]
    repository.update("api_flow_scenarios", scene["id"], {"project_id": 2})
    with pytest.raises(BusinessRuleError, match="同一项目"):
        service.bind_business(case["id"], payload)


def test_run_refuses_invalid_edited_definition_before_queueing(repository, catalog):
    case = imported(repository, catalog)
    repository.update("miniapp_test_cases", case["id"], {"data": {**case["data"], "definition": {}}})
    with pytest.raises(BusinessRuleError, match="源码定义无效"):
        MiniappSourceRunService(repository).create_run(SourceRunRequest(project_id=1, case_ids=[case["id"]]))


def test_routes_and_restart_status(repository, catalog):
    app = FastAPI()
    app.include_router(router)
    register_exception_handlers(app)
    app.dependency_overrides[get_resource_repository] = lambda: repository
    with TestClient(app) as client:
        prefix = "/miniapp-testing/cases/source"
        response = client.post(prefix + "/import", json=catalog)
        assert response.status_code == 200
        case_id = response.json()["data"]["case_ids"][0]
        with patch("app.scheduler.jobs.miniapp_source_jobs.submit_source_run"):
            run = client.post(prefix + "/runs", json={"project_id": 1, "case_ids": [case_id]}).json()["data"]
        detail = client.get(f"{prefix}/runs/{run['id']}").json()["data"]
        assert detail["status"] == "interrupted"
        assert "results" not in client.get(prefix + "/runs?project_id=1").json()["data"][0]["data"]
        assert client.post(prefix + "/runs", json={"project_id": 2, "case_ids": [case_id]}).status_code == 404
