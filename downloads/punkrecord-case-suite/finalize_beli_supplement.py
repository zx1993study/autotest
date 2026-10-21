"""Verify retained remote data and reconcile supplementary coverage metadata."""
from datetime import datetime
import json
import os

import requests

from case_suite_runner import API, CN, HERE, PROJECT_ID, Platform, write_json
from supplement_beli import OUTPUT, REPORT, Supplement, money


def main():
    state = json.loads(OUTPUT.read_text(encoding="utf-8"))
    latest = {row["code"]: row for row in state["scenarios"]}
    assert len(latest) == 51 and all(row["status"] == "success" for row in latest.values())
    session = requests.Session()
    login = session.post(API + "/auth/login", json={"username": "admin", "password": os.environ["PUNKRECORD_PASSWORD"]}, timeout=25)
    login.raise_for_status()
    session.headers["Authorization"] = "Bearer " + login.json()["access_token"]

    def get(path):
        response = session.get(API + path, timeout=30)
        response.raise_for_status()
        payload = response.json()
        assert payload["code"] == 0
        return payload["data"]

    users = get("/iam/users?page_size=100&page=1")
    assert users["total"] == 22 and len(users["items"]) == 22
    pool = json.loads((HERE / "test-account-pool.json").read_text(encoding="utf-8"))
    statuses = []
    for account in pool["accounts"].values():
        user = get("/iam/users/" + account["id"])
        assert user["username"] == account["username"] and user["status"] == "inactive"
        statuses.append({"id": user["id"], "username": user["username"], "status": user["status"]})
    products = {row["id"]: row for row in get("/beli/products")}
    projects = [row for row in state["fixtures"] if row["type"] == "project"]
    for fixture in projects:
        assert get("/project/projects/" + fixture["id"])["name"] == fixture["name"]
    for fixture in state["fixtures"]:
        if fixture["type"] == "product":
            assert products[fixture["id"]]["active"] is False
            state["cleanup"].append({"type": "product", "id": fixture["id"], "status": "success",
                "action": "post-run readonly verification: already unpublished; no further mutation needed"})
    employee_id = pool["accounts"]["employee"]["id"]
    accounts = get("/beli/accounts")["items"]
    current = next(row for row in accounts if row["user_id"] == employee_id)
    assert money(current["balance"]) == money(state["reconciliation"]["final"]["balance"])
    assert money(current["frozen"]) == 0
    web = state["web_cases"][-1]
    assert web["status"] == "success" and web["mode"] == "local_headed" and web["headless"] is False
    state["post_run_verification"] = {"at": datetime.now(CN).isoformat(), "account_count": 22,
        "fixed_accounts": statuses, "current_account": current, "project_retained": projects,
        "headed_record_ids": [row["id"] for row in web["records"]], "passed": True}
    write_json(OUTPUT, state)
    reporter = object.__new__(Supplement)
    reporter.state, reporter.prefix, reporter.platform = state, state["run_prefix"], Platform()
    reporter.report()

    summary_path = HERE / "case-coverage-final.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if "pre_supplement_summary" not in summary:
        summary["pre_supplement_summary"] = {key: summary[key] for key in ("latest_scenarios", "latest_success", "latest_failure",
            "api_records_including_retests", "headed_cases", "headed_records_including_retests", "touched_points")}
    base = summary["pre_supplement_summary"]
    combined = {row["code"]: row for row in summary["scenarios"]}
    for row in latest.values():
        combined[row["code"]] = {**row, "run_file": OUTPUT.name, "run_prefix": state["run_prefix"]}
    summary["scenarios"] = list(combined.values())
    summary["latest_scenarios"] = len(combined)
    summary["latest_success"] = sum(row["status"] == "success" for row in combined.values())
    summary["latest_failure"] = sum(row["status"] != "success" for row in combined.values())
    summary["api_records_including_retests"] = base["api_records_including_retests"] + len(state["api_cases"])
    summary["headed_cases"] = base["headed_cases"] + 1
    summary["headed_records_including_retests"] = base["headed_records_including_retests"] + len(web["records"])
    for point in summary["catalog"]:
        point["evidence"] = list(dict.fromkeys(point["evidence"] + [row["code"] for row in latest.values() if point["id"] in row["case_points"]]))
        if point["id"] == "LEAVE-05":
            point["remote_status"] = "verified"
        elif point["id"] in {"TODO-07", "LEAVE-02"}:
            point["remote_status"] = "verified"
        elif point["id"] in {"TODO-04", "BELI-09"}:
            point["remote_status"] = "partial"
    summary["not_run_points"] = [point["id"] for point in summary["catalog"] if point["remote_status"] == "not_run"]
    summary["touched_points"] = len(summary["catalog"]) - len(summary["not_run_points"])
    summary["supplement"] = {"file": OUTPUT.name, "report": REPORT.name, "latest_scenarios": len(latest),
        "passed": len(latest), "failed": 0, "native_api_records": len(state["api_cases"]), "knowledge_id": state["knowledge_id"],
        "visible_reward_income": state["reconciliation"]["task_reward_gross"], "current_balance": str(money(current["balance"])),
        "note": "Concurrent HTTP and MCP RPC traces are stored separately; not counted as native execution records"}
    summary["generated_at"] = datetime.now(CN).isoformat()
    if OUTPUT.name not in summary["run_files"]:
        summary["run_files"].append(OUTPUT.name)
    write_json(summary_path, summary)
    write_json(HERE / "case-catalog.json", summary["catalog"])

    note = ("## 最新贝利补测（2026-10-19）\n\n"
        "本文件下方为补测前报告，旧数量和未验证列表属于当时快照。最新汇总以case-coverage-final.json为准。\n"
        f"新增补跑{len(latest)}个细分场景，最新全部通过；{len(state['api_cases'])}条原生API执行记录及1条有头记录19668，另有真实HTTP并发和MCP RPC证据。\n"
        "固定员工case_20261019_144610_employee期初0，任务奖励5142.46，期末5142.46，冻结0；完整流水对账通过。测试项目/任务/奖励保留，不再清理冲销。\n"
        "LEAVE-05真实MCP审批及6个仅本轮新建夹具的历史兼容场景已通过，原团队审核人下拉失败仍保留。另有29个补充分支定义，逐条标注已验证、部分验证和未执行。\n"
        "详见beli-supplement-report.md、supplement-unfinished-cases.md；平台知识19652及19484。\n\n")
    report_path = HERE / "case-final-report.md"
    old_report = report_path.read_text(encoding="utf-8")
    if old_report.startswith("## 最新贝利补测"):
        old_report = "# " + old_report.split("\n\n# ", 1)[1]
    report_path.write_text(note + old_report, encoding="utf-8")
    api = Platform()
    for knowledge_id, content in [(19124, report_path.read_text(encoding="utf-8")),
            (19125, json.dumps(summary["catalog"], ensure_ascii=False, indent=2))]:
        old = api.call("GET", f"/project-knowledge/{knowledge_id}")
        api.call("PUT", f"/project-knowledge/{knowledge_id}", {"data": {**old["data"], "content": content}})
    project = api.call("GET", f"/projects/{PROJECT_ID}")
    data = dict(project["data"])
    data["beli_supplement"] = summary["supplement"]
    data["beli_visible_employee"] = {"username": pool["accounts"]["employee"]["username"],
        "display_name": current["name"], "user_id": employee_id, "balance": str(money(current["balance"])),
        "route": "/beli", "ledger_retained": True}
    api.call("PUT", f"/projects/{PROJECT_ID}", {"data": data})
    print(json.dumps({"latest_scenarios": summary["latest_scenarios"], "success": summary["latest_success"],
        "failure": summary["latest_failure"], "touched_points": summary["touched_points"], "not_run_points": summary["not_run_points"],
        "beli_balance": str(money(current["balance"])), "fixed_accounts": statuses, "post_run_verification": True}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
