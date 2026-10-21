"""Update only the existing attendance flow through the platform services."""
import json

from bootstrap import HERE, CampaignRepository, collect, fingerprint, save

from app.db.session import engine
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.services.api_flow_scenario_service import ApiFlowScenarioService
from app.services.api_request_file_service import ApiRequestFileService
from app.services.execution_flow_service import ExecutionFlowService
from app.services.project_auth_service import ProjectAuthService
from app.services.resource_service import ResourceService
from app.services.test_case_service import TestCaseService
from fixtures import MIME, change_member, speakers
from flow_reorganization.compiler import signature
from inspect_target import sessions
from plan import FLOW_ID, OK, PROJECT_ID, ROUTES, definition, scenario
from sqlalchemy.orm import Session

KINDS = ("absent", "repeat", "present", "correction", "weekly", "duplicate", "invalid")


def prepare_files(repository):
    provided = (HERE / "input" / "provided.docx").read_bytes()
    contents = {"provided": provided, "present": change_member(provided, "test_user2", True),
                "absent": change_member(provided, "test_user2", False), "invalid": b"not a Word document"}
    service = ApiRequestFileService(repository)
    files = {key: service.save(PROJECT_ID, key + ".docx", MIME, content) for key, content in contents.items()}
    names = {key: speakers(content) for key, content in contents.items() if key != "invalid"}
    assert "test_user2" in names["present"] and "test_user2" not in names["absent"]
    assert "test_user3" in names["provided"]
    return files, names


def prepare_resources(repository, interfaces):
    result = {}
    for key, (method, path, auth_id) in ROUTES.items():
        wanted = signature({"request": {"method": method, "path": path}})
        matches = [api for api in interfaces if signature({"request": api["data"]}) == wanted]
        if matches:
            api = min(matches, key=lambda row: row["id"])
        else:
            api = ResourceService("api_interfaces", repository).create({"name": "会议文稿上传", "project_id": PROJECT_ID,
                "data": {"method": method, "path": path, "module_id": 17905, "module": "meeting",
                         "api_base_path": "/api/v1", "content_type": "multipart/form-data"}})
            interfaces.append(api)
        case = TestCaseService("API", repository).create({"name": "早会链路共享节点-" + key,
            "project_id": PROJECT_ID, "source_id": api["id"], "status": "active", "assertions": OK,
            "data": {"method": method, "path": path, "auth_id": auth_id, "requires_flow": True}})
        result[key] = {"api_id": api["id"], "case_id": case["id"]}
    return result


def refresh_auth(repository, clients):
    service = ProjectAuthService(repository)
    for actor, auth_id in (("manager", 20373), ("supervisor", 20374), ("employee", 20375), ("other", 20376)):
        auth = repository.get("project_auth", auth_id)
        assert auth["project_id"] == PROJECT_ID
        service.generate_token_auth({"project_id": PROJECT_ID, "name": auth["name"], "target_auth_id": auth_id,
            "token": clients[actor].headers["Authorization"].removeprefix("Bearer "), "auth_type": "bearer",
            "login_case_type": "API", "login_case_id": auth["data"].get("login_case_id")})


def publish(db, clients):
    before = collect(db)
    old = next(flow for flow in before["execution_flows"] if flow["id"] == FLOW_ID)
    assert old["data"]["version"] == 1 and len(before["execution_flows"]) == 9
    assert not (HERE / "applied.json").exists(), "Already published; do not duplicate scenes"
    save(HERE / "before.json", before)
    raw = SqlAlchemyResourceRepository(db)
    repository = CampaignRepository(raw)
    files, names = prepare_files(repository)
    resources = prepare_resources(repository, before["api_interfaces"])
    refresh_auth(repository, clients)
    flows, scenes = ExecutionFlowService(repository), ApiFlowScenarioService(repository)
    flow = flows.update(FLOW_ID, {"status": "active", "description": "文稿上传、考勤扣款、防重、冲正及同名异常；只清理本轮会议，串行运行",
        "data": {**definition(resources), "version": old["data"]["version"]}})
    created = []
    for index, kind in enumerate(KINDS):
        payload = scenario(kind, files, names, "2026-10-21", resources)
        if index < 2:
            scene_id = (21139, 21140)[index]
            scenes.sync(FLOW_ID, scene_id)
            row = scenes.update_for_flow(FLOW_ID, scene_id, payload)
        else:
            row = scenes.create_for_flow(FLOW_ID, payload)
        created.append({"id": row["id"], "kind": kind, "name": row["name"]})
    histories = raw.get_many("api_flow_runs", [row["id"] for row in before["history"]])
    assert {row["id"]: fingerprint(row) for row in histories} == {row["id"]: row["fingerprint"] for row in before["history"]}
    for item in before["execution_flows"]:
        if item["id"] != FLOW_ID:
            assert fingerprint(raw.get("execution_flows", item["id"])) == fingerprint(item)
    return {"flow_id": FLOW_ID, "version": flow["data"]["version"], "scenarios": created,
            "resources": resources, "files": files, "names": names, "business_writes": 0}


if __name__ == "__main__":
    clients = sessions()
    with engine.connect() as connection, connection.begin(), Session(bind=connection, join_transaction_mode="create_savepoint") as db:
        result = publish(db, clients)
    save(HERE / "applied.json", result)
    print(json.dumps({"flow_id": result["flow_id"], "version": result["version"], "scenarios": result["scenarios"]}, ensure_ascii=True))
