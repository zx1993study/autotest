"""Remote-only supplementary cases with retained, inspectable Beli evidence."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import json
import os
import time
from uuid import uuid4

import requests

from case_suite_runner import API, BASE, CN, HERE, PROJECT_ID, SOURCE, Platform, write_json
from headed_case_runner import HeadedSuite, check, click, login, step


OUTPUT = HERE / "beli-supplement-results.json"
REPORT = HERE / "beli-supplement-report.md"


def money(value):
    return Decimal(str(value)).quantize(Decimal(".01"), rounding=ROUND_HALF_UP)


class Supplement(HeadedSuite):
    def __init__(self):
        if OUTPUT.exists():
            raise RuntimeError("Supplement output already exists; inspect/resume it instead of duplicating rewards")
        self.platform = Platform()
        self.prefix = "CASE_" + datetime.now(CN).strftime("%Y%m%d_%H%M%S")
        self.state = {"target": BASE, "project_id": PROJECT_ID, "source_commit": SOURCE,
            "run_prefix": self.prefix, "started_at": datetime.now(CN).isoformat(),
            "scenarios": [], "api_cases": [], "web_cases": [], "fixtures": [], "cleanup": [],
            "earnings": [], "concurrency": [], "mcp": [], "retention": "Keep project, tasks, rewards and ledger for UI inspection; restore fixed account statuses"}
        self.sessions, self.auth, self.user_ids, self.interfaces = {}, {}, {}, {}
        self.password, self.current = None, None
        self.pats = {}
        self.save()

    def save(self):
        write_json(OUTPUT, self.state)

    def ledger(self, actor="employee"):
        rows = []
        for page in range(1, 100):
            found = self.call(actor, "GET", f"/beli/ledger?user_id={self.user_ids[actor]}&page={page}")
            rows.extend(found)
            if len(found) < 30:
                return rows
        raise AssertionError("Ledger pagination did not terminate")

    def earned(self, label, hours, priority="p2", days=0, salary=12000):
        self.call("admin", "PUT", f"/iam/users/{self.user_ids['employee']}/salary", {"basic_salary": str(salary)})
        task_id = self.task(label, hours=hours, priority=priority, days=days)
        before = money(self.account()["balance"])
        self.complete(task_id)
        self.account(balance=before)
        expected = money(Decimal(str(salary)) / 1000 * Decimal("2.5") * Decimal(str(hours))
            * {"p0": Decimal("1.2"), "p1": Decimal(1), "p2": Decimal(1), "p3": Decimal(".8")}[priority]
            * {0: Decimal(1), 1: Decimal(".95"), 2: Decimal(".9"), 3: Decimal(".8"), 4: Decimal(".6"), 5: Decimal(".5"), 8: Decimal(".5")}[days])
        review = self.call("manager", "POST", f"/beli/rewards/{task_id}/review", {"action": "approve", "comment": label},
            equals={"data.status": "approved", "data.amount": float(expected)})
        record_id = self.current["evidence"][-1]["record_id"]
        after = money(self.account(balance=before + expected)["balance"])
        ledger = [r for r in self.ledger() if r.get("details", {}).get("todo_id") == task_id and r["kind"] == "task_reward"]
        assert len(ledger) == 1 and money(ledger[0]["amount"]) == expected, ledger
        self.state["earnings"].append({"scenario": self.current["code"], "title": label,
            "user_id": self.user_ids["employee"], "username": self.account_pool["accounts"]["employee"]["username"],
            "task_id": task_id, "reward_id": review["id"], "ledger_id": ledger[0]["id"],
            "hours": str(hours), "priority": priority, "late_days": days, "expected": str(expected),
            "actual": str(money(review["amount"])), "before": str(before), "after": str(after), "record_id": record_id})
        self.save()

    def amount_cases(self):
        for priority in ("p0", "p1", "p2", "p3"):
            for days in (0, 1, 2, 3, 4, 5, 8):
                self.scenario(f"SUP-AMOUNT-{priority}-{days}", f"保留金额证据 {priority.upper()} 延期{days}天", ["BELI-01", "BELI-02"],
                    lambda p=priority, d=days: self.earned(f"贝利边界 {p.upper()} 延期{d}天 8小时", 8, p, d))
        for label, salary, hours in [("最小工时0.01", 12000, ".01"), ("两位工时1.23", 12000, "1.23"),
                ("半分四舍五入", 200, ".01"), ("小于半分归零", 199, ".01"), ("带分工资", "12345.67", ".17")]:
            self.scenario("SUP-PRECISION-" + str(hours) + "-" + str(salary), label, ["BELI-02"],
                lambda l=label, s=salary, h=hours: self.earned(l, h, salary=s))
        self.direct("admin", "PUT", f"/iam/users/{self.user_ids['employee']}/salary", {"basic_salary": 12000})

    def exceptional_cases(self):
        def invalid_salary():
            before = self.call("admin", "GET", f"/iam/users/{self.user_ids['employee']}/salary")
            for value in (0, -1, None, ".001", "NaN", "Infinity", "10000000000.00"):
                self.call("admin", "PUT", f"/iam/users/{self.user_ids['employee']}/salary", {"basic_salary": value}, expected=422)
            self.call("admin", "GET", f"/iam/users/{self.user_ids['employee']}/salary", equals={"data.basic_salary": before["basic_salary"]})
        self.scenario("SUP-SALARY-INVALID", "工资零值、负数、空值、精度、非有限和位数上界拒绝且不改原值", ["IAM-01"], invalid_salary)

        def adjust_boundary():
            before = money(self.account()["balance"])
            body = {"amount": ".01", "reason": self.prefix + " 最小分币防重", "request_key": str(uuid4())}
            for _ in range(2):
                self.call("manager", "POST", f"/beli/accounts/{self.user_ids['employee']}/adjust", body)
            self.account(balance=before + Decimal(".01"))
            for value, expected in [(0, 400), (".001", 422), ("NaN", 422), ("Infinity", 422), ("10000000000.00", 422)]:
                self.call("manager", "POST", f"/beli/accounts/{self.user_ids['employee']}/adjust", {**body, "amount": value, "request_key": str(uuid4())}, expected=expected)
            self.adjust("-.01", reason="返还最小分币测试调整")
            self.account(balance=before)
        self.scenario("SUP-ADJUST-PRECISION", "分币调整、防重和非法精度，最终余额不变", ["BELI-06"], adjust_boundary)

        def leave_adjust():
            before = self.account()
            body = {"amount": ".5", "leave_type": "annual", "reason": self.prefix + " 半天假期防重", "request_key": str(uuid4())}
            for _ in range(2):
                self.call("manager", "POST", f"/beli/accounts/{self.user_ids['employee']}/adjust", body)
            self.account(balance=before["balance"], leave=float(before["leave"]["annual"]) + .5)
            self.call("manager", "POST", f"/beli/accounts/{self.user_ids['employee']}/adjust", {**body, "amount": 1}, expected=400)
            self.call("manager", "POST", f"/beli/accounts/{self.user_ids['employee']}/adjust", {**body, "amount": ".1", "request_key": str(uuid4())}, expected=400)
            self.adjust("-.5", reason="返还半天假期测试调整", leave_type="annual")
            self.account(balance=before["balance"], leave=before["leave"]["annual"])
        self.scenario("SUP-LEAVE-ADJUST", "假期0.5边界、防重、异参拒绝和0.1拒绝", ["BELI-06"], leave_adjust)

        def self_backfill():
            body = self.todo_body("自建零工时补录", hours=0, kind="custom")
            tid = self.call("employee", "POST", "/todo", body)["id"]
            self.state["fixtures"].append({"type": "custom_todo", "id": tid, "name": body["title"], "retained": True})
            before = money(self.account()["balance"])
            self.call("employee", "POST", f"/todo/{tid}/submit", equals={"data.status": "done"})
            self.rewards(tid)
            for _ in range(2):
                self.call("employee", "PATCH", f"/todo/{tid}", {"estimated_hours": ".01"})
            self.rewards(tid, "pending")
            self.account(balance=before)
        self.scenario("SUP-SELF-BACKFILL", "员工自建任务零工时完成后补录，只入队不发钱", ["BELI-07"], self_backfill)

    def simultaneous(self, requests_to_send):
        def send(item):
            actor, method, path, body = item
            response = requests.request(method, API + path, headers=dict(self.sessions[actor].headers), json=body, timeout=45)
            try:
                payload = response.json()
            except ValueError:
                payload = {"detail": response.text[:400]}
            return {"actor": actor, "method": method, "path": path, "http_status": response.status_code, "response": payload}
        with ThreadPoolExecutor(max_workers=len(requests_to_send)) as pool:
            result = list(pool.map(send, requests_to_send))
        self.state["concurrency"].append({"scenario": self.current["code"], "requests": result,
            "execution": "Concurrent direct HTTP to current remote service; not a native platform execution record"})
        self.save()
        return result

    def concurrency_cases(self):
        def duplicate_reward():
            tid = self.task("并发重复审批只发一次", hours=1)
            self.complete(tid)
            before = money(self.account()["balance"])
            result = self.simultaneous([("manager", "POST", f"/beli/rewards/{tid}/review", {"action": "approve"})] * 4)
            assert all(r["http_status"] == 200 for r in result), result
            self.account(balance=before + 30)
            rows = [r for r in self.ledger() if r["kind"] == "task_reward" and r.get("details", {}).get("todo_id") == tid]
            assert len(rows) == 1 and money(rows[0]["amount"]) == 30, rows
        self.scenario("SUP-CONCURRENT-REVIEW", "4个并发请求审核同一任务，只发放30一次", ["BELI-05"], duplicate_reward)

        for trial in range(3):
            def race(trial=trial):
                tid = self.task(f"归零与发奖竞争 {trial}", hours=1)
                self.complete(tid)
                before = money(self.account()["balance"])
                result = self.simultaneous([("manager", "POST", f"/beli/rewards/{tid}/review", {"action": "approve"}),
                    ("manager", "PATCH", f"/todo/{tid}", {"estimated_hours": 0})])
                assert sorted(r["http_status"] for r in result) == [200, 400], result
                task = self.call("employee", "GET", f"/todo/{tid}")
                rows = [r for r in self.ledger() if r["kind"] == "task_reward" and r.get("details", {}).get("todo_id") == tid]
                if money(task["estimated_hours"]) == 0:
                    assert not rows, rows
                    self.account(balance=before)
                else:
                    assert len(rows) == 1 and money(rows[0]["amount"]) == 30, rows
                    self.account(balance=before + 30)
            self.scenario(f"SUP-CONCURRENT-ZERO-{trial}", f"归零与发奖真实HTTP竞争第{trial + 1}轮", ["BELI-10"], race)

        def last_stock():
            body = {"name": self.prefix + " 最后一件并发测试", "kind": "physical", "price": 1, "stock": 1, "active": True}
            product = self.call("manager", "POST", "/beli/products", body)
            self.state["fixtures"].append({"type": "product", "id": product["id"], "name": body["name"], "body": body})
            before = self.account()
            result = self.simultaneous([("employee", "POST", "/beli/orders", {"product_id": product["id"], "request_key": str(uuid4()), "delivery": self.prefix + " test"}) for _ in range(2)])
            assert sorted(r["http_status"] for r in result) == [200, 400], result
            created = next(r["response"]["data"] for r in result if r["http_status"] == 200)
            self.account(balance=before["balance"], frozen=money(before["frozen"]) + 1)
            products = self.call("manager", "GET", "/beli/products")
            assert next(p for p in products if p["id"] == product["id"])["stock"] == 0
            self.call("employee", "POST", f"/beli/orders/{created['id']}/action", {"action": "cancel"})
            self.account(balance=before["balance"], frozen=before["frozen"])
            products = self.call("manager", "GET", "/beli/products")
            assert next(p for p in products if p["id"] == product["id"])["stock"] == 1
        self.scenario("SUP-CONCURRENT-STOCK", "最后一件商品并发兑换，只冻结一次且取消恢复库存", ["SHOP-02", "SHOP-03"], last_stock)

    def rpc(self, actor, name, arguments):
        if actor not in self.pats:
            token = self.direct(actor, "POST", "/auth/agent-tokens", {"name": self.prefix + " MCP", "expires_in_days": 1})
            self.pats[actor] = token
        headers = {"Authorization": "Bearer " + self.pats[actor]["token"], "Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
        payload = {"jsonrpc": "2.0", "id": str(uuid4()), "method": "tools/call", "params": {"name": name, "arguments": arguments}}
        response = requests.post(API + "/mcp/", headers=headers, json=payload, timeout=65)
        response.raise_for_status()
        if "text/event-stream" in response.headers.get("Content-Type", ""):
            events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
            result = next(event for event in events if event.get("id") == payload["id"])
        else:
            result = response.json()
        self.state["mcp"].append({"scenario": self.current["code"], "actor": actor, "tool": name, "arguments": arguments, "response": result})
        self.save()
        assert "error" not in result and not result.get("result", {}).get("isError"), result
        value = result["result"]
        if value.get("structuredContent") is not None:
            value = value["structuredContent"]
            return value.get("result", value)
        values = [json.loads(c["text"]) for c in value["content"] if c["type"] == "text"]
        if name.startswith("list_"):
            return values[0] if len(values) == 1 and isinstance(values[0], list) else values
        assert len(values) == 1, values
        return values[0]

    def mcp_leave(self):
        calendar = self.direct("employee", "GET", "/beli/calendar")
        overrides = {row["day"]: row["is_workday"] for row in calendar}
        day = datetime.now(CN).date() + timedelta(days=28)
        while not overrides.get(day.isoformat(), day.weekday() < 5):
            day += timedelta(days=1)
        before = self.account()
        todo_count = self.call("employee", "GET", "/todo/my?page_size=100")["total"]
        for approved in (True, False):
            existing = self.direct("employee", "GET", "/todo/leaves/my?status=pending&page_size=100")["items"]
            leave = next((row for row in existing if row.get("reason") == self.prefix + " MCP leave" and row["start_at"].startswith(str(day))), None)
            if leave is None:
                leave = self.rpc("employee", "create_leave", {"leave_type": "annual", "start_at": str(day) + "T10:00:00", "end_at": str(day) + "T12:00:00", "reason": self.prefix + " MCP leave"})
            leave_id = leave["id"]
            self.state["fixtures"].append({"type": "leave_audit", "id": leave_id, "name": self.prefix + " MCP leave"})
            pending = self.rpc("manager", "list_leaves_to_review", {})
            if isinstance(pending, dict):
                pending = pending.get("items", pending.get("data", []))
            assert any(item["id"] == leave_id for item in pending), pending
            result = self.rpc("manager", "approve_leave" if approved else "reject_leave", {"leave_id": leave_id, **({} if approved else {"comment": "supplement reject"})})
            assert result["status"] == ("approved" if approved else "rejected"), result
            self.call("employee", "GET", "/todo/my?page_size=100", equals={"data.total": todo_count})
            self.account(balance=before["balance"], leave=float(before["leave"]["annual"]) - .5)
            day += timedelta(days=1)
            while not overrides.get(day.isoformat(), day.weekday() < 5):
                day += timedelta(days=1)

    def reconciliation(self):
        entries = self.ledger()
        initial_ids = {row["id"] for row in self.state["initial_ledger"]}
        new = [row for row in entries if row["id"] not in initial_ids]
        assert len({r["id"] for r in entries}) == len(entries), "Duplicate ledger IDs across pages"
        assert len({r["event_key"] for r in entries}) == len(entries), "Duplicate ledger event keys"
        final = self.account()
        net = sum((money(r["amount"]) for r in new), Decimal(0))
        assert money(self.state["initial_account"]["balance"]) + net == money(final["balance"])
        assert sum((money(r["amount"]) for r in entries), Decimal(0)) == money(final["balance"])
        # Timestamp groups can contain several entries; compare the whole group rather than UUID order.
        running = Decimal(0)
        for stamp in sorted({r["created_at"] for r in entries}):
            group = [r for r in entries if r["created_at"] == stamp]
            target = running + sum((money(r["amount"]) for r in group), Decimal(0))
            assert target in {money(r["balance_after"]) for r in group}, (stamp, str(target))
            running = target
        self.state["reconciliation"] = {"user_id": self.user_ids["employee"], "initial": self.state["initial_account"], "final": final,
            "new_ledger": new, "all_ledger_count": len(entries), "new_ledger_count": len(new),
            "task_reward_gross": str(sum((money(r["amount"]) for r in new if r["kind"] == "task_reward"), Decimal(0))),
            "credits": str(sum((money(r["amount"]) for r in new if money(r["amount"]) > 0), Decimal(0))),
            "debits": str(sum((money(r["amount"]) for r in new if money(r["amount"]) < 0), Decimal(0))), "net": str(net), "passed": True}
        self.save()

    def visible_case(self):
        balance = str(money(self.state["reconciliation"]["final"]["balance"]))
        name = self.account_pool["accounts"]["employee"]["display_name"]
        self.run_case("SUP-WEB-EARNINGS", "有头查看固定员工余额、奖励金额及流水分页", ["BELI-01", "BELI-02"], "/beli",
            login() + [click("贝利"), check('.beli-heading h1:text-is("贝利")', "贝利"),
                step("select", 'select[aria-label="员工"]', name),
                check('.beli-summary > div:first-child strong', balance), check('h2:text-is("账户流水")', "账户流水"),
                check('.beli-table-wrap tbody tr:has-text("任务奖励") >> nth=0', "任务奖励"), step("click", 'button[title="下一页"]'),
                check('.beli-pager span', "第 2 页"), step("wait", "", 3000), click("任务奖励"),
                check('.beli-table-wrap tbody tr:has-text("贝利边界") >> nth=0', "贝利边界"), step("wait", "", 5000)], actor="manager")

    def cleanup(self):
        for actor, token in self.pats.items():
            try:
                self.direct(actor, "DELETE", f"/auth/agent-tokens/{token['id']}")
                self.state["cleanup"].append({"type": "agent_token", "id": token["id"], "status": "success"})
            except Exception as error:
                self.state["cleanup"].append({"type": "agent_token", "status": "failed", "error": str(error)[:300]})
        # Replays append reused users again; finish authenticated cleanup before deactivation.
        for item in sorted(self.state["fixtures"], key=lambda item: item["type"] == "user"):
            entry = {"type": item["type"], "id": item["id"], "status": "success"}
            try:
                if item["type"] == "user":
                    assert item.get("reused")
                    self.direct("admin", "PATCH", f"/iam/users/{item['id']}", {"status": item["original_status"]})
                    entry["action"] = "restored original status; account reused"
                elif item["type"] == "product":
                    self.direct("manager", "PUT", f"/beli/products/{item['id']}", {**item["body"], "active": False})
                    entry["action"] = "unpublished; audit retained"
                else:
                    entry["action"] = "retained for UI inspection; do not reopen/reverse/delete"
            except Exception as error:
                entry.update(status="failed", error=str(error)[:300])
            self.state["cleanup"].append(entry)
            self.save()

    def report(self):
        self.state["finished_at"] = datetime.now(CN).isoformat()
        latest = {row["code"]: row for row in self.state["scenarios"]}
        counts = {s: sum(row["status"] == s for row in latest.values()) for s in ("success", "failed")}
        lines = ["# 贝利补测与可见金额", "", f"目标：{BASE}；项目：{self.prefix} Project。仅复用固定3账号，没有新建账号。",
            "", "## 查看位置", "", "管理员登录远程页面，进入“贝利 → 贝利与假期”，员工选择 CASE_20261019_144610 employee；任务奖励栏目可看每项任务奖励。",
            "账号恢复原停用状态，但管理员员工列表包含停用账号，金额与流水保留。本轮测试项目及奖励不清理、不自动冲销。",
            "", f"本轮去重场景：{len(latest)}；最新通过：{counts['success']}；最新失败：{counts['failed']}；下方保留重测前失败尝试。",
            "", "## 账户核对", ""]
        rec = self.state.get("reconciliation")
        if rec:
            lines += [f"期初 {rec['initial']['balance']}；任务奖励收入 {rec['task_reward_gross']}；全部收入 {rec['credits']}；支出 {rec['debits']}；净增 {rec['net']}；期末 {rec['final']['balance']}；冻结 {rec['final']['frozen']}。",
                f"读取全量 {rec['all_ledger_count']} 条流水，新流水 {rec['new_ledger_count']} 条；唯一事件键、分页无重复、流水合计和余额一致。"]
        lines += ["", "## 逐项金额", "", "| 场景 | 应得 | 实得 | 发放前 | 发放后 | 执行记录 |", "|---|---:|---:|---:|---:|---:|"]
        lines += [f"| {r['title']} | {r['expected']} | {r['actual']} | {r['before']} | {r['after']} | {r['record_id']} |" for r in self.state["earnings"]]
        lines += ["", "## 新增场景", "", "| 编号 | 场景 | 结果 |", "|---|---|---|"]
        lines += [f"| {r['code']} | {r['title']} | {r['status']} {r.get('error', '')} |" for r in self.state["scenarios"]]
        history_passed = [row["code"] for row in latest.values() if row["code"].startswith("SUP-HISTORY-") and row["status"] == "success"]
        lines += ["", "## 历史兼容补测", "", "仅本轮新建任务按精确ID构造历史形状；不改已有业务任务和全局策略。通过：" + ("、".join(history_passed) or "尚无") + "。",
            "", "## 仍待验证", "", "BELI-09策略未初始化、缺done_at的额外组合及迁移仍未执行；已完成的历史缺字段分支见上方实际结果。",
            "ATT-01～ATT-07、SHOP-07真实早会：考勤按全体员工重算；未创建早会或修改日历，防止影响其他账号余额。SHOP-07此前只验证手工扣减后的余额保护。",
            "LEAVE-04：微信真实通道需专用绑定，未发真实微信。移动390/暗色完整组合、图片全生命周期、迁移、收费AI/ASR仍未完整覆盖。",
            "团队任务审核人下拉缺当前主管的原失败保留，未修复业务代码。本轮并发是当前远程服务真实HTTP并发，不等于后台pytest/MySQL隔离测试全套通过。",
            "", "## 保留和清理", "", "仅测试项目、任务、奖励、账本与请假审计保留；商品下架，临时MCP密钥删除，固定账号恢复运行前状态。具体ID见JSON。"]
        REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
        existing_id = self.state.get("knowledge_id")
        knowledge = self.platform.call("PUT" if existing_id else "POST", f"/project-knowledge/{existing_id}" if existing_id else "/project-knowledge", {"project_id": PROJECT_ID, "name": "贝利边界补测与用户实际收益", "status": "active",
            "data": {"domain": "WEB", "kind": "test_coverage_review", "knowledge_key": "punkrecord-beli-supplement-" + self.prefix,
                "content": "\n".join(lines), "verification_status": "partial"}})
        self.state["knowledge_id"] = knowledge["id"]
        self.save()
        print("SUPPLEMENT_REPORT", str(REPORT), "KNOWLEDGE", knowledge["id"], "COUNTS", counts, flush=True)


def main():
    suite = Supplement()
    try:
        suite.setup()
        suite.current = {"code": "SUP-BASELINE", "title": "固定账号期初余额与流水", "case_points": ["BELI-01"], "evidence": []}
        suite.state["initial_account"] = suite.account()
        suite.state["initial_ledger"] = suite.ledger()
        suite.save()
        suite.amount_cases()
        suite.exceptional_cases()
        suite.concurrency_cases()
        suite.scenario("SUP-MCP-LEAVE", "真实MCP请假待审批、批准、驳回，不创建待办", ["LEAVE-05"], suite.mcp_leave)
        suite.scenario("SUP-LEDGER-RECONCILE", "全量分页流水、唯一事件键和期初期末余额核对", ["BELI-05", "BELI-06"], suite.reconciliation)
        if suite.state.get("reconciliation"):
            suite.visible_case()
    except Exception as error:
        suite.state["fatal_error"] = str(error)[:800]
        suite.save()
        raise
    finally:
        suite.cleanup()
        suite.report()


if __name__ == "__main__":
    main()
