"""Legacy compatibility checks through current remote HTTP with test-only fixtures."""
import base64
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess

from account_pool import load_pool, read_password, use_existing_accounts
from case_suite_runner import BASE, CN, HERE, Platform
from supplement_beli import OUTPUT, Supplement


def shape(suite, task_id, mode, **extra):
    source = (HERE / "remote_history_fixture.py").read_bytes()
    encoded = base64.b64encode(source).decode("ascii")
    code = "import os,sys,base64; os.chdir('/srv/workspaces/zheyang/punkrecord/backend'); sys.path.insert(0,os.getcwd()); exec(compile(base64.b64decode('" + encoded + "'),'<test-history-fixture>','exec'))"
    command = "/opt/miniconda3/envs/punkrecord/bin/python -c '" + code.replace("'", "'\\''") + "'"
    plan = {"target": BASE, "prefix": suite.prefix, "project_id": suite.pid, "task_id": task_id, "mode": mode, **extra}
    result = subprocess.run(["ssh", "-i", str(Path.home() / ".ssh/id_xnous"), "-o", "BatchMode=yes", "xiaox@14.103.229.153", command],
        input=json.dumps(plan), text=True, encoding="utf-8", capture_output=True, timeout=60)
    assert result.returncode == 0, result.stderr[-1000:]
    evidence = json.loads(result.stdout.strip())
    suite.state.setdefault("history_fixture_audit", []).append(evidence)
    suite.save()


