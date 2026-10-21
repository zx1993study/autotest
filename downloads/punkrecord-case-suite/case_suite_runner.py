"""Trace cases.md to remote-only scenarios and persist native autotest evidence."""
from __future__ import annotations

import argparse
import ast
import csv
import json
import os
from pathlib import Path
import re
import sys
import time
from datetime import datetime, timedelta
from decimal import Decimal
from urllib.parse import quote, urlencode
from uuid import uuid4
from zoneinfo import ZoneInfo

import requests
from account_pool import load_pool, read_password, use_existing_accounts

HERE = Path(__file__).resolve().parent
DEFAULT_REFERENCE = HERE / "source-reference" if (HERE / "source-reference").exists() else HERE.parent / "punkrecord-source-reference-5b44cbe"
REFERENCE = Path(os.environ.get("PUNKRECORD_REFERENCE", str(DEFAULT_REFERENCE)))
BASE = "http://14.103.229.153:15173"
API = BASE + "/api/v1"
MANAGEMENT = "https://dev-cn-01.yios.cn/autotest/api/v1"
PROJECT_ID = 17796
SOURCE = "5b44cbe96766ff0f56f7789271b245b5ce003518"
CN = ZoneInfo("Asia/Shanghai")

# The mappings identify source tests, not proof that those tests ran remotely.
MAPPING = {
    "TODO-01": ("test_beli_workflow.py; test_mcp_todo_tools.py", "task_creation; generate_development; sync_feature; mcp_creates", "跨创建来源的真实 HTTP 参数边界"),
    "TODO-02": ("test_project_workflow.py", "project_todo_plan", "同一任务双向编辑、真实图片与状态持久化"),
    "TODO-03": ("test_beli_workflow.py", "sync_preserves_identity", "重复生成/同步后身份、审核和附件不丢失"),
    "TODO-04": ("test_beli_workflow.py", "historical_completed; mandatory_backfill", "历史缺失字段需隔离历史夹具，不能修改存量业务记录"),
    "TODO-05": ("test_beli_workflow.py", "task_required_fields; timezone", "退回重提、最终提交时间及上海自然日结算"),
    "TODO-06": ("test_todo_ordering.py", "done_todos", "分页大小10、展开/加载更多及跨页排序"),
    "TODO-07": ("test_beli_workflow.py", "historical_pending_review", "缺少提交时间的历史夹具与撤回重提"),
    "TODO-08": ("scripts/test-planning-ui.cjs", "beli-task", "远程桌面/手机、明暗色、看板/列表/团队完整组合"),
    "BUG-01": ("test_beli_workflow.py; test_mcp_todo_tools.py", "bug_title; search_project_bugs", "真实字面量百分号/下划线、大小写和分页断言"),
    "BUG-02": ("scripts/test-planning-ui.cjs", "Bug状态", "远程刷新、翻页、浏览器历史和URL一致"),
    "BUG-03": ("test_project_workflow.py; scripts/test-planning-ui.cjs", "reassign_bug", "独立页完整生命周期、图片、390视口"),
    "LEAVE-01": ("test_beli_workflow.py", "leave_decoupled", "新员工独立请假批准/驳回与Todo数量不变"),
    "LEAVE-02": ("test_beli_workflow.py", "legacy_leave", "只允许隔离历史请假待办，远程存量不造假"),
    "LEAVE-03": ("test_beli_workflow.py", "calendar_leave", "真实半天和休息日；不改全局调休日历"),
    "LEAVE-04": ("test_wechat_inbound.py", "typed_leave; pending_reviews", "真实微信通道、编号和批量消息需专用绑定"),
    "LEAVE-05": ("test_mcp_todo_tools.py", "independent_leave_review", "MCP实际RPC调用而非mock转发"),
    "IAM-01": ("test_beli_workflow.py", "salary_admin", "管理员、非管理员L0、普通员工三身份与敏感字段检查"),
    "IAM-02": ("test_beli_workflow.py", "unauthorized_read", "普通员工跨账户/流水/调整拒绝"),
    "IAM-03": ("test_beli_workflow.py", "legacy_writes", "旧写接口拒绝和用户页面入口移除"),
    "BELI-01": ("test_beli_workflow.py", "self_created_task; formula", "真实完成后未发奖、独立审核后240"),
    "BELI-02": ("test_beli_workflow.py", "reward_formula", "4重要级×7延期日的28个真实结算组合"),
    "BELI-03": ("test_beli_workflow.py", "independent_review_edits", "审核修改计划同步、敏感字段不公开；内部快照只静态覆盖"),
    "BELI-04": ("test_beli_workflow.py", "requires_completion; reject_reward", "工资缺失/未验收/非L0及驳回后任务仍完成"),
    "BELI-05": ("test_beli_workflow.py; test_beli_mysql.py", "independent_review; concurrent_reward", "重复审批、重开冲销、再次结算和流水唯一性"),
    "BELI-06": ("test_beli_workflow.py", "adjustments_are_audited", "金额/假期防重、同键异参、原因必填"),
    "BELI-07": ("test_beli_workflow.py", "zero_hours_completion", "0工时完成后补录、重复保存不直接发奖"),
    "BELI-08": ("test_beli_workflow.py", "zero_hours_excludes", "pending/rejected归零退出，伪造审核拒绝，恢复唯一"),
    "BELI-09": ("test_beli_workflow.py", "historical_completed; no_policy", "需隔离策略和历史时间夹具，禁止改远程策略"),
    "BELI-10": ("test_beli_workflow.py; test_beli_mysql.py", "zero_hours_and_reward; zero_hours_completion", "已发奖保护可远程测；真实锁并发需隔离MySQL"),
    "ATT-01": ("test_beli_workflow.py", "activation; no_record", "启用日前/无记录/非工作日/L0四分支"),
    "ATT-02": ("test_beli_workflow.py", "automatic_once; same_day_union", "不能在共享环境造早会触发全员扣款"),
    "ATT-03": ("test_beli_workflow.py", "duplicate_names", "同名、未匹配、未发言名单，不影响现有员工"),
    "ATT-04": ("test_beli_workflow.py", "afternoon_leave; late_approval", "上午/下午/事后补批引发全局考勤重算"),
    "ATT-05": ("test_beli_workflow.py", "correction_and_waiver", "补参会人/删早会/改日历会影响现有余额"),
    "ATT-06": ("test_beli_workflow.py", "automatic_once", "后台跨日中断恢复缺少独立时钟和服务沙箱"),
    "ATT-07": ("test_beli_workflow.py", "historical_roster", "历史员工快照需专属隔离数据集"),
    "SHOP-01": ("test_beli_workflow.py; scripts/test-planning-ui.cjs", "product_image", "商品上下架、认证图片与员工可见性"),
    "SHOP-02": ("test_beli_mysql.py; test_beli_workflow.py", "oversell; overspend", "金额/库存不足可远程；行锁并发只在隔离MySQL"),
    "SHOP-03": ("test_beli_workflow.py", "store_freeze", "重复申请只冻结一次，余额与库存精确断言"),
    "SHOP-04": ("test_beli_workflow.py", "approval_leave", "批准扣款解冻并增假期，0.5天边界"),
    "SHOP-05": ("test_beli_workflow.py", "store_release", "拒绝、本人取消、L0取消及重复退款保护"),
    "SHOP-06": ("test_beli_workflow.py", "shipped_cannot_refund", "实物发货后禁止普通退款"),
    "SHOP-07": ("test_beli_workflow.py", "balance_loss", "用新员工手工扣款验证余额保护；不伪造真实早会扣款"),
    "DOC-01": ("test_mcp_todo_tools.py", "documented_inventory", "远程mcp-info工具名称和总数与最新文档逐项一致"),
}


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")


