"""Apply the reviewed configuration-only plan through existing domain services."""
import json
from copy import deepcopy
from datetime import datetime, timedelta, timezone

from inventory import HERE, PROJECT_ID, collect, fingerprint, save
from plan import NOTICE

# isort: split
from app.db.session import engine
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.schemas.api_flow_scenario import ApiFlowScenarioCreate
from app.schemas.execution_flow import ExecutionFlowCreate
from app.services.api_flow_scenario_service import ApiFlowScenarioService
from app.services.execution_flow_service import ExecutionFlowService
from app.services.test_case_service import TestCaseService
from sqlalchemy.orm import Session


class CachedRepository:
    def __init__(self, repository, snapshot):
        self.repository = repository
        self.cache = {(table, row["id"]): row for table, rows in snapshot.items()
                      if table not in {"history", "project"} for row in rows}
        self.cache[("projects", PROJECT_ID)] = snapshot["project"]

    def __getattr__(self, name):
        return getattr(self.repository, name)

    def get(self, table, item_id):
        key = table, item_id
        if key not in self.cache:
            self.cache[key] = self.repository.get(table, item_id)
        return deepcopy(self.cache[key])

    def create(self, table, payload):
        row = self.repository.create(table, payload)
        self.cache[(table, row["id"])] = row
        return row


def assert_originals(repository, before):
    for table in ("execution_flows", "api_flow_scenarios", "api_test_cases", "api_interfaces"):
        ids = [r["id"] for r in before[table]]
        live = repository.get_many(table, ids)
        assert fingerprint(sorted(live, key=lambda r: r["id"])) == fingerprint(sorted(before[table], key=lambda r: r["id"])), f"Concurrent edit: {table}"


def verify_history(repository, before):
    history = repository.get_many("api_flow_runs", [r["id"] for r in before["history"]])
    assert {r["id"]: fingerprint(r) for r in history} == {r["id"]: r["fingerprint"] for r in before["history"]}, "Historical runs changed"
    rows = repository.get_many("api_test_cases", [r["id"] for r in before["api_test_cases"]])
    assert fingerprint(sorted(rows, key=lambda r: r["id"])) == fingerprint(sorted(before["api_test_cases"], key=lambda r: r["id"])), "Original API cases changed"


def apply(db, before, plan):
    repository = SqlAlchemyResourceRepository(db)
    live = collect(db)
    assert fingerprint(live) == plan["source_fingerprint"] == fingerprint(before), "Inventory changed; create a new reviewed plan"
    cached = CachedRepository(repository, before)
    cases = TestCaseService("API", cached)
    flows = ExecutionFlowService(cached)
    scenarios = ApiFlowScenarioService(cached)
    result = {"project_id": PROJECT_ID, "configuration_only": True, "business_requests": 0, "groups": [], "base_cases": {}}
    for key, payload in plan["base_cases"].items():
        auth = repository.get("project_auth", payload["data"]["auth_id"])
        assert auth and auth["project_id"] == PROJECT_ID, "Invalid project authentication"
        # Shared node definitions must not become standalone bulk execution targets.
        result["base_cases"][key] = cases.create({**payload, "status": "disabled"})["id"]
    for group in plan["groups"]:
        flow_payload = ExecutionFlowCreate.model_validate({"project_id": PROJECT_ID, "name": group["name"],
            "description": group["description"], "status": "disabled", "data": group["definition"]}).model_dump(exclude_none=True)
        flow = flows.create(flow_payload)
        row = {"key": group["key"], "id": flow["id"], "name": flow["name"], "status": flow["status"], "scenarios": []}
        for branch in group["branches"]:
            data = deepcopy(branch["compiled"])
            for override in data["nodes"].values():
                if "case_key" in override:
                    override["case_id"] = result["base_cases"][override.pop("case_key")]
            description = (branch.get("description") or "") + "。" + NOTICE
            description += " 原流程#" + str(branch["source_flow_id"]) + "，原场景#" + str(branch["source_scene_id"]) + "。"
            if branch.get("prerequisites"):
                description += "前置：" + "；".join(branch["prerequisites"])
            payload = ApiFlowScenarioCreate.model_validate({"name": branch["name"], "description": description,
                                                           "status": "disabled", "data": data}).model_dump()
            scene = scenarios.create_for_flow(flow["id"], payload)
            assert not ({"latest_status", "latest_run_id"} & scene["data"].keys())
            row["scenarios"].append({"id": scene["id"], "name": scene["name"],
                "source_flow_id": branch["source_flow_id"], "source_scene_id": branch["source_scene_id"]})
        result["groups"].append(row)
    assert_originals(repository, before)
    # Domain deletion soft-deletes child scenarios but never deletes run history.
    count = ExecutionFlowService(repository).batch_delete([r["id"] for r in before["execution_flows"]])
    assert count["deleted_count"] == len(before["execution_flows"])
    verify_history(repository, before)
    remaining, total = repository.list("execution_flows", project_id=PROJECT_ID, page_size=10000)
    scenes, scene_total = repository.list("api_flow_scenarios", project_id=PROJECT_ID, page_size=10000)
    assert total == len(plan["groups"]) and scene_total == sum(len(g["branches"]) for g in plan["groups"])
    assert all(r["status"] == "disabled" for r in [*remaining, *scenes])
    result.update(old_flows_removed=count["deleted_count"], api_only_flows=sum(d["destination"] == "api" for d in plan["decisions"]),
                  workflows=total, scenarios=scene_total, preserved_runs=len(before["history"]), preserved_api_cases=len(before["api_test_cases"]),
                  applied_at=datetime.now(timezone(timedelta(hours=8))).isoformat())
    return result


if __name__ == "__main__":
    before = json.loads((HERE / "before.json").read_text(encoding="utf-8"))
    plan = json.loads((HERE / "plan.json").read_text(encoding="utf-8"))
    assert not (HERE / "applied.json").exists(), "Already applied; do not create duplicate flows"
    # Repository commits release savepoints, not the owning MySQL transaction.
    with engine.connect() as connection, connection.begin(), Session(bind=connection, join_transaction_mode="create_savepoint") as db:
        result = apply(db, before, plan)
    save(HERE / "applied.json", result)
    print(json.dumps({k: v for k, v in result.items() if k not in {"groups", "base_cases"}}, ensure_ascii=True))
