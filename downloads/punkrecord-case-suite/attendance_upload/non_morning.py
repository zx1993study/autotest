"""Check creation and transcript import for every non-morning meeting type."""
import json
from copy import deepcopy
from datetime import date

from bootstrap import HERE, CampaignRepository, save

# isort: split
from app.db.session import SessionLocal
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.services.api_flow_scenario_service import ApiFlowScenarioService
from app.services.execution_flow_service import ExecutionFlowService
from app.services.test_case_service import TestCaseService
from inspect_target import get, sessions
from plan import EMPLOYEE, FLOW_ID, OK, binding, equal, extract, rows
from publish import refresh_auth
from run import accounts, execute_one, guarded_cleanup

TYPES = {"weekly": "周会", "project": "项目会议", "review": "复盘会议",
         "brainstorm": "头脑风暴", "other": "其他"}


def admin(node, case_id):
    node["case_id"] = case_id
    node["request"].pop("auth_id", None)
    return node


def scenario(weekly, absent, kind, day, manager_cases):
    assert kind in TYPES, "Only the five page-supported non-morning types are allowed"
    data = deepcopy(weekly)
    data["inputs"].update(meeting_type=kind, attendance_day=day)
    data.pop("latest_status", None)
    data.pop("latest_run_id", None)
    nodes = data["nodes"]
    nodes["create"]["request"]["body"].update(
        title="早会文稿链路-non-morning-" + kind + "-{{timestamp_ms}}", meeting_type="{{meeting_type}}")
    nodes["upload"]["mode"] = "skip"
    nodes["detail"]["assertions"] = deepcopy(OK) + [equal("/data/meeting_type", "{{meeting_type}}"),
        equal("/data/status", "transcribed"), equal("/data/attendees", None)]
    nodes["upload_again"] = deepcopy(absent["nodes"]["upload"])
    nodes["detail_again"] = deepcopy(absent["nodes"]["detail"])
    for key in ("upload_again", "detail_again"):
        nodes[key]["mode"] = "always"
        for rule in nodes[key]["assertions"]:
            if rule.get("path") == "/data/meeting_type":
                rule["expected"] = "{{meeting_type}}"
    for key in ("date_guard", "attendance", "attendance_again"):
        nodes[key] = admin(deepcopy(nodes["date_guard"]), manager_cases["attendance"])
        nodes[key].update(mode="always", bindings=[], extracts=[], assertions=deepcopy(OK) + [
            equal("/data/policy_active", True), rows("/data/items", {"/absent": False, "/charged": False}, 0, None)])
    baseline = admin(nodes["baseline"], manager_cases["accounts"])
    baseline.update(assertions=deepcopy(OK) + [equal("/data/is_l0", True), rows("/data/items", {}, 1, None)],
                    extracts=[extract("accounts", "/data/items")], bindings=[])
    for key in ("balance", "balance_again", "balance_restored"):
        nodes[key] = deepcopy(baseline)
        nodes[key].update(mode="always", extracts=[], bindings=[binding("baseline", "accounts")])
        nodes[key]["assertions"].append(equal("/data/items", "{{bound_accounts}}"))
    before = admin(nodes["ledger_before"], manager_cases["ledger"])
    before["request"]["query"] = {"user_id": EMPLOYEE, "page": 1}
    before.update(extracts=[extract("entries", "/data")], bindings=[], assertions=deepcopy(OK))
    for key in ("ledger", "ledger_again"):
        nodes[key] = deepcopy(before)
        nodes[key].update(mode="always", extracts=[], bindings=[binding("ledger_before", "entries")])
        nodes[key]["assertions"].append(equal("/data", "{{bound_entries}}"))
    data.update(failure_policy="stop", expected_end="balance_restored")
    return {"name": "ATT-NON-MORNING-" + kind.upper() + " " + TYPES[kind] + "创建及上传文稿均不扣款",
            "status": "active", "description": "无早会前置→创建非早会→核对全员考勤/余额与测试员工流水→上传缺席文稿→再次核对不扣款→删除本次会议",
            "data": data}