def catalog():
    lines = (REFERENCE / ".agent/test/cases.md").read_text(encoding="utf-8").splitlines()
    items, section = [], ""
    for number, line in enumerate(lines, 1):
        if line.startswith("## "):
            section = line[3:]
        row = next(csv.reader([line], delimiter="|"))
        if len(row) < 5 or not re.fullmatch(r"(?:TODO|BUG|LEAVE|IAM|BELI|ATT|SHOP|DOC)-\d+", row[1].strip()):
            continue
        code, scene, expected = [part.strip() for part in row[1:4]]
        scripts, functions, gap = MAPPING[code]
        items.append({"id": code, "section": section, "scenario": scene, "expected": expected,
                      "source": ".agent/test/cases.md", "line": number, "source_commit": SOURCE,
                      "existing_scripts": scripts, "existing_test_filter": functions,
                      "remote_gap": gap, "remote_status": "not_run", "evidence": []})
    assert len(items) == 44 and {i["id"] for i in items} == set(MAPPING)
    write_json(HERE / "case-catalog.json", items)
    tests = []
    for file in sorted((REFERENCE / "backend/tests").glob("*.py")):
        tree = ast.parse(file.read_text(encoding="utf-8"))
        count = sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test_")
                    for n in ast.walk(tree))
        if count:
            tests.append((file.name, count))
    content = ["# cases.md 脚本盘点与补充清单", "", f"来源：origin/main `{SOURCE}`；仅静态读取，不运行本地业务测试。",
        "", "此前使用旧 dev 分支 a2ace19，未读取最新 .agent/test/cases.md。这是此前生成来源不完整的原因。",
        "现有61条远程冒烟用例不能代替本清单44个回归测试点。一个测试点含多个分支，触达不等于完整覆盖。",
        "", "## 已有测试脚本", "", "| 文件 | test函数数（非参数化用例数） |", "|---|---:|"]
    content += [f"| backend/tests/{name} | {count} |" for name, count in tests]
    content += ["", "另有 scripts/test-planning-ui.cjs：浏览器请求转发隔离SQLite，不是当前远程验收证据。",
        "", "## 逐条映射", "", "| 原编号 | 已有脚本 | 需补充/远程限制 |", "|---|---|---|"]
    content += [f"| {i['id']} | {i['existing_scripts']} | {i['remote_gap']} |" for i in items]
    content += ["", "## 安全边界", "", "目标仅为 http://14.103.229.153:15173/。只创建、修改本轮前缀数据。",
        "不创建早会、不修改全局日历/策略、不运行迁移、不重启服务、不发真实微信、不调用收费AI。",
        "历史数据、全员考勤和真实行锁并发保留为未验证；不能以静态代码或旧隔离测试报告计为本轮通过。",
        "固定测试账号保留并恢复运行前状态、商品下架；普通运行保留订单/请假/账本审计。新测试项目和非早会会议删除。",
        "", "会议参会人应在说话人识别中编辑，并由实际分段同步。旧MEET-002错误定位独立输入框，应归为脚本问题。"]
    (HERE / "case-script-audit.md").write_text("\n".join(content) + "\n", encoding="utf-8")
    return items


class Platform:
    def __init__(self):
        self.session = requests.Session()
        result = self.session.post(MANAGEMENT + "/auth/login", json={
            "username": os.environ.get("AUTOTEST_USERNAME", "admin"),
            "password": os.environ["AUTOTEST_PASSWORD"]}, timeout=30)
        result.raise_for_status()
        self.session.headers["Authorization"] = "Bearer " + result.json()["data"]["access_token"]

    def call(self, method, path, body=None):
        response = self.session.request(method, MANAGEMENT + path, json=body, timeout=90)
        if not response.ok:
            raise RuntimeError(f"autotest {method} {path}: HTTP {response.status_code} {response.text[:250]}")
        result = response.json()
        if result.get("code") != 0:
            raise RuntimeError(f"autotest {path}: {result.get('message')}")
        return result["data"]


