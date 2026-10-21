"""Slow, visible replay of the reported team reviewer selection failure."""
import json
from datetime import datetime

from case_suite_runner import HERE, CN, write_json
from headed_case_runner import HeadedSuite, login, click, check, step


STAMP = datetime.now(CN).strftime("%Y%m%d_%H%M%S")
OUTPUT = HERE / f"team-headed-replay-{STAMP}.json"
REPORT = HERE / f"team-headed-replay-{STAMP}.md"


class Replay(HeadedSuite):
    def __init__(self):
        original = json.loads((HERE / "case-catalog.json").read_text(encoding="utf-8"))
        super().__init__()
        write_json(HERE / "case-catalog.json", original)

    def save(self):
        write_json(OUTPUT, self.state)

    def report(self):
        self.state["finished_at"] = datetime.now(CN).isoformat()
        self.save()
        lines = ["# 团队审核人有头慢速复现", "", f"目标：{self.state['target']}；前缀：{self.prefix}",
                 "", "密码使用平台加密参数，不截图或录屏；不修改已有业务数据。", "", "## 步骤", ""]
        for number, item in enumerate(self.state.get("replay_steps", []), 1):
            lines.append(f"{number}. {item['name']}")
        lines += ["", "## 结果", ""]
        for scene in self.state["scenarios"]:
            lines += [f"场景：{scene['code']}；结果：{scene['status']}", scene.get("error", "")]
        for case in self.state["web_cases"]:
            lines.append(f"任务：{case.get('task_id')}；模式：{case.get('mode')}；headless={case.get('headless')}；执行记录：{case.get('records')}")
        for progress in self.state.get("execution_progress", []):
            lines.append(f"执行记录{progress['record_id']}：已完成{progress['completed_steps']}/{progress['total_steps']}步；耗时{progress['duration_ms']}毫秒；错误：{progress['error']}")
        lines += ["", "## 清理", "", json.dumps(self.state["cleanup"], ensure_ascii=False, indent=2)]
        REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("REPLAY_OUTPUT", str(OUTPUT), flush=True)
        print("REPLAY_REPORT", str(REPORT), flush=True)


def main():
    suite = Replay()
    try:
        nodes = suite.platform.call("GET", "/agent/nodes")
        nodes = nodes.get("items", []) if isinstance(nodes, dict) else nodes
        node = next(n for n in nodes if n.get("node_key", n.get("data", {}).get("node_key")) == "local-win-01")
        print("AGENT", json.dumps({k: node.get(k) for k in ("node_key", "status", "last_seen_at")}), flush=True)
        suite.setup()
        suite.direct("manager", "POST", "/todo", suite.todo_body("Positive hours", hours=1.25))
        suite.direct("manager", "POST", "/todo", suite.todo_body("Zero hours", hours=0))
        reviewer = '.filter-select-item:has(span:text-is("审核人")) select'
        raw = login() + [step("wait", "", 2500), click("待办事项"), step("wait", "", 3000),
                         click("团队任务"), check('h1:text-is("团队任务")', "团队任务"),
                         step("wait", "", 4000), step("click", reviewer), step("wait", "", 10000),
                         step("select", reviewer, suite.account_pool["accounts"]["manager"]["display_name"])]
        names = ["输入本轮新主管用户名", "输入加密密码", "提交登录", "确认工作台已加载", "停留工作台2.5秒",
                 "进入待办事项", "停留3秒", "切换团队任务", "确认团队任务标题", "等待团队任务加载4秒",
                 "打开审核人下拉", "展开后停留10秒供查看", "选择当前测试主管（原失败步骤）"]
        assert len(raw) == len(names)
        for item, name in zip(raw, names):
            item["name"] = name
        suite.state["replay_steps"] = raw
        suite.save()
        print("VISIBLE_REPLAY_START", suite.prefix, flush=True)
        suite.run_case("TODO08-team-replay", "团队审核人下拉缺项有头慢速复现", ["TODO-08"], "/todo", raw,
                       actor="manager", limitation="仅复现团队审核人选择；不计为新增完整覆盖")
        suite.state["execution_progress"] = []
        for web in suite.state["web_cases"]:
            for saved in web.get("records", []):
                record = suite.platform.call("GET", f"/reports/records/{saved['id']}")
                detail = record.get("data", {})
                suite.state["execution_progress"].append({"record_id": record["id"],
                    "completed_steps": detail.get("step_count"), "total_steps": len(detail.get("steps", [])),
                    "duration_ms": detail.get("duration_ms"), "error": detail.get("error")})
        rows = suite.direct("manager", "GET", "/todo/team?status=open&page_size=100&reviewed_by_user_id=" + suite.user_ids["manager"])
        suite.state["api_diagnostic"] = {"total": rows["total"], "own_items": [r for r in rows["items"] if r["title"].startswith(suite.prefix + " ")]}
        suite.save()
    finally:
        suite.cleanup()
        suite.report()


if __name__ == "__main__":
    main()