def admin_cases(repo):
    template = ExecutionFlowService(repo).get(FLOW_ID)["data"]
    existing, _ = repo.list("api_test_cases", project_id=17796, page_size=10000)
    result = {}
    for key, node_key, path in (("accounts", "baseline", "/beli/accounts"),
                                ("ledger", "ledger_before", "/beli/ledger"),
                                ("attendance", "date_guard", "/beli/attendance")):
        api_id = next(node["api_id"] for node in template["nodes"] if node["key"] == node_key)
        matches = [row for row in existing if row["source_id"] == api_id and row["status"] == "active"
                   and row["data"].get("auth_id") == 20373 and row["data"].get("requires_flow")]
        row = min(matches, key=lambda item: item["id"]) if matches else TestCaseService("API", repo).create({
            "name": "早会链路共享节点-管理员" + key, "project_id": 17796, "source_id": api_id,
            "status": "active", "assertions": OK, "data": {"method": "GET", "path": path,
                "auth_id": 20373, "requires_flow": True, "api_base_path": "/api/v1"}})
        result[key] = row["id"]
    return result


def publish(clients, day):
    saved = HERE / "non-morning-applied.json"
    with SessionLocal() as db:
        repo = CampaignRepository(SqlAlchemyResourceRepository(db))
        service = ApiFlowScenarioService(repo)
        refresh_auth(repo, clients)
        weekly = service.get_for_flow(FLOW_ID, 21144)["data"]
        absent = service.get_for_flow(FLOW_ID, 21139)["data"]
        manager_cases = admin_cases(repo)
        existing = service.list_for_flow(FLOW_ID)
        result = []
        for kind in TYPES:
            payload = scenario(weekly, absent, kind, day, manager_cases)
            matches = [row for row in existing if row["name"] == payload["name"]]
            assert len(matches) <= 1, "Duplicate configuration; inspect before publishing"
            row = service.update_for_flow(FLOW_ID, matches[0]["id"], payload) if matches else service.create_for_flow(FLOW_ID, payload)
            result.append({"id": row["id"], "kind": kind, "day": day, "name": row["name"]})
            save(saved, result)
    return result


def preflight(manager, day):
    assert get(manager, "/meeting/records", meeting_type="morning", search=day, limit=1)["total"] == 0
    policy = get(manager, "/beli/attendance", day=day)
    assert policy["policy_active"] and policy["starts_on"] <= day
    calendar = get(manager, "/beli/calendar")
    workday = next((row["is_workday"] for row in calendar if row["day"] == day), date.fromisoformat(day).weekday() < 5)
    assert workday, "Use an effective workday, so a non-workday cannot mask a meeting-type defect"
    get(manager, "/beli/ledger", user_id=EMPLOYEE, page=1)


def main():
    clients, day = sessions(), date.today().isoformat()
    manager = clients["manager"]
    preflight(manager, day)
    scenes = publish(clients, day)
    path = HERE / "non-morning-execution.json"
    report = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"runs": []}
    for scene in scenes:
        preflight(manager, day)
        baseline = accounts(manager)
        row = execute_one(scene["id"], inputs={"attendance_day": day, "meeting_type": scene["kind"]})
        result = row["data"]["results"][0]
        item = {"scene": scene, "batch_id": row["id"], "status": row["status"], "result": result}
        report["runs"].append(item)
        save(path, report)
        try:
            item["cleanup"] = guarded_cleanup(manager, result)
            item["balances_restored"] = accounts(manager) == baseline
            item["remaining_morning_meetings"] = get(manager, "/meeting/records", meeting_type="morning", search=day, limit=1)["total"]
            assert item["balances_restored"] and item["remaining_morning_meetings"] == 0, "Stop on account drift or unexpected morning meeting"
        finally:
            save(path, report)
        failed = [{"key": node["key"], "error": node.get("error"),
                   "assertions": [rule for rule in node.get("assertions", []) if not rule.get("passed")]}
                  for node in result.get("nodes", []) if node["status"] == "failed"]
        print(json.dumps({"scene_id": scene["id"], "kind": scene["kind"], "batch_id": row["id"],
                          "status": row["status"], "failed": failed}, ensure_ascii=True), flush=True)
        assert result.get("nodes"), "Stop if execution failed before sending requests"
        assert not any(node["key"] in {"date_guard", "guard", "baseline", "ledger_before"}
                       and node["status"] == "failed" for node in result["nodes"]), "Stop on invalid preconditions"


if __name__ == "__main__":
    main()