class Suite:
    def __init__(self):
        self.platform = Platform()
        self.prefix = "CASE_" + datetime.now(CN).strftime("%Y%m%d_%H%M%S")
        self.state = {"target": BASE, "project_id": PROJECT_ID, "source_commit": SOURCE,
                      "run_prefix": self.prefix, "started_at": datetime.now(CN).isoformat(),
                      "catalog": catalog(), "scenarios": [], "api_cases": [], "web_cases": [],
                      "fixtures": [], "cleanup": []}
        self.sessions, self.auth, self.user_ids = {}, {}, {}
        self.password = None
        self.interfaces = {}
        self.current = None
        self.save()

    def save(self):
        write_json(getattr(self, "output", HERE / "case-suite-results.json"), self.state)

    def direct(self, actor, method, path, body=None, **kwargs):
        assert path.startswith("/") and not path.startswith("//")
        response = self.sessions[actor].request(method, API + path, json=body, timeout=30, **kwargs)
        response.raise_for_status()
        result = response.json()
        assert result.get("code") == 0, result.get("message")
        return result["data"]

    def login(self, name, username, password):
        session = requests.Session()
        response = session.post(API + "/auth/login", json={"username": username, "password": password}, timeout=25)
        response.raise_for_status()
        token = response.json()["access_token"]
        session.headers["Authorization"] = "Bearer " + token
        self.sessions[name] = session
        self.user_ids[name] = self.direct(name, "GET", "/auth/me")["id"]
        auth = self.platform.call("POST", "/project-auth/generate-token", {
            "project_id": PROJECT_ID, "name": "PunkRecord remote admin" if name == "admin" else username,
            "token": token, "header_name": "Authorization", "auth_type": "bearer",
            "login_case_type": "API", "refresh_strategy": "manual"})
        self.auth[name] = auth["id"]

    def setup(self):
        pool = load_pool()
        password = read_password(pool)
        project = self.platform.call("GET", f"/projects/{PROJECT_ID}")
        assert project["name"] == "PunkRecord" and project["data"]["base_url"].rstrip("/") == BASE
        self.login("admin", "admin", os.environ["PUNKRECORD_PASSWORD"])
        permissions = self.direct("admin", "GET", "/iam/permissions")
        if isinstance(permissions, dict):
            permissions = permissions.get("items", [])
        allowed = {"todo.read", "todo.write", "project.read", "project.write", "iam.read", "meeting.read", "meeting.write"}
        assert allowed <= {p["code"] for p in permissions}
        job_id = pool["accounts"]["manager"]["job_title_id"]
        granted = self.direct("admin", "GET", f"/iam/job-titles/{job_id}/permissions")
        assert allowed <= set(granted), "Fixed test role permissions changed; no automatic role creation"
        use_existing_accounts(self, pool, password)
        self.direct("admin", "PUT", f"/iam/users/{self.user_ids['employee']}/salary", {"basic_salary": 12000})
        project = self.direct("manager", "POST", "/project/projects", {
            "name": self.prefix + " Project", "project_no": self.prefix, "project_type": "b2b",
            "pm_user_id": self.user_ids["manager"]})
        self.pid = project["id"]
        self.state["fixtures"].append({"type": "project", "id": self.pid, "name": project["name"]})
        self.direct("manager", "POST", f"/project/projects/{self.pid}/members", {"user_id": self.user_ids["employee"]})
        self.save()

    def scenario(self, code, title, points, fn, *, limitation=None):
        selected = self.state.get("selected_scenarios")
        if selected and code not in selected:
            return
        self.current = {"code": code, "title": title, "case_points": points, "status": "running", "evidence": []}
        if limitation:
            self.current["coverage_limit"] = limitation
        self.state["scenarios"].append(self.current)
        self.save()
        try:
            fn()
            self.current["status"] = "success"
        except Exception as error:
            self.current.update(status="failed", error=str(error)[:900])
        self.save()
        print(self.current["status"].upper(), code, title, self.current.get("error", ""), flush=True)

    def call(self, actor, method, path, body=None, *, expected=200, equals=None, contains=None, missing=(), content_type="application/json"):
        number = len(self.current["evidence"]) + 1
        code = self.current["code"] + f".{number:02}"
        key = method + " " + path.split("?")[0]
        if key not in self.interfaces:
            iface = self.platform.call("POST", "/api-testing/interfaces", {
                "project_id": PROJECT_ID, "name": "cases.md " + key, "status": "active",
                "data": {"method": method, "path": path.split("?")[0], "module": "cases.md " + self.current["case_points"][0].split("-")[0], "api_base_path": "/api/v1"}})
            self.interfaces[key] = iface["id"]
        assertions = [{"type": "status", "expected": expected}]
        if expected == 200:
            assertions.append({"type": "json_equals", "path": "code", "expected": 0})
        assertions += [{"type": "json_equals", "path": k, "expected": v} for k, v in (equals or {}).items()]
        if contains:
            assertions.append({"type": "body_contains", "expected": contains})
        case = self.platform.call("POST", "/api-testing/cases", {
            "project_id": PROJECT_ID, "case_type": "API", "source_id": self.interfaces[key],
            "name": "CASE " + code + " " + self.current["title"], "status": "active",
            "description": "来源 .agent/test/cases.md " + ", ".join(self.current["case_points"]) + "; actor=" + actor + "; fixture=" + self.prefix + "; rerun with case_suite_runner.py (fresh fixtures required).",
            "assertions": assertions, "data": {"method": method, "path": path, "body": body or {},
                "api_base_path": "/api/v1", "auth_id": self.auth[actor], "content_type": content_type,
                "case_points": self.current["case_points"], "source_commit": SOURCE, "fixture_scope": self.prefix}})
        result = self.platform.call("POST", "/api-testing/cases/run", {"project_id": PROJECT_ID, "case_ids": [case["id"]],
            "mode": "server_headless", "config": {"concurrency": 1, "timeout": 25}})
        record = result["records"][0]
        data = record["data"]
        evidence = {"case_id": case["id"], "record_id": record["id"], "status": record["status"],
                    "method": method, "path": path, "http_status": data.get("response_status"),
                    "assertions": data.get("assertions"), "actor": actor}
        self.current["evidence"].append(evidence)
        self.state["api_cases"].append({"code": code, **evidence})
        self.save()
        try:
            response = json.loads(data.get("response_body") or "{}")
        except json.JSONDecodeError:
            if method != "GET":
                raise
            full = self.sessions[actor].get(API + path, timeout=30)
            full.raise_for_status()
            response = full.json()
            evidence["response_reloaded_readonly"] = "Platform response_body truncated at 8000 characters; no mutation replayed"
            self.save()
        if record["status"] != "success":
            failed = [a for a in data.get("assertions", []) if not a.get("passed")]
            raise AssertionError(f"record {record['id']}: {failed}; {str(response)[:350]}")
        # The deployed executor predates json_pointer_exists; retain explicit client assertions.
        for pointer in missing:
            value = response
            exists = True
            for part in pointer.strip("/").split("/"):
                if not isinstance(value, dict) or part not in value:
                    exists = False
                    break
                value = value[part]
            evidence.setdefault("scenario_assertions", []).append({"type": "field_absent", "path": pointer, "passed": not exists})
            self.save()
            assert not exists, f"Sensitive field unexpectedly present: {pointer} (record {record['id']})"
        return response.get("data")

    def todo_body(self, title, *, hours=0, priority="p2", days=0, actor="employee", kind="project"):
        due = (datetime.now(CN) - timedelta(days=days)).replace(hour=18, minute=0, second=0, microsecond=0)
        body = {"title": self.prefix + " " + title, "assignee_user_id": self.user_ids[actor],
                "due_at": due.isoformat(), "priority": priority, "estimated_hours": hours}
        if kind != "custom":
            body.update(source_type="project_task", source_id=self.pid, link={"project_id": self.pid})
        if kind == "bug":
            body.update(tags=["bug"], link={"project_id": self.pid, "type": "bug"})
        return body

    def task(self, title, **kwargs):
        return self.call("manager", "POST", "/todo", self.todo_body(title, **kwargs))["id"]

    def complete(self, task_id):
        self.call("employee", "POST", f"/todo/{task_id}/submit", equals={"data.status": "pending_review"})
        return self.call("manager", "POST", f"/todo/{task_id}/approve", equals={"data.status": "done"})

    def account(self, *, balance=None, frozen=None, actor="employee", leave=None):
        equals = {"data.is_l0": False, "data.items.0.user_id": self.user_ids[actor]}
        if balance is not None:
            equals["data.items.0.balance"] = float(Decimal(str(balance)).quantize(Decimal(".01")))
        if frozen is not None:
            equals["data.items.0.frozen"] = float(Decimal(str(frozen)).quantize(Decimal(".01")))
        if leave is not None:
            equals["data.items.0.leave.annual"] = leave
        return self.call(actor, "GET", "/beli/accounts", equals=equals)["items"][0]

    def rewards(self, task_id, status=None):
        rows = self.call("employee", "GET", "/beli/rewards")
        found = [r for r in rows if r["todo_id"] == task_id]
        if status is None:
            assert not found, found
        else:
            assert len(found) == 1 and found[0]["status"] == status, found
        return found

    def adjust(self, amount, *, reason="case suite adjustment", key=None, leave_type=None):
        body = {"amount": amount, "reason": self.prefix + " " + reason, "request_key": key or str(uuid4())}
        if leave_type:
            body["leave_type"] = leave_type
        self.call("manager", "POST", f"/beli/accounts/{self.user_ids['employee']}/adjust", body)
        return body

    def task_scenarios(self):
        for kind in ("custom", "project", "bug"):
            for value in ("omitted", 0, 1.25, -1, None, 0.001, "NaN", "Infinity"):
                def boundary(kind=kind, value=value):
                    body = self.todo_body(f"{kind} hours {value}", kind=kind)
                    if value == "omitted":
                        body.pop("estimated_hours")
                    else:
                        body["estimated_hours"] = value
                    valid = value in ("omitted", 0, 1.25)
                    data = self.call("manager", "POST", "/todo", body, expected=200 if valid else 422)
                    if valid:
                        assert Decimal(data["estimated_hours"]) == Decimal(str(0 if value == "omitted" else value))
                        if kind == "custom":
                            self.state["fixtures"].append({"type": "custom_todo", "id": data["id"], "name": body["title"]})
                self.scenario(f"TODO01-{kind}-{str(value).replace('.', '_')}", f"{kind} 工时={value}", ["TODO-01"], boundary)
            def missing_date(kind=kind):
                body = self.todo_body("missing date", kind=kind)
                body.pop("due_at")
                self.call("manager", "POST", "/todo", body, expected=422)
            self.scenario("TODO01-" + kind + "-date", kind + " 缺少截止日拒绝", ["TODO-01"], missing_date)

        def generated():
            path = f"/project/projects/{self.pid}/generate-dev-tasks"
            task = {"title": self.prefix + " generated", "assignee_user_id": self.user_ids["employee"],
                    "due_at": self.todo_body("x")["due_at"], "feature_key": "case-repeat", "dev_type": "dev_backend"}
            self.call("manager", "POST", path, {"tasks": [task]})
            before = self.call("manager", "GET", f"/project/projects/{self.pid}/todos")
            found = next(t for t in before if t["title"] == task["title"])
            assert Decimal(found["estimated_hours"]) == 0
            self.call("manager", "PATCH", f"/todo/{found['id']}", {"notes": "preserved", "estimated_hours": 1.25})
            self.call("manager", "POST", path, {"tasks": [task]})
            after = self.call("manager", "GET", f"/project/projects/{self.pid}/todos")
            again = [t for t in after if t["title"] == task["title"]]
            assert len(again) == 1 and again[0]["id"] == found["id"] and Decimal(again[0]["estimated_hours"]) == Decimal("1.25")
            for hours in (-1, None, 0.001, "NaN", "Infinity"):
                self.call("manager", "POST", path, {"tasks": [{**task, "feature_key": str(uuid4()), "estimated_hours": hours}]}, expected=422)
        self.scenario("TODO01-03-batch", "批量生成默认0工时、边界与重复身份", ["TODO-01", "TODO-03"], generated,
                      limitation="审核附件保留另需带真实图片的完整回归；MCP入口尚未执行")

        def sync():
            stages = self.call("manager", "GET", f"/project/projects/{self.pid}/stages")
            features = [{"product": "case", "module": "case", "l1_feature": "case", "l2_feature": "sync", "description": "test", "dev_backend": 1}]
            self.call("manager", "PATCH", f"/project/projects/{self.pid}/stages/{stages[0]['id']}", {"feature_list": json.dumps(features)})
            path = f"/project/projects/{self.pid}/sync-dev-tasks"
            plan = {"due_at": self.todo_body("x")["due_at"]}
            self.call("manager", "POST", path, plan, equals={"data.created": 1, "data.deleted": 0})
            before = self.call("manager", "GET", f"/project/projects/{self.pid}/todos")
            self.call("manager", "POST", path, plan, equals={"data.created": 0, "data.deleted": 0})
            after = self.call("manager", "GET", f"/project/projects/{self.pid}/todos")
            assert {t["id"] for t in before} == {t["id"] for t in after}
        self.scenario("TODO03-sync", "重复同步不重建任务或复制Bug", ["TODO-01", "TODO-03"], sync,
                      limitation="未构造带已审核奖励与图片附件的同步组合")

        def identity():
            task_id = self.task("identity")
            self.call("manager", "PATCH", f"/todo/{task_id}", {"estimated_hours": 1.25})
            rows = self.call("manager", "GET", f"/project/projects/{self.pid}/todos")
            assert Decimal(next(r for r in rows if r["id"] == task_id)["estimated_hours"]) == Decimal("1.25")
            self.call("manager", "POST", f"/project/projects/{self.pid}/todos/{task_id}/plan", {"estimated_hours": 2.5, "due_at": self.todo_body("x")["due_at"]})
            self.call("employee", "GET", f"/todo/{task_id}", equals={"data.id": task_id, "data.estimated_hours": "2.50"})
        self.scenario("TODO02-identity", "项目与待办双向编辑保持同一ID和工时", ["TODO-02"], identity, limitation="图片及状态全组合尚未完整覆盖")

        def resubmit():
            task_id = self.task("resubmit")
            first = self.call("employee", "POST", f"/todo/{task_id}/submit")
            self.call("manager", "POST", f"/todo/{task_id}/reject", {"comment": "revise"}, equals={"data.status": "open"})
            time.sleep(1.1)
            second = self.call("employee", "POST", f"/todo/{task_id}/submit")
            assert second["submitted_at"] > first["submitted_at"]
            self.call("manager", "POST", f"/todo/{task_id}/approve", equals={"data.status": "done", "data.submitted_at": second["submitted_at"]})
        self.scenario("TODO05-resubmit", "退回重提以最终提交时间验收", ["TODO-05"], resubmit, limitation="未跨真实午夜等待审核")

        def timezone():
            body = self.todo_body("timezone")
            body["due_at"] = "2026-10-22T10:00:00+00:00"
            self.call("manager", "POST", "/todo", body, equals={"data.due_at": "2026-10-22T18:00:00"})
        self.scenario("TODO05-zone", "UTC截止时间归一到上海18点", ["TODO-05"], timezone)

    def bug_scenarios(self):
        def search():
            titles = ["CaseMixed Alpha", "literal%percent", "literal_under", "unrelated"]
            expected = {}
            for title in titles:
                tid = self.task(title, kind="bug")
                expected[title] = tid
            for query, name in (("casemixed", titles[0]), ("%", titles[1]), ("_under", titles[2])):
                data = self.call("manager", "GET", f"/project/projects/{self.pid}/bugs?" + urlencode({"title": query, "page_size": 1}),
                                 equals={"data.total": 1, "data.items.0.id": expected[name]})
                assert len(data["items"]) == 1
            self.call("manager", "GET", f"/project/projects/{self.pid}/bugs?title=no-such-" + self.prefix,
                      equals={"data.total": 0, "data.items": []})
            page1 = self.call("manager", "GET", f"/project/projects/{self.pid}/bugs?page=1&page_size=2")
            page2 = self.call("manager", "GET", f"/project/projects/{self.pid}/bugs?page=2&page_size=2")
            assert len(page1["items"]) == len(page2["items"]) == 2
            assert not ({i["id"] for i in page1["items"]} & {i["id"] for i in page2["items"]})
        self.scenario("BUG01-search", "Bug大小写、字面百分号/下划线和分页", ["BUG-01"], search)

    def permission_scenarios(self):
        employee = self.user_ids["employee"]
        def salary():
            self.call("admin", "PUT", f"/iam/users/{employee}/salary", {"basic_salary": 12000})
            self.call("admin", "GET", f"/iam/users/{employee}/salary", equals={"data.basic_salary": 12000})
            for actor in ("employee", "manager"):
                self.call(actor, "GET", f"/iam/users/{employee}/salary", expected=403)
            self.call("admin", "GET", f"/iam/users/{employee}", missing=("/data/basic_salary", "/data/hashed_password"))
        self.scenario("IAM01-salary", "工资仅管理员可读写，普通员工和非管理员L0拒绝", ["IAM-01"], salary)

        def forbidden():
            self.call("employee", "GET", "/beli/ledger?user_id=" + self.user_ids["other"], expected=404)
            self.call("employee", "POST", f"/beli/accounts/{self.user_ids['other']}/adjust",
                      {"amount": 1, "reason": "forbidden", "request_key": str(uuid4())}, expected=403)
            self.account()
        self.scenario("IAM02-cross-user", "员工跨账户流水及余额调整拒绝", ["IAM-02"], forbidden)

        def legacy():
            self.call("admin", "PATCH", f"/iam/users/{employee}", {"beili_adjust_action": "add", "beili_adjust_amount": 1}, expected=400)
            self.call("admin", "POST", f"/iam/users/{employee}/reset-leave-balances", expected=400)
        self.scenario("IAM03-legacy", "旧余额调整与假期重置写接口不可绕过", ["IAM-03"], legacy,
                      limitation="用户管理页面入口另行有头验证")

    def reward_scenarios(self):
        def amount_case(priority, days):
            task_id = self.task(f"reward {priority} {days}", hours=8, priority=priority, days=days)
            before = Decimal(self.account()["balance"])
            self.complete(task_id)
            self.account(balance=before)
            expected = (Decimal(240) * {"p0": Decimal("1.2"), "p1": Decimal(1), "p2": Decimal(1), "p3": Decimal(".8")}[priority]
                        * {0: Decimal(1), 1: Decimal(".95"), 2: Decimal(".9"), 3: Decimal(".8"), 4: Decimal(".6"), 5: Decimal(".5"), 8: Decimal(".5")}[days]).quantize(Decimal(".01"))
            self.call("manager", "POST", f"/beli/rewards/{task_id}/review", {"action": "approve"},
                      equals={"data.status": "approved", "data.amount": float(expected)},
                      missing=("/data/snapshot", "/data/basic_salary", "/data/priority_factor"))
            self.account(balance=before + expected)
        for priority in ("p0", "p1", "p2", "p3"):
            for days in (0, 1, 2, 3, 4, 5, 8):
                points = ["BELI-02"] + (["BELI-01"] if priority == "p2" and days == 0 else [])
                self.scenario(f"BELI02-{priority}-{days}", f"工资12000、8小时、{priority}、延期{days}天", points,
                              lambda p=priority, d=days: amount_case(p, d))

        def idempotent():
            task_id = self.task("reward duplicate", hours=1)
            before = Decimal(self.account()["balance"])
            self.complete(task_id)
            for _ in range(2):
                self.call("manager", "POST", f"/beli/rewards/{task_id}/review", {"action": "approve"}, equals={"data.amount": 30})
            self.account(balance=before + 30)
            self.call("manager", "PATCH", f"/todo/{task_id}", {"estimated_hours": 0}, expected=400)
            self.call("manager", "POST", f"/todo/{task_id}/status", {"status": "open"})
            self.account(balance=before)
            self.complete(task_id)
            self.call("manager", "POST", f"/beli/rewards/{task_id}/review", {"action": "approve"}, equals={"data.amount": 30})
            self.account(balance=before + 30)
        self.scenario("BELI05-10-idempotency", "重复审核只发一次、已发奖归零拒绝、重开冲销后再结算", ["BELI-05", "BELI-10"], idempotent,
                      limitation="串行真实请求通过不代表MySQL并发锁验证通过")

        def edits():
            task_id = self.task("review edits", hours=8)
            self.complete(task_id)
            self.call("manager", "POST", f"/beli/rewards/{task_id}/review", {"action": "approve", "estimated_hours": 2, "priority": "p0"},
                      equals={"data.amount": 72, "data.estimated_hours": 2, "data.priority": "p0"}, missing=("/data/snapshot",))
            self.call("employee", "GET", f"/todo/{task_id}", equals={"data.estimated_hours": "2.00", "data.priority": "p0"})
        self.scenario("BELI03-edits", "独立审核修改工时重要级同步原任务且不泄露快照", ["BELI-03"], edits,
                      limitation="内部结算快照旧值需要隔离数据库测试，远程只验证公开响应不泄密")

        def guards():
            task_id = self.task("missing salary", hours=1, actor="other")
            self.call("manager", "POST", f"/beli/rewards/{task_id}/review", {"action": "approve"}, expected=400)
            self.call("other", "POST", f"/todo/{task_id}/submit")
            self.call("manager", "POST", f"/todo/{task_id}/approve")
            self.call("manager", "POST", f"/beli/rewards/{task_id}/review", {"action": "approve"}, expected=400)
            self.call("employee", "POST", f"/beli/rewards/{task_id}/review", {"action": "approve"}, expected=403)
            self.call("manager", "POST", f"/beli/rewards/{task_id}/review", {"action": "reject", "comment": "no salary"}, equals={"data.status": "rejected"})
            self.call("other", "GET", f"/todo/{task_id}", equals={"data.status": "done"})
        self.scenario("BELI04-guards", "未验收/工资缺失/非L0不发奖，驳回奖励不改变完成态", ["BELI-04"], guards)

        def adjust():
            before = Decimal(self.account()["balance"])
            body = self.adjust(10, key=str(uuid4()))
            self.call("manager", "POST", f"/beli/accounts/{self.user_ids['employee']}/adjust", body)
            self.account(balance=before + 10)
            self.call("manager", "POST", f"/beli/accounts/{self.user_ids['employee']}/adjust", {**body, "amount": 11}, expected=400)
            self.call("manager", "POST", f"/beli/accounts/{self.user_ids['employee']}/adjust", {**body, "request_key": str(uuid4()), "reason": " "}, expected=400)
            self.adjust(-10)
            self.account(balance=before)
        self.scenario("BELI06-adjust", "新员工余额调整防重、同键异参和原因校验", ["BELI-06"], adjust, limitation="假期调整防重另在商城/请假场景验证")

        def backfill():
            before = Decimal(self.account()["balance"])
            task_id = self.task("zero backfill", hours=0)
            self.complete(task_id)
            self.rewards(task_id)
            self.call("manager", "POST", f"/beli/rewards/{task_id}/review", {"action": "approve", "estimated_hours": 2}, expected=400)
            for _ in range(2):
                self.call("manager", "PATCH", f"/todo/{task_id}", {"estimated_hours": 2})
            self.rewards(task_id, "pending")
            self.account(balance=before)
        self.scenario("BELI07-backfill", "0工时完成不入队，补录和重复保存只生成待审核不发钱", ["BELI-07"], backfill,
                      limitation="本轮验证指派任务；自建任务组合需额外执行")
        for previous in ("pending", "rejected"):
            def excluded(previous=previous):
                task_id = self.task("exclude " + previous, hours=1)
                self.complete(task_id)
                if previous == "rejected":
                    self.call("manager", "POST", f"/beli/rewards/{task_id}/review", {"action": "reject", "comment": "preserve review"})
                self.call("manager", "PATCH", f"/todo/{task_id}", {"estimated_hours": 0})
                found = self.rewards(task_id, "excluded")
                if previous == "rejected":
                    assert found[0]["comment"] == "preserve review"
                for action in ("approve", "reject"):
                    self.call("manager", "POST", f"/beli/rewards/{task_id}/review", {"action": action, "estimated_hours": 2, "comment": "stale"}, expected=400)
                self.call("manager", "PATCH", f"/todo/{task_id}", {"estimated_hours": 1.5})
                self.rewards(task_id, "pending")
            self.scenario("BELI08-" + previous, previous + "归零退出且不能伪造工时审核，恢复唯一待审核", ["BELI-08"], excluded)

    def leave_scenarios(self):
        # Future dates have no attendance reconciliation effect; never alter the calendar.
        calendar = self.direct("employee", "GET", "/beli/calendar")
        overrides = {r["day"]: r["is_workday"] for r in calendar}
        day = datetime.now(CN).date() + timedelta(days=14)
        while not overrides.get(day.isoformat(), day.weekday() < 5):
            day += timedelta(days=1)
        def leave(approve):
            before = self.call("employee", "GET", "/todo/my?page_size=100")["total"]
            account = self.account()
            annual = float(account["leave"]["annual"])
            data = self.call("employee", "POST", "/todo/leaves", {"leave_type": "annual", "start_at": str(day) + "T09:00:00",
                "end_at": str(day) + "T12:00:00", "reason": self.prefix + " half-day"}, equals={"data.status": "pending"})
            endpoint = "approve" if approve else "reject"
            self.call("manager", "POST", f"/todo/leaves/{data['id']}/{endpoint}", {"comment": "test"},
                      equals={"data.status": "approved" if approve else "rejected"})
            self.call("employee", "GET", "/todo/my?page_size=100", equals={"data.total": before})
            self.account(leave=annual - 0.5 if approve else annual)
            self.state["fixtures"].append({"type": "leave_audit", "id": data["id"], "name": self.prefix + " half-day"})
        self.scenario("LEAVE01-03-approve", "未来工作日上午半天请假批准只扣0.5天、不创建Todo", ["LEAVE-01", "LEAVE-03"], lambda: leave(True),
                      limitation="未修改调休日历，未测周末调休；未来日期避免影响现有考勤")
        self.scenario("LEAVE01-reject", "独立请假驳回不扣假期、不创建Todo", ["LEAVE-01"], lambda: leave(False))

    def shop_scenarios(self):
        def setup_product():
            self.product_body = {"name": self.prefix + " Physical", "kind": "physical", "price": 100, "stock": 20, "active": True}
            product = self.call("manager", "POST", "/beli/products", self.product_body)
            self.product_id = product["id"]
            self.state["fixtures"].append({"type": "product", "id": self.product_id, "name": self.product_body["name"], "body": self.product_body})
            self.call("employee", "POST", "/beli/products", self.product_body, expected=403)
            self.call("manager", "PUT", f"/beli/products/{self.product_id}", {**self.product_body, "active": False})
            products = self.call("employee", "GET", "/beli/products")
            assert all(p["id"] != self.product_id for p in products)
            self.call("manager", "PUT", f"/beli/products/{self.product_id}", self.product_body)
        self.scenario("SHOP01-publish", "L0建商品上下架，员工不能维护或看到下架商品", ["SHOP-01"], setup_product,
                      limitation="图片上传/粘贴与认证查看尚未执行")
        if not hasattr(self, "product_id"):
            return
        def order(quantity=1):
            return self.call("employee", "POST", "/beli/orders", {"product_id": self.product_id, "quantity": quantity,
                "request_key": str(uuid4()), "delivery": self.prefix + " test-only collection"})
        def insufficient():
            self.call("other", "POST", "/beli/orders", {"product_id": self.product_id, "request_key": str(uuid4()), "delivery": "test"}, expected=400)
            self.call("employee", "POST", "/beli/orders", {"product_id": self.product_id, "quantity": 100, "request_key": str(uuid4()), "delivery": "test"}, expected=400)
        self.scenario("SHOP02-insufficient", "余额不足和库存不足拒绝兑换", ["SHOP-02"], insufficient, limitation="未验证并发最后一件行锁")

        def duplicate():
            available = Decimal(self.account()["available"])
            if available < 100:
                self.adjust(str(200 - available), reason="fund temporary redemption test")
            before = self.account()
            body = {"product_id": self.product_id, "request_key": str(uuid4()), "delivery": "test"}
            created = self.call("employee", "POST", "/beli/orders", body, equals={"data.status": "pending", "data.amount": "100.00"})
            self.call("employee", "POST", "/beli/orders", body, equals={"data.id": created["id"]})
            self.account(balance=before["balance"], frozen=Decimal(before["frozen"]) + 100)
            self.call("employee", "POST", f"/beli/orders/{created['id']}/action", {"action": "cancel"}, equals={"data.status": "cancelled"})
            self.call("manager", "POST", f"/beli/orders/{created['id']}/action", {"action": "cancel"}, equals={"data.status": "cancelled"})
            self.call("employee", "POST", f"/beli/orders/{created['id']}/action", {"action": "cancel"}, expected=403)
            self.account(balance=before["balance"], frozen=before["frozen"])
        self.scenario("SHOP03-05-repeat", "重复兑换只冻结一次，申请人重复取消不重复解冻", ["SHOP-03", "SHOP-05"], duplicate)

        def cancellation(action):
            before = self.account()
            created = order()
            if action == "approved_cancel":
                self.call("manager", "POST", f"/beli/orders/{created['id']}/action", {"action": "approve"}, equals={"data.status": "approved"})
            for _ in range(2):
                self.call("manager", "POST", f"/beli/orders/{created['id']}/action", {"action": "reject" if action == "reject" else "cancel"})
            self.account(balance=before["balance"], frozen=before["frozen"])
        for action in ("reject", "approved_cancel"):
            self.scenario("SHOP05-" + action, "L0 " + action + " 重复操作不重复退款", ["SHOP-05"], lambda a=action: cancellation(a))

        def shipped():
            created = order()
            self.call("manager", "POST", f"/beli/orders/{created['id']}/action", {"action": "approve"})
            self.call("manager", "POST", f"/beli/orders/{created['id']}/action", {"action": "ship", "tracking": self.prefix + " simulated test record"}, equals={"data.status": "shipped"})
            self.call("manager", "POST", f"/beli/orders/{created['id']}/action", {"action": "cancel"}, expected=400)
        self.scenario("SHOP06-shipping", "实物批准发货后不可普通取消退款", ["SHOP-06"], shipped)

        def leave_product():
            body = {"name": self.prefix + " Leave", "kind": "leave", "price": 100, "stock": 3, "active": True, "leave_type": "annual", "leave_days": 0.5}
            self.call("manager", "POST", "/beli/products", {**body, "leave_days": 0.1}, expected=422)
            product = self.call("manager", "POST", "/beli/products", body)
            self.state["fixtures"].append({"type": "product", "id": product["id"], "name": body["name"], "body": body})
            before = self.account()
            created = self.call("employee", "POST", "/beli/orders", {"product_id": product["id"], "request_key": str(uuid4())})
            self.call("manager", "POST", f"/beli/orders/{created['id']}/action", {"action": "approve"}, equals={"data.status": "fulfilled"})
            self.account(balance=Decimal(before["balance"]) - 100, frozen=before["frozen"], leave=float(before["leave"]["annual"]) + 0.5)
        self.scenario("SHOP04-leave", "假期兑换最小0.5天，批准时扣款解冻并增假期", ["SHOP-04"], leave_product)

        def loss():
            created = order()
            before = self.account()
            reduction = Decimal(before["balance"]) - 50
            self.adjust(str(-reduction))
            self.call("manager", "POST", f"/beli/orders/{created['id']}/action", {"action": "approve"}, expected=400)
            self.call("employee", "POST", f"/beli/orders/{created['id']}/action", {"action": "cancel"})
            self.adjust(str(reduction))
        self.scenario("SHOP07-balance", "冻结后新员工余额下降，不得绕过余额不足完成审批", ["SHOP-07"], loss,
                      limitation="使用本轮新员工独立余额调整模拟下降；未执行会影响全员的真实早会扣款")

    def documentation(self):
        def inventory():
            text = (REFERENCE / ".agent/workflows/backend-api.md").read_text(encoding="utf-8")
            line = next(line for line in text.splitlines() if line.startswith("- **工具（43）**"))
            expected = set(re.findall(r"`([^`]+)`", line))
            result = self.call("admin", "GET", "/mcp-info")
            actual = {t["name"] for t in result["tools"]}
            assert len(result["tools"]) == 43 and actual == expected, {"missing": sorted(expected - actual), "extra": sorted(actual - expected)}
        self.scenario("DOC01-tools", "远程43个MCP工具名称集合和最新工作流文档完全一致", ["DOC-01"], inventory)

    def cleanup(self):
        product_ids = {f["id"] for f in self.state["fixtures"] if f["type"] == "product"}
        if product_ids and "employee" in self.sessions:
            try:
                for order in self.direct("employee", "GET", "/beli/orders"):
                    if order["product_id"] in product_ids and order["status"] == "pending":
                        self.direct("employee", "POST", f"/beli/orders/{order['id']}/action", {"action": "cancel"})
                        self.state["cleanup"].append({"type": "order", "id": order["id"], "status": "success", "action": "cancelled pending test order; unfrozen"})
            except Exception as error:
                self.state["cleanup"].append({"type": "order", "status": "failed", "error": str(error)[:350]})
        for item in reversed(self.state["fixtures"]):
            kind, item_id = item["type"], item["id"]
            if kind == "user" and item.get("reused"):
                assert item_id in {a["id"] for a in self.account_pool["accounts"].values()}
            else:
                assert item["name"].startswith(self.prefix + " ")
            entry = {"type": kind, "id": item_id, "status": "pending"}
            try:
                if kind == "project":
                    existing = self.sessions["manager"].get(API + f"/project/projects/{item_id}", timeout=30)
                    if existing.status_code == 404:
                        entry["action"] = "already deleted"
                    else:
                        existing.raise_for_status()
                        assert existing.json()["data"]["name"] == item["name"]
                        for todo in self.direct("manager", "GET", f"/project/projects/{item_id}/todos"):
                            if todo["status"] == "done":
                                detail = self.direct("manager", "GET", f"/todo/{todo['id']}")
                                assert detail["source_id"] == item_id
                                assert detail["creator_user_id"] == self.user_ids["manager"]
                                assert detail["assignee_user_id"] in self.user_ids.values()
                                self.direct("manager", "POST", f"/todo/{todo['id']}/status", {"status": "open"})
                        self.direct("manager", "DELETE", f"/project/projects/{item_id}")
                        entry["action"] = "reopened own test tasks to reverse awards, then deleted"
                elif kind == "custom_todo":
                    self.direct("employee", "POST", f"/todo/{item_id}/dismiss", {"dismiss_reason": self.prefix + " cleanup"})
                    entry["action"] = "dismissed (no delete endpoint)"
                elif kind == "product":
                    self.direct("manager", "PUT", f"/beli/products/{item_id}", {**item["body"], "active": False})
                    entry["action"] = "unpublished; audit retained"
                elif kind == "user":
                    desired = item.get("original_status", "inactive")
                    self.direct("admin", "PATCH", f"/iam/users/{item_id}", {"status": desired})
                    entry["action"] = f"reused account retained; restored status={desired}"
                else:
                    entry["action"] = "audit retained (no delete endpoint)"
                entry["status"] = "success"
            except Exception as error:
                entry.update(status="failed", error=str(error)[:350])
            self.state["cleanup"].append(entry)
            self.save()

    def report(self):
        for point in self.state["catalog"]:
            scenarios = [s for s in self.state["scenarios"] if point["id"] in s["case_points"]]
            point["evidence"] = [s["code"] for s in scenarios]
            point["remote_status"] = "partial" if scenarios else "not_run"
            if any(s["status"] == "failed" for s in scenarios):
                point["remote_status"] = "has_failure"
            if point["id"] == "DOC-01" and scenarios and all(s["status"] == "success" for s in scenarios):
                point["remote_status"] = "verified"
        self.state["finished_at"] = datetime.now(CN).isoformat()
        self.save()
        write_json(HERE / "case-catalog.json", self.state["catalog"])
        rows = self.state["scenarios"]
        success = sum(s["status"] == "success" for s in rows)
        failed = sum(s["status"] == "failed" for s in rows)
        untouched = [p["id"] for p in self.state["catalog"] if p["remote_status"] == "not_run"]
        content = ["# cases.md 远程场景执行报告", "", f"目标：{BASE}/；平台项目：PunkRecord ({PROJECT_ID})；源码参考：{SOURCE}。",
            f"本轮前缀：{self.prefix}；时间：{self.state['started_at']} 至 {self.state['finished_at']}。",
            "", f"44个原始测试点。本轮执行 {len(rows)} 个细分场景：{success}通过、{failed}失败。",
            f"平台原生API执行记录 {len(self.state['api_cases'])} 条；这不是44个测试点全部通过，也不是代码覆盖率。",
            "", "## 场景结果", "", "| 场景 | 原编号 | 结果 | 平台记录 | 限制/错误 |", "|---|---|---|---|---|"]
        for s in rows:
            records = ",".join(str(e["record_id"]) for e in s["evidence"] if "record_id" in e)
            limit = (s.get("error") or s.get("coverage_limit") or "").replace("|", "/").replace("\n", " ")
            content.append(f"| {s['code']} {s['title']} | {','.join(s['case_points'])} | {s['status']} | {records} | {limit} |")
        content += ["", "## 未执行与边界", "", "未执行原编号：" + ", ".join(untouched) + "。",
            "ATT系列会触发全员考勤结算；历史缺失字段/策略边界需隔离历史夹具；真实MySQL并发和迁移不能指向共享业务库。",
            "真实微信消息、小程序真机、收费AI/ASR、迁移、全量本地pytest和构建未执行，不能借用仓库旧报告计为本轮通过。",
            "已有图片、浏览器历史、完整移动端/暗色组合等缺口以逐条覆盖清单为准。",
            "", "## 清理", "", "仅处理本轮登记的前缀与ID，不扫描修改历史业务对象。",
            "新建项目删除、普通独立待办撤销、商品下架；固定测试账号保留并恢复运行前状态，不再每轮新建用户或职位。普通运行保留请假/订单/账本审计。",
            f"清理失败数：{sum(c['status'] == 'failed' for c in self.state['cleanup'])}。详见 case-suite-results.json。",
            "", "## 复跑", "", "通过环境变量提供 AUTOTEST_PASSWORD 和 PUNKRECORD_PASSWORD，执行 case_suite_runner.py run。",
            "不要单独重跑含已清理ID的API步骤；脚本会新建夹具并重新生成对应记录。凭证不写入脚本或导出的用例。"]
        report = "\n".join(content) + "\n"
        (HERE / "case-based-report.md").write_text(report, encoding="utf-8")
        for name, key, body in (("cases.md覆盖清单", "punkrecord.cases_md.catalog", json.dumps(self.state["catalog"], ensure_ascii=False, indent=2)),
                                 ("cases.md远程执行报告", "punkrecord.cases_md.report", report),
                                 ("测试脚本盘点", "punkrecord.cases_md.audit", (HERE / "case-script-audit.md").read_text(encoding="utf-8"))):
            saved = self.platform.call("POST", "/project-knowledge", {"project_id": PROJECT_ID, "name": name, "status": "active",
                "data": {"domain": "WEB", "kind": "test_coverage_review", "knowledge_key": key,
                         "source_file": name, "content": body, "verification_status": "partial", "source_commit": SOURCE}})
            self.state.setdefault("knowledge_ids", []).append(saved["id"])
        self.save()
        print(f"SUMMARY scenarios={len(rows)} success={success} failed={failed} api_records={len(self.state['api_cases'])}", flush=True)


