"""Publish the reviewed scene definitions through existing platform services."""
import json

from bootstrap import HERE, CampaignRepository, collect, save
from flow_reorganization.compiler import signature
from inspect_target import sessions
from publish import refresh_auth
from review_plan import build

from app.db.session import engine
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.services.api_flow_scenario_service import ApiFlowScenarioService
from app.services.execution_flow_service import ExecutionFlowService
from app.services.resource_service import ResourceService
from app.services.test_case_service import TestCaseService
from sqlalchemy.orm import Session


def resources(repository, groups, snapshot):
    shared, apis = {}, {}
    original_shared = json.loads((HERE.parent / "flow_reorganization" / "applied.json").read_text(encoding="utf-8"))["base_cases"]
    for group in groups:
        for branch in group["branches"]:
            for step in branch["steps"]:
                route, auth = signature(step), step["auth_id"]
                key = repr((route, auth))
                if step["api_id"] < 0 and route not in apis:
                    api = ResourceService("api_interfaces", repository).create({"project_id": 17796,
                        "name": "流程清理 " + route[0] + " " + route[1], "data": {
                            "method": route[0], "path": route[1], "api_base_path": "/api/v1", "module_id": 17905}})
                    apis[route] = api["id"]
                api_id = apis.get(route, step["api_id"])
                if key in shared:
                    continue
                payload = {"name": "业务链路共享节点 " + route[0] + " " + route[1] + " / " + str(auth),
                    "project_id": 17796, "source_id": api_id, "status": "active", "assertions": [],
                    "data": {"method": route[0], "path": route[1], "auth_id": auth,
                             "requires_flow": True, "api_base_path": "/api/v1", "content_type": "application/json"}}
                service = TestCaseService("API", repository)
                if key in original_shared:
                    row = service.update(original_shared[key], payload)
                else:
                    row = service.create(payload)
                shared[key] = row["id"]
    for group in groups:
        for item in group["definition"]["nodes"]:
            if item["api_id"] < 0:
                route = signature({"request": {"method": item["name"].split(" ", 1)[0], "path": item["name"].split(" ", 1)[1]}})
                item["api_id"] = apis[route]
    return shared


def apply(db, clients):
    assert not (HERE / "review-applied.json").exists(), "Already published"
    snapshot = collect(db)
    save(HERE / "review-before.json", snapshot)
    groups = build(snapshot)
    raw = SqlAlchemyResourceRepository(db)
    repository = CampaignRepository(raw)
    refresh_auth(repository, clients)
    for table in ("execution_flows", "api_flow_scenarios", "api_test_cases", "api_interfaces"):
        for row in snapshot[table]:
            repository.cache[(table, row["id"])] = row
    cases = resources(repository, groups, snapshot)
    result = []
    for group in groups:
        flow = ExecutionFlowService(repository).update(group["id"], {"status": "active",
            "description": "按业务状态分支回归；新建隔离夹具、动态余额差额断言；串行执行，保留历史运行记录",
            "data": {**group["definition"], "version": group["version"]}})
        scenes = ApiFlowScenarioService(repository)
        for branch in group["branches"]:
            data = branch["compiled"]
            for item in data["nodes"].values():
                if "case_key" in item:
                    item["case_id"] = cases[item.pop("case_key")]
            payload = {"name": branch["name"], "status": "active", "description": "独立业务链路；只使用本轮新建业务ID；执行前记录余额，执行后清理；新增/拒绝/状态及数值断言均保留",
                       "data": data}
            if branch["id"]:
                scenes.sync(group["id"], branch["id"])
                row = scenes.update_for_flow(group["id"], branch["id"], payload)
            else:
                row = scenes.create_for_flow(group["id"], payload)
            result.append({"flow_id": flow["id"], "group": group["group"], "scene_id": row["id"],
                           "name": row["name"], "added": branch["id"] is None})
    return result


if __name__ == "__main__":
    clients = sessions()
    with engine.connect() as connection, connection.begin(), Session(bind=connection, join_transaction_mode="create_savepoint") as db:
        result = apply(db, clients)
    save(HERE / "review-applied.json", result)
    print(json.dumps({"scenes": len(result), "added": [item for item in result if item["added"]]}, ensure_ascii=True))
