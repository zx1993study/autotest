"""Retry only failed supplementary steps, retaining existing accounts and rewards."""
import json
import os

from account_pool import load_pool, read_password, use_existing_accounts
from case_suite_runner import Platform
from supplement_beli import OUTPUT, Supplement


def main():
    suite = object.__new__(Supplement)
    suite.state = json.loads(OUTPUT.read_text(encoding="utf-8"))
    suite.prefix = suite.state["run_prefix"]
    suite.pid = next(row["id"] for row in suite.state["fixtures"] if row["type"] == "project")
    suite.platform = Platform()
    suite.sessions, suite.auth, suite.user_ids, suite.interfaces = {}, {}, {}, {}
    suite.pats, suite.password, suite.current = {}, None, None
    if suite.state.get("fatal_error"):
        suite.state.setdefault("script_errors", []).append(suite.state.pop("fatal_error"))
    try:
        suite.login("admin", "admin", os.environ["PUNKRECORD_PASSWORD"])
        pool = load_pool()
        use_existing_accounts(suite, pool, read_password(pool))
        latest = {row["code"]: row for row in suite.state["scenarios"]}
        if latest.get("SUP-MCP-LEAVE", {}).get("status") != "success":
            suite.scenario("SUP-MCP-LEAVE", "真实MCP请假待审批、批准、驳回，不创建待办（解析修正重测）", ["LEAVE-05"], suite.mcp_leave)
        suite.scenario("SUP-LEDGER-RECONCILE", "MCP补测后全量流水与期末余额再核对", ["BELI-05", "BELI-06"], suite.reconciliation)
        if latest.get("SUP-WEB-EARNINGS", {}).get("status") != "success":
            suite.visible_case()
    finally:
        suite.cleanup()
        suite.report()


if __name__ == "__main__":
    main()