def recover_cleanup():
    suite = Suite.__new__(Suite)
    suite.platform = Platform()
    suite.output = Path(os.environ.get("PUNKRECORD_CLEANUP_STATE", str(HERE / "case-suite-results.json"))).resolve()
    assert suite.output.parent == HERE and suite.output.suffix == ".json"
    suite.state = json.loads(suite.output.read_text(encoding="utf-8"))
    suite.prefix = suite.state["run_prefix"]
    suite.sessions, suite.auth, suite.user_ids = {}, {}, {}
    suite.login("admin", "admin", os.environ["PUNKRECORD_PASSWORD"])
    suite.account_pool = load_pool()
    fixed_password = read_password(suite.account_pool)
    fixture_users = [u for u in suite.state["fixtures"] if u["type"] == "user"]
    pool_ids = {a["id"] for a in suite.account_pool["accounts"].values()}
    assert all(u["id"] in pool_ids for u in fixture_users), "Legacy one-time users were removed; refusing automatic recreation or password resets"
    for actor in ("manager", "employee", "other"):
        user = next((u for u in suite.state["fixtures"] if u["type"] == "user" and u["username"].endswith("_" + actor)), None)
        if user:
            expected = suite.account_pool["accounts"][actor]
            assert user["id"] == expected["id"] and user["username"] == expected["username"]
            suite.direct("admin", "PATCH", f"/iam/users/{user['id']}", {"status": "active"})
            user["reused"] = True
            user.setdefault("original_status", "inactive")
            suite.login(actor, user["username"], fixed_password)
    for scenario in suite.state["scenarios"]:
        if scenario["status"] == "running":
            scenario.update(status="interrupted", error="Stopped to fix deployed executor assertion compatibility; not a business failure")
        if "不支持的断言类型" in scenario.get("error", ""):
            scenario["failure_category"] = "script_compatibility"
    suite.cleanup()
    suite.report()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("catalog", "run", "cleanup"))
    parser.add_argument("--follow-up", action="store_true")
    parser.add_argument("--select", action="append", default=[])
    args = parser.parse_args()
    if args.command == "catalog":
        print("Generated", len(catalog()), "source test points")
        return
    if args.command == "cleanup":
        recover_cleanup()
        return
    suite = Suite()
    if args.follow_up:
        suite.state["selected_scenarios"] = ["BELI07-backfill", "BELI08-pending", "BELI08-rejected", "LEAVE01-03-approve", "LEAVE01-reject", "SHOP01-publish", "SHOP03-05-repeat", "DOC01-tools"]
        suite.save()
    if args.select:
        suite.state["selected_scenarios"] = args.select
        suite.save()
    try:
        suite.setup()
        suite.permission_scenarios()
        suite.task_scenarios()
        suite.bug_scenarios()
        suite.reward_scenarios()
        suite.leave_scenarios()
        suite.shop_scenarios()
        suite.documentation()
    finally:
        suite.cleanup()
        suite.report()


if __name__ == "__main__":
    main()
