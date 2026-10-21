"""Correct reviewed expected deltas, without weakening business assertions."""
from copy import deepcopy

from bootstrap import CampaignRepository
from plan import OK, binding
from review_common import delta

from app.db.session import SessionLocal
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.services.api_flow_scenario_service import ApiFlowScenarioService
from app.services.execution_flow_service import ExecutionFlowService


def main():
    with SessionLocal() as db:
        repository = CampaignRepository(SqlAlchemyResourceRepository(db))
        scenes = ApiFlowScenarioService(repository)
        # Explicit end-state deltas make this repair safe to run more than once.
        for scene_id, node_key, field, amount in (
                (21121, "review_node_19", "balance", -100),
                (21133, "review_node_11", "leave/annual", 0)):
            row = scenes.get_for_flow(21116, scene_id)
            data = deepcopy(row["data"])
            checks = [rule for rule in data["nodes"][node_key]["assertions"]
                      if rule.get("type") == "json_number_delta"
                      and rule.get("path") == "/data/items/0/" + field]
            assert len(checks) == 1
            checks[0]["expected"] = amount
            scenes.update_for_flow(21116, scene_id, {"data": data})
        add_task_balance_check(repository, scenes)
        repair_empty_project(scenes)


def repair_empty_project(scenes):
    row = scenes.get_for_flow(21062, 21156)
    data = deepcopy(row["data"])
    for node in data["nodes"].values():
        if node.get("request", {}).get("path", "").endswith("/sync-dev-tasks"):
            node["assertions"] = deepcopy(OK) + [
                {"type": "json_pointer", "path": "/data/" + field, "expected": 0}
                for field in ("created", "deleted", "feature_total")]
    scenes.update_for_flow(21062, 21156, {
        "name": "PROJECT-EMPTY-SYNC 空功能清单重复同步不产生任务", "data": data})


def add_task_balance_check(repository, scenes):
    flows = ExecutionFlowService(repository)
    flow = flows.get(21066)
    data = deepcopy(flow["data"])
    baseline = deepcopy(scenes.get_for_flow(21066, 21068)["data"]["nodes"]["review_node_01"])
    if not any(n["key"] == "check_no_automatic_reward" for n in data["nodes"]):
        data["nodes"].append({"key": "check_no_automatic_reward", "name": "核对验收不直接发放奖励",
                              "api_id": data["nodes"][0]["api_id"], "case_id": baseline["case_id"]})
        flows.update(21066, {"data": data})
    for scene_id in (21067, 21068, 21069, 21157):
        scenes.sync(21066, scene_id)
        row = scenes.get_for_flow(21066, scene_id)
        scene = deepcopy(row["data"])
        if scene_id in (21067, 21157):
            scene["nodes"]["review_node_01"] = deepcopy(baseline)
        source = "review_node_01"
        account = scene["nodes"][source]
        assert account["request"]["path"] == "/beli/accounts"
        case_id = scene["nodes"][source]["case_id"]
        scene["nodes"]["check_no_automatic_reward"] = {"case_id": case_id,
            "mode": "always",
            "request": {"method": "GET", "path": "/beli/accounts", "body": {}, "query": {}, "params": {},
                        "auth_id": account["request"]["auth_id"]},
            "bindings": [binding(source, "balance")], "extracts": [],
            "assertions": deepcopy(OK) + [delta("/data/items/0/balance", "{{bound_balance}}", 0)]}
        scene["expected_end"] = "check_no_automatic_reward"
        scenes.update_for_flow(21066, scene_id, {"data": scene})


if __name__ == "__main__":
    main()