def main():
    suite = object.__new__(Supplement)
    suite.state = json.loads(OUTPUT.read_text(encoding="utf-8"))
    suite.prefix = suite.state["run_prefix"]
    suite.pid = next(row["id"] for row in suite.state["fixtures"] if row["type"] == "project")
    suite.platform = Platform()
    suite.sessions, suite.auth, suite.user_ids, suite.interfaces = {}, {}, {}, {}
    suite.pats, suite.password, suite.current = {}, None, None
    latest = {row["code"]: row for row in suite.state["scenarios"]}
    codes = {"SUP-HISTORY-DATE", "SUP-HISTORY-HOURS", "SUP-HISTORY-SUBMIT", "SUP-HISTORY-PRE-RULE", "SUP-HISTORY-NO-TIME", "SUP-HISTORY-LEAVE"}
    suite.state["selected_scenarios"] = sorted({code for code in codes if latest.get(code, {}).get("status") != "success"} | {"SUP-LEDGER-RECONCILE"})
    try:
        suite.login("admin", "admin", os.environ["PUNKRECORD_PASSWORD"])
        pool = load_pool()
        use_existing_accounts(suite, pool, read_password(pool))
        def task(title, hours):
            found = [row for row in suite.direct("manager", "GET", f"/project/projects/{suite.pid}/todos") if row["title"] == suite.prefix + " " + title]
            assert len(found) <= 1, "Ambiguous historical fixture; refusing duplicate creation"
            return found[0]["id"] if found else suite.task(title, hours=hours)
        def missing_date():
            tid = task("历史夹具 缺截止日期", 0)
            shape(suite, tid, "missing_due")
            suite.call("employee", "POST", f"/todo/{tid}/submit", expected=400)
            suite.call("manager", "PATCH", f"/todo/{tid}", {"due_at": datetime.now(CN).replace(hour=18, minute=0, second=0, microsecond=0).isoformat()})
            suite.complete(tid)
        suite.scenario("SUP-HISTORY-DATE", "本轮历史缺日期夹具提交拒绝，补齐后可验收", ["TODO-04"], missing_date)
        def missing_hours():
            tid = task("历史夹具 空工时", 0)
            shape(suite, tid, "missing_hours")
            suite.call("employee", "GET", f"/todo/{tid}", equals={"data.estimated_hours": None})
            suite.complete(tid)
            suite.call("employee", "GET", f"/todo/{tid}", equals={"data.estimated_hours": None, "data.status": "done"})
            suite.rewards(tid)
            suite.call("manager", "POST", f"/beli/rewards/{tid}/review", {"action": "approve"}, expected=400)
        suite.scenario("SUP-HISTORY-HOURS", "历史空工时不覆盖、不阻止验收、不参与奖励", ["TODO-04"], missing_hours)
        def missing_submit():
            tid = task("历史夹具 待验收缺提交时间", 1)
            if suite.direct("employee", "GET", f"/todo/{tid}")["status"] != "pending_review":
                suite.call("employee", "POST", f"/todo/{tid}/submit")
            shape(suite, tid, "missing_submit")
            suite.call("manager", "POST", f"/todo/{tid}/approve", expected=400)
            suite.call("manager", "POST", f"/todo/{tid}/status", {"status": "open"})
            suite.complete(tid)
            detail = suite.call("employee", "GET", f"/todo/{tid}")
            assert detail["submitted_at"] and detail["submitted_at"].startswith(str(datetime.now(CN).date()))
            suite.rewards(tid, "pending")
        suite.scenario("SUP-HISTORY-SUBMIT", "历史待验收缺提交时间拒绝，撤回重提后通过", ["TODO-07"], missing_submit)
        def old_completion():
            tid = task("历史夹具 生效前已完成", 0)
            if suite.direct("employee", "GET", f"/todo/{tid}")["status"] != "done":
                suite.complete(tid)
            shape(suite, tid, "predates_rule")
            before = suite.call("employee", "GET", f"/todo/{tid}")
            for _ in range(2):
                suite.call("manager", "PATCH", f"/todo/{tid}", {"estimated_hours": 2})
            after = suite.call("employee", "GET", f"/todo/{tid}")
            assert after["done_at"] == before["done_at"] and after["submitted_at"] == before["submitted_at"]
            suite.rewards(tid)
        suite.scenario("SUP-HISTORY-PRE-RULE", "生效前已完成任务补录工时不追溯入队", ["BELI-09"], old_completion)
        def missing_done_submit():
            tid = task("历史夹具 完成后缺提交时间", 0)
            if suite.direct("employee", "GET", f"/todo/{tid}")["status"] != "done":
                suite.complete(tid)
            shape(suite, tid, "missing_submit")
            suite.call("manager", "PATCH", f"/todo/{tid}", {"estimated_hours": 1})
            suite.call("employee", "GET", f"/todo/{tid}", equals={"data.submitted_at": None})
            suite.rewards(tid)
        suite.scenario("SUP-HISTORY-NO-TIME", "历史已完成缺可靠提交时间，补录不伪造时间或发奖", ["BELI-09"], missing_done_submit)
        def legacy_leave():
            tid = task("历史夹具 请假旧待办", 1)
            leave_id = next(row["id"] for row in suite.state["fixtures"] if row["type"] == "leave_audit")
            shape(suite, tid, "historical_leave", leave_id=leave_id)
            suite.call("employee", "GET", f"/todo/{tid}", equals={"data.id": tid})
            rows = suite.call("employee", "GET", "/todo/my?page_size=100")
            assert all(row["id"] != tid for row in rows["items"])
            for actor, action, body in [("employee", "start", None), ("employee", "submit", None), ("manager", "approve", None),
                    ("manager", "reject", {"comment": "legacy"}), ("employee", "dismiss", {"dismiss_reason": "legacy"}),
                    ("manager", "status", {"status": "done"})]:
                suite.call(actor, "POST", f"/todo/{tid}/{action}", body, expected=400)
            suite.rewards(tid)
            suite.call("employee", "GET", f"/todo/{tid}", equals={"data.id": tid, "data.status": "open"})
        suite.scenario("SUP-HISTORY-LEAVE", "历史请假待办保留可读，列表隔离且六类旧写操作拒绝", ["LEAVE-02"], legacy_leave)
        suite.scenario("SUP-LEDGER-RECONCILE", "历史兼容补测后全量流水与余额复核", ["BELI-05", "BELI-06"], suite.reconciliation)
    finally:
        suite.state.pop("selected_scenarios", None)
        suite.cleanup()
        suite.report()


if __name__ == "__main__":
    main()
