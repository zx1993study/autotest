"""Headed native autotest cases against remote PunkRecord only."""
import json
import argparse
import os
from pathlib import Path
import time
from datetime import datetime, timedelta

from case_suite_runner import Suite, HERE, BASE, PROJECT_ID, CN, SOURCE, write_json


def step(action, locator, value=None, expected=None, kind="css"):
    result = {"action": action, "locator_type": kind, "locator": locator, "name": locator, "require_unique": True}
    if value is not None:
        result["value"] = value
    if expected is not None:
        result["expected"] = expected
    return result


def click(text):
    return step("click", f'button:has-text("{text}")')


def check(selector, text=""):
    return step("assert", selector, expected=text)


def login():
    return [step("fill", "用户名", "{{username}}", kind="label"),
            step("fill", "密码", "{{password}}", kind="label"),
            step("click", 'button[type="submit"]'), check('h1:text-is("工作台")', "工作台")]


class HeadedSuite(Suite):
    def save(self):
        write_json(HERE / "case-headed-results.json", self.state)

    def run_case(self, code, title, points, route, steps, actor="employee", limitation=None):
        if self.state.get("selected_scenarios") and code not in self.state["selected_scenarios"]:
            return
        self.current = {"code": code, "title": title, "case_points": points, "status": "running", "evidence": []}
        if limitation:
            self.current["coverage_limit"] = limitation
        self.state["scenarios"].append(self.current)
        self.save()
        pages = self.platform.call("GET", f"/web-testing/page-groups?project_id={PROJECT_ID}&pageSize=200")["items"]
        page = next((p for p in pages if p.get("data", {}).get("route", p.get("route")) == route
                     or p.get("data", {}).get("url", p.get("url", "")).rstrip("/") == (BASE + route).rstrip("/")), None)
        if page is None:
            page = self.platform.call("POST", "/web-testing/page-groups", {
                "project_id": PROJECT_ID, "name": "cases.md " + code, "route": route,
                "url": BASE + route, "status": "active", "description": ".agent/test/cases.md " + ",".join(points)})
        params = [{"key": "username", "label": "用户名", "type": "text", "required": True,
                   "locator_type": "label", "locator": "用户名", "confirmed": True},
                  {"key": "password", "label": "密码", "type": "password", "required": True,
                   "locator_type": "label", "locator": "密码", "confirmed": True}]
        feature = self.platform.call("POST", f"/web-testing/page-groups/{page['id']}/features", {
            "name": "CASE " + code + " " + title, "feature_type": "query", "parameters": params,
            "description": ".agent/test/cases.md " + ",".join(points) + "; remote only; " + (limitation or ""),
            "candidate": {"name": title, "steps": steps, "variables": {}, "input_info": {}}})
        username = self.account_pool["accounts"][actor]["username"]
        fixture = next(u for u in self.state["fixtures"] if u["type"] == "user" and u["username"] == username)
        case = self.platform.call("POST", f"/web-testing/features/{feature['id']}/input-cases", {
            "name": "CASE " + code + " " + title, "input_info": {"username": fixture["username"], "password": self.password},
            "priority": "P1", "status": "active", "script_version": feature["data"]["script_version"]})
        record = {"code": code, "case_id": case["id"], "feature_id": feature["id"], "page_id": page["id"], "steps": steps}
        self.state["web_cases"].append(record)
        self.save()
        task = self.platform.call("POST", f"/web-testing/features/{feature['id']}/run", {
            "case_ids": [case["id"]], "node_key": "local-win-01", "headless": False,
            "approve_side_effects": True, "record_video": False})
        record["task_id"] = task["agent_task_id"]
        self.save()
        print("RUN HEADED", code, record["task_id"], flush=True)
        deadline = time.monotonic() + 240
        while time.monotonic() < deadline:
            task = self.platform.call("GET", f"/agent/tasks/{record['task_id']}")
            if task["status"] not in ("pending", "running"):
                payload = task.get("data", {}).get("payload", {})
                execution = payload.get("execution", {})
                config = execution.get("config", payload.get("config", {}))
                records = task.get("data", {}).get("saved_records") or (task.get("data", {}).get("result") or {}).get("records", [])
                record.update(status=task["status"], mode=execution.get("mode", payload.get("mode")), headless=config.get("headless"),
                    records=[{"id": r.get("id"), "status": r["status"], "error": r.get("data", {}).get("error")} for r in records])
                self.current["status"] = task["status"]
                self.current["evidence"] = [{"record_id": r.get("id"), "case_id": case["id"], "status": r["status"]} for r in records]
                if task["status"] != "success":
                    self.current["error"] = str(task.get("data", {}).get("error") or record["records"])
                    if code == "TODO08-team":
                        rows = self.direct("manager", "GET", "/todo/team?status=open&page_size=100&reviewed_by_user_id=" + self.user_ids["manager"])
                        self.current["api_diagnostic"] = {"total": rows["total"], "own_items": [r for r in rows["items"] if r["title"].startswith(self.prefix + " ")]}
                    if code == "TODO06-pagination":
                        rows = self.direct("employee", "GET", "/todo/my?status=done&page_size=10")
                        self.current["api_diagnostic"] = {"total": rows["total"], "items": [{"id": r["id"], "title": r["title"], "done_at": r["done_at"]} for r in rows["items"]]}
                assert record["headless"] is False and record["mode"] == "local_headed", "Headed mode not confirmed"
                self.save()
                print("FINISH HEADED", code, task["status"], self.current.get("error", ""), flush=True)
                return
            time.sleep(2)
        raise TimeoutError(f"Agent task {record['task_id']} is not finished")

    def fixtures(self):
        self.colored = self.prefix + " Positive hours"
        self.plain = self.prefix + " Zero hours"
        self.direct("manager", "POST", "/todo", self.todo_body("Positive hours", hours=1.25))
        self.direct("manager", "POST", "/todo", self.todo_body("Zero hours", hours=0))
        self.done_titles = []
        for number in range(12):
            task = self.direct("manager", "POST", "/todo", self.todo_body(f"Done {number:02}", hours=0))
            self.direct("employee", "POST", f"/todo/{task['id']}/submit")
            self.direct("manager", "POST", f"/todo/{task['id']}/approve")
            self.done_titles.append(task["title"])
        self.bug_title = self.prefix + " CaseMixed Bug"
        self.direct("manager", "POST", "/todo", self.todo_body("CaseMixed Bug", kind="bug"))
        meeting = self.direct("manager", "POST", "/meeting/records", data={
            "title": self.prefix + " Meeting", "meeting_type": "project", "meeting_date": datetime.now(CN).date().isoformat()})
        self.mid = meeting["id"]
        self.state["fixtures"].append({"type": "meeting", "id": self.mid, "name": meeting["title"]})
        self.direct("manager", "PATCH", f"/meeting/records/{self.mid}/transcript", {
            "replace": True, "segments": [{"speaker_id": "speaker_1", "content": "Remote transcript test", "start_time": 0, "end_time": 1, "segment_index": 0}]})
        self.save()

    def cases(self):
        card = f'.todo-card:has-text("{self.colored}")'
        plain = f'.todo-card:has-text("{self.plain}")'
        item = f'.todo-item:has-text("{self.colored}")'
        steps = login() + [click("待办事项"), check('h1:text-is("我的任务")', "我的任务"),
            check(card + '.beli-task .beli-task-badge', "贝利任务"),
            check(plain + ':not(.beli-task):not(:has(.beli-task-badge))', self.plain), click("全部列表"),
            check(item + '.beli-task', self.colored), step("click", item), click("编辑"),
            step("fill", "#estimated_hours", "0"), step("click", '.todo-editor button[type="submit"]'),
            check(item + ':not(.beli-task):not(:has(.beli-task-badge))', self.colored),
            step("click", item), click("编辑"), step("fill", "#estimated_hours", "1.25"),
            step("click", '.todo-editor button[type="submit"]'), check(item + '.beli-task .beli-task-badge', "贝利任务")]
        self.run_case("TODO08-my-edit", "我的任务看板/列表与工时归零恢复标识", ["TODO-08"], "/todo", steps,
                      limitation="当前Agent标准桌面视口；390手机、暗色和计算颜色值未覆盖")
        self.run_case("TODO08-team", "团队任务看板和列表的贝利/普通样式分类", ["TODO-08"], "/todo",
            login() + [click("待办事项"), step("wait", "", 1000), click("团队任务"), check('h1:text-is("团队任务")', "团队任务"),
                step("wait", "", 1200), step("select", '.filter-select-item:has(span:text-is("审核人")) select', self.account_pool["accounts"]["manager"]["display_name"]),
                check(card + '.beli-task .beli-task-badge', "贝利任务"),
                check(plain + ':not(.beli-task)', self.plain), click("全部列表"), check(item + '.beli-task', self.colored)], actor="manager",
            limitation="暗色与手机组合未覆盖")
        self.run_case("TODO06-pagination", "完成任务默认10条，加载更多到12条", ["TODO-06", "TODO-08"], "/todo",
            login() + [click("待办事项"), step("click", '.column-header:has(h3:text-is("已完成"))'),
                check('.column-header:has(h3:text-is("已完成")) .count-badge:text-is("10/12")', "10/12"),
                check(f'.todo-card.done:has-text("{self.done_titles[-1]}")', self.done_titles[-1]),
                click("加载更多"), check('.column-header:has(h3:text-is("已完成")) .count-badge:text-is("12/12")', "12/12"),
                check(f'.todo-card.done:has-text("{self.done_titles[0]}")', self.done_titles[0])],
            limitation="API时间排序已有隔离单测；页面验证首批数量及加载更多")
        self.run_case("BUG02-filter-refresh", "独立Bug页面标题搜索、状态筛选和刷新保持", ["BUG-01", "BUG-02", "BUG-03"], "/project",
            login() + [click("项目管理"), step("click", f'.project-card:has-text("{self.prefix} Project")'),
                click("Bug管理"), step("fill", '[aria-label="搜索Bug标题"]', "casemixed"),
                check(':text-is("第 1 页 · 共 1 项")', "共 1 项"),
                step("select", '[aria-label="Bug状态"]', "done"), check(':text-is("第 1 页 · 共 0 项")', "共 0 项"),
                step("click", '[aria-label="刷新"]'), check(':text-is("第 1 页 · 共 0 项")', "共 0 项"),
                step("select", '[aria-label="Bug状态"]', ""), check(':text-is("第 1 页 · 共 1 项")', "共 1 项")], actor="manager",
            limitation="浏览器前进后退、URL字符串、30项分页和图片完整生命周期未执行")
        self.run_case("MEET02-speaker-corrected", "说话人识别编辑姓名并自动同步参会人员", ["GENERAL-MEETING"], "/meeting",
            login() + [click("会议记录"), step("click", f'.meeting-row:has-text("{self.prefix} Meeting")'),
                check('.speaker-mapping-panel', "说话人识别"), step("fill", '.speaker-name-input', self.prefix + " Attendee"),
                step("click", 'h2:text-is("转录文本")'), check('.meeting-detail-attendees', self.prefix + " Attendee")], actor="manager",
            limitation="修正历史MEET-002脚本错误，不将错误输入框定位归为业务缺陷")
        actual = self.direct("manager", "GET", f"/meeting/records/{self.mid}")
        self.state["meeting_persistence"] = {"id": self.mid, "attendees": actual["attendees"], "speaker_mapping": actual["speaker_mapping"]}
        self.save()

    def cleanup(self):
        for item in self.state["fixtures"]:
            if item["type"] == "meeting":
                try:
                    self.direct("manager", "DELETE", f"/meeting/records/{item['id']}")
                    item["type"] = "meeting_deleted"
                except Exception as error:
                    self.state["cleanup"].append({"type": "meeting", "status": "failed", "error": str(error)[:300]})
        super().cleanup()

    def report(self):
        self.state["finished_at"] = datetime.now(CN).isoformat()
        self.save()
        rows = self.state["scenarios"]
        content = ["# cases.md 有头页面补充测试", "", f"远程目标：{BASE}/；平台项目 {PROJECT_ID}；前缀 {self.prefix}。",
            "所有页面任务请求 headless=false，并逐条核对实际执行 local_headed。密码参数由平台加密，禁用截图和录屏。",
            "", "| 场景 | 原测试点 | 结果 | 任务 | 执行记录 | 限制 |", "|---|---|---|---|---|---|"]
        for scenario, web in zip(rows, self.state["web_cases"]):
            content.append(f"| {scenario['code']} | {','.join(scenario['case_points'])} | {scenario['status']} | {web['task_id']} | {','.join(str(r['id']) for r in web.get('records', []))} | {scenario.get('error') or scenario.get('coverage_limit', '')} |")
        content += ["", "未将标准桌面验证等同于1440/390、暗色或完整跨端验收。",
                    "清理：本轮会议和项目删除，固定测试账号保留并恢复运行前状态，普通运行保留账本/审计。"]
        report = "\n".join(content) + "\n"
        (HERE / "case-headed-report.md").write_text(report, encoding="utf-8")
        knowledge = self.platform.call("POST", "/project-knowledge", {"project_id": PROJECT_ID, "name": "cases.md有头页面执行报告", "status": "active",
            "data": {"domain": "WEB", "kind": "test_coverage_review", "knowledge_key": "punkrecord.cases_md.headed",
                     "content": report, "verification_status": "partial", "source_commit": SOURCE}})
        self.state["knowledge_id"] = knowledge["id"]
        self.save()
        print("HEADED SUMMARY", [(s["code"], s["status"]) for s in rows], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--select", action="append", default=[])
    args = parser.parse_args()
    suite = HeadedSuite()
    if args.select:
        suite.state["selected_scenarios"] = args.select
    try:
        suite.setup()
        suite.fixtures()
        suite.cases()
    finally:
        suite.cleanup()
        suite.report()
