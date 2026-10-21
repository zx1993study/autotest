"""Exercise same-day meeting union and deletion without changing old meetings."""
import json
from copy import deepcopy

from bootstrap import HERE, CampaignRepository, save

from app.db.session import SessionLocal
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.services.api_flow_scenario_service import ApiFlowScenarioService
from app.services.execution_flow_service import ExecutionFlowService
from inspect_target import get, sessions
from plan import FLOW_ID
from run import DAY, accounts, execute_one, guarded_cleanup


def publish():
    saved = HERE / "multi-applied.json"
    if saved.exists():
        return json.loads(saved.read_text(encoding="utf-8"))
    with SessionLocal() as db:
        repo = CampaignRepository(SqlAlchemyResourceRepository(db))
        scenarios, flows = ApiFlowScenarioService(repo), ExecutionFlowService(repo)
        source = deepcopy(scenarios.get_for_flow(FLOW_ID, 21143)["data"])
        definition = deepcopy(flows.get(FLOW_ID)["data"])
        copies = {"create_second": "create", "attendance_after_remove": "attendance_again",
                  "balance_after_remove": "balance_again", "cleanup_second": "cleanup"}
        base = {node["key"]: node for node in definition["nodes"]}
        added = []
        for key, original in copies.items():
            node = deepcopy(base[original])
            node.update(key=key, name={"create_second": "创建同日第二场早会", "attendance_after_remove": "删除缺席会议后仍保持出席",
                                       "balance_after_remove": "仍有出席会议时不得再次扣款", "cleanup_second": "删除第二场测试会议"}[key])
            added.append(node)
        insert = next(i for i, node in enumerate(definition["nodes"]) if node["key"] == "upload_again")
        definition["nodes"].insert(insert, added[0])
        definition["nodes"][-1:-1] = added[1:]
        flows.update(FLOW_ID, {"data": definition})
        old, _ = repo.list("api_flow_scenarios", project_id=17796, page_size=10000)
        for row in old:
            if row["data"].get("flow_id") != FLOW_ID:
                continue
            scenarios.sync(FLOW_ID, row["id"])
            data = deepcopy(scenarios.get_for_flow(FLOW_ID, row["id"])["data"])
            for key in copies:
                data["nodes"][key] = {"mode": "skip"}
            scenarios.update_for_flow(FLOW_ID, row["id"], {"data": data})
        nodes = source["nodes"]
        nodes["create"]["request"]["body"]["title"] = "早会文稿链路-multi-absent-{{timestamp_ms}}"
        nodes["create_second"] = deepcopy(nodes["create"])
        nodes["create_second"]["request"]["body"]["title"] = "早会文稿链路-multi-present-{{timestamp_ms}}"
        for key in ("upload_again", "detail_again"):
            for rule in nodes[key]["bindings"]:
                if rule["source"] == "create":
                    rule["source"] = "create_second"
        for key in ("attendance_after_remove", "balance_after_remove", "cleanup_second"):
            nodes[key] = deepcopy(nodes[copies[key]])
        for rule in nodes["cleanup_second"]["bindings"]:
            if rule["source"] == "create":
                rule["source"] = "create_second"
        source.update(failure_policy="stop", expected_end="balance_restored")
        row = scenarios.create_for_flow(FLOW_ID, {
            "name": "ATT-UPLOAD-MULTI 同日多场早会取出席并集，删除缺席场次不再次扣款", "status": "active",
            "description": "创建缺席早会并扣款→创建第二场出席早会并退款→删除第一场仍不扣款→删除第二场并核对余额恢复",
            "data": source})
    scene = {"id": row["id"], "kind": "multi", "day": DAY, "name": row["name"]}
    save(saved, scene)
    return scene


def main():
    manager = sessions()["manager"]
    assert get(manager, "/meeting/records", meeting_type="morning", search=DAY, limit=1)["total"] == 0
    baseline = accounts(manager)
    scene = publish()
    row = execute_one(scene["id"])
    result = row["data"]["results"][0]
    item = {"scene": scene, "batch_id": row["id"], "status": row["status"], "result": result}
    report = {"runs": [item]}
    save(HERE / "multi-execution.json", report)
    item["cleanup"] = guarded_cleanup(manager, result)
    item["balances_restored"] = accounts(manager) == baseline
    item["remaining_meetings"] = get(manager, "/meeting/records", meeting_type="morning", search=DAY, limit=1)["total"]
    save(HERE / "multi-execution.json", report)
    assert item["balances_restored"] and item["remaining_meetings"] == 0
    print(json.dumps({"scene_id": scene["id"], "batch_id": row["id"], "status": row["status"],
                      "failed": [{"key": n["key"], "assertions": [a for a in n.get("assertions", []) if not a.get("passed")]}
                                 for n in result["nodes"] if n["status"] == "failed"]}, ensure_ascii=True), flush=True)


if __name__ == "__main__":
    main()
