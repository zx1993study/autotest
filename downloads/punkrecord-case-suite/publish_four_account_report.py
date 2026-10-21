"""Publish only newly executed native evidence and reconcile visible test balances."""
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
import csv
import json
import os

import requests

import case_suite_runner as core
from account_pool import load_pool
from case_suite_runner import BASE, CN, HERE, PROJECT_ID, Platform, write_json


def main():
    core.MANAGEMENT = "http://127.0.0.1:8000/api/v1"
    platform = Platform()
    pool = load_pool()
    session = requests.Session()
    response = session.post(BASE + "/api/v1/auth/login", json={"username": "admin", "password": os.environ["PUNKRECORD_PASSWORD"]}, timeout=25)
    response.raise_for_status()
    session.headers["Authorization"] = "Bearer " + response.json()["access_token"]

    def read(path):
        result = session.get(BASE + "/api/v1" + path, timeout=30)
        result.raise_for_status()
        assert result.json()["code"] == 0
        return result.json()["data"]

    users = read("/iam/users?page_size=100")
    by_id = {u["id"]: u for u in users["items"]}
    retired = json.loads((HERE / "retired-test-account-pool.json").read_text(encoding="utf-8"))
    assert not ({u["id"] for u in retired["accounts"].values()} & by_id.keys()), "Retired users still exist"
    for actor, account in pool["accounts"].items():
        assert by_id[account["id"]]["username"] == account["username"]
        assert by_id[account["id"]]["manager_user_id"] == account["manager_user_id"]
        assert by_id[account["id"]]["status"] == "active"
    accounts = {a["user_id"]: a for a in read("/beli/accounts")["items"]}
    financial = []
    for actor in ("supervisor", "employee", "other"):
        user = pool["accounts"][actor]
        ledger = []
        for page in range(1, 100):
            batch = read(f"/beli/ledger?user_id={user['id']}&page={page}")
            ledger.extend(batch)
            if len(batch) < 30:
                break
        else:
            raise AssertionError("Ledger safety limit exceeded")
        totals = defaultdict(Decimal)
        for row in ledger:
            totals[row["kind"]] += Decimal(str(row["amount"]))
        account = accounts[user["id"]]
        total = sum(totals.values(), Decimal(0))
        financial.append({"username": user["username"], "balance": account["balance"], "frozen": account["frozen"],
            "available": account["available"], "leave": account["leave"], "ledger_count": len(ledger),
            "totals_by_kind": {key: str(value) for key, value in totals.items()},
            "ledger_amount_sum": str(total), "ledger_sum_matches_balance": total == Decimal(str(account["balance"]))})
    sets = []
    for filename, label in (("native-82-four-accounts-results.json", "82个旧API流程"),
            ("four-account-permission-results.json", "四账号层级与权限"), ("shop-rich-native-results.json", "商城丰富场景"),
            ("reward-page-four-accounts-results.json", "有头页面权限")):
        file = HERE / filename
        if not file.exists():
            sets.append({"label": label, "status": "not_run", "filename": filename, "scenarios": []})
            continue
        data = json.loads(file.read_text(encoding="utf-8"))
        latest = {s["code"]: s for s in data["scenarios"]}
        web_by_code = {w["code"]: w for w in data.get("web_cases", [])}
        for code, row in latest.items():
            if code in web_by_code:
                row["run_id"] = web_by_code[code]["task_id"]
                row["headed_mode"] = web_by_code[code].get("mode")
                row["headless"] = web_by_code[code].get("headless")
        rows = list(latest.values())
        sets.append({"label": label, "filename": filename, "scenarios": rows, "run_prefix": data["run_prefix"],
            "success": sum(r["status"] == "success" for r in rows), "total": len(rows), "cleanup_failures": [c for c in data["cleanup"] if c["status"] != "success"]})
    state = {"target": BASE, "project_id": PROJECT_ID, "generated_at": datetime.now(CN).isoformat(),
        "remaining_users": users["total"], "retired_users_absent": True, "new_users_created": 0,
        "hierarchy": "test_user1 (L0) -> test_user2 (L1) -> test_user3 / test_user4 (L2)",
        "financial": financial, "runs": [{k: v for k, v in s.items() if k != "scenarios"} for s in sets]}
    lines = ["# PunkRecord 固定四账号远程回归", "", f"生成时间：{state['generated_at']}；目标仅为 {BASE}/；平台项目 {PROJECT_ID}。",
        "", "## 账号处理", "", "已删除旧 CASE_20261019_144610 manager / employee / other 及经用户明确授权的关联测试数据。",
        "服务器备份：/home/xiaox/data/punkrecord-test-cleanup/20261019T085835Z-7b189e548213.json。autotest 历史执行报告保留。",
        "本轮未新建员工；现有账号总数19。密码不写入报告，平台页面密码参数和本机凭据均加密保存。",
        "", "test_user1 为 L0；test_user2 汇报给 test_user1；test_user3、test_user4 汇报给 test_user2。",
        "四人使用专用 API Workflow Test 业务岗位，包含 todo/project/meeting 读写及 iam.read，无管理员、工资或 iam.write 权限。",
        "test_user4 的显示名称仍为 test_requset_leave；另一个无登录名的同名 test_user3 未操作。",
        "", "## 权限结论", "", "修改前 test_user2.manager_user_id=null、level=0，后端按无上级判断 L0，因此可以进行贝利审核。",
        "补齐层级后应区分：L1主管可验收指定审核任务，但不能批准/驳回贝利奖励；只有L0可进行独立贝利审核。",
        "实际 API 与页面结论以以下新执行记录为准，不能以静态代码替代测试。",
        "", "## 执行汇总", "", "| 测试集 | 通过 | 场景数 |", "|---|---:|---:|"]
    for suite in sets:
        lines.append(f"| {suite['label']} | {suite.get('success', 0)} | {suite.get('total', '未执行')} |")
    lines += ["", "## 贝利核对", "", "余额在远程贝利页面选择对应账号查看；累计奖励与当前余额不是同一个数，后者还包含调整及兑换。",
        "", "| 账号 | 累计奖励 | 奖励冲销 | 手动调整净额 | 商品兑换 | 当前余额 | 冻结 | 可用 | 流水核对 |", "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for row in financial:
        totals = row["totals_by_kind"]
        lines.append(f"| {row['username']} | {totals.get('task_reward', '0')} | {totals.get('task_reverse', '0')} | {totals.get('manual', '0')} | {totals.get('redemption', '0')} | {row['balance']} | {row['frozen']} | {row['available']} | {'一致' if row['ledger_sum_matches_balance'] else '不一致，需调查'} |")
    lines += ["", "## 原生执行明细", "", "| 测试集 | 场景 | 标题 | 结果 | 流程 | 批次/页面任务 |", "|---|---|---|---|---:|---:|"]
    csv_rows = []
    for suite in sets:
        for row in suite["scenarios"]:
            lines.append(f"| {suite['label']} | {row['code']} | {row['title']} | {row['status']} | {row.get('flow_id', '')} | {row.get('run_id', '')} |")
            csv_rows.append({"suite": suite["label"], "code": row["code"], "title": row["title"], "status": row["status"],
                "flow_id": row.get("flow_id", ""), "run_id": row.get("run_id", ""), "error": row.get("error", "")})
            if row.get("error"):
                lines.append("\n失败说明：" + row["error"].replace("\n", " ") + "\n")
    lines += ["", "## 覆盖边界", "", "82个旧流程、商城补充、四账号权限分别计数；不能把82个流程全部通过称为cases.md全部测试点完整覆盖。",
        "本轮不创建早会、不修改全员考勤、全局日历或奖励策略，不发送真实微信，不运行本地PunkRecord业务服务。",
        "保留本轮任务、奖励、订单和账本用于页面查看；新建商品下架，固定四账号保持启用。",
        "流程模板执行后禁用以避免重复点击使用过期夹具；重新运行应通过脚本重新生成夹具。"]
    report = "\n".join(lines) + "\n"
    (HERE / "four-account-native-report.md").write_text(report, encoding="utf-8")
    with (HERE / "four-account-native-scenarios.csv").open("w", newline="", encoding="utf-8-sig") as output:
        writer = csv.DictWriter(output, fieldnames=list(csv_rows[0]) if csv_rows else ["suite", "code"])
        writer.writeheader()
        writer.writerows(csv_rows)
    publish = HERE / "four-account-native-summary.json"
    previous = json.loads(publish.read_text(encoding="utf-8")) if publish.exists() else {}
    payload = {"project_id": PROJECT_ID, "name": "固定四账号API流程、权限及商城回归报告", "status": "active",
        "data": {"domain": "API", "kind": "test_coverage_review", "knowledge_key": "punkrecord.fixed_four.native.20261019",
            "content": report, "verification_status": "partial", "target": BASE, "financial": financial}}
    result = platform.call("PUT", f"/project-knowledge/{previous['knowledge_id']}", payload) if previous.get("knowledge_id") else platform.call("POST", "/project-knowledge", payload)
    state["knowledge_id"] = result["id"]
    write_json(publish, state)
    print(json.dumps(state, ensure_ascii=True))


if __name__ == "__main__":
    main()
