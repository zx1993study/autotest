"""Native API regression for the four user-authorized hierarchical test accounts."""
from datetime import datetime, timedelta
from decimal import Decimal
import json
from uuid import uuid4

from case_suite_runner import CN, HERE
from shop_rich_native import Shop

OUTPUT = HERE / "four-account-permission-results.json"


class Permissions(Shop):
    def __init__(self):
        super().__init__(OUTPUT)
        self.case_label = "FOURACCOUNT"

    def run_all(self):
        pool = self.account_pool["accounts"]

        def hierarchy():
            for actor, account in pool.items():
                self.step(actor, "admin", "GET", f"/iam/users/{account['id']}", equals={
                    "data.username": account["username"], "data.manager_user_id": account["manager_user_id"],
                    "data.level": {"manager": 0, "supervisor": 1, "employee": 2, "other": 2}[actor]})
        self.execute("FOUR-HIERARCHY", "四账号三级上下级关系与级别持久化", hierarchy,
                     lambda values: {"accounts_checked": len(values), "new_users_created": 0})

        def scopes():
            for actor in pool:
                self.step(actor, actor, "GET", "/beli/accounts", equals={"data.is_l0": actor == "manager"})
        def verify_scopes(values):
            for actor in ("supervisor", "employee", "other"):
                assert [item["user_id"] for item in values[actor]["items"]] == [self.user_ids[actor]]
            assert {self.user_ids[a] for a in ("supervisor", "employee", "other")} <= {u["user_id"] for u in values["manager"]["items"]}
            return {"non_l0_self_only": 3, "l0_can_manage_test_employees": True}
        self.execute("FOUR-ACCOUNT-SCOPE", "L0可管理员工，非L0只能查看自己的贝利账户", scopes, verify_scopes)

        def salary():
            for actor in pool:
                self.step(actor, actor, "GET", f"/iam/users/{self.user_ids['employee']}/salary", expected=403)
        self.execute("FOUR-SALARY-GUARD", "四个业务测试账号均不能读取工资", salary, lambda _: {"forbidden": 4})

        task_ids = {}
        for assignee in ("employee", "other"):
            symbolic = str(uuid4())
            title = self.prefix + " FOUR " + assignee + " supervisor acceptance"
            body = {"title": title, "assignee_user_id": self.user_ids[assignee], "estimated_hours": 1,
                "due_at": (datetime.now(CN) + timedelta(days=1)).replace(hour=18, minute=0, second=0, microsecond=0).isoformat(),
                "priority": "p2", "link": {"reviewer_user_id": self.user_ids["supervisor"]}}
            before = self.balance(assignee)
            def acceptance(assignee=assignee, symbolic=symbolic, body=body, before=before):
                self.step("create", assignee, "POST", "/todo", body, response={"code": 0, "data": {"id": symbolic}})
                self.step("submit", assignee, "POST", f"/todo/{symbolic}/submit", equals={"data.status": "pending_review"})
                self.step("self_approve_forbidden", assignee, "POST", f"/todo/{symbolic}/approve", expected=404)
                peer = "other" if assignee == "employee" else "employee"
                self.step("peer_approve_forbidden", peer, "POST", f"/todo/{symbolic}/approve", expected=404)
                self.step("supervisor_accept", "supervisor", "POST", f"/todo/{symbolic}/approve", equals={"data.status": "done"})
                self.account_step("no_automatic_reward", before, actor=assignee)
                self.step("reward_pending", assignee, "GET", "/beli/rewards")
            def verify_acceptance(values, assignee=assignee):
                task = values["create"]
                assert any(r["todo_id"] == task["id"] and r["status"] == "pending" for r in values["reward_pending"])
                task_ids[assignee] = task["id"]
                self.state["fixtures"].append({"type": "custom_todo", "id": task["id"], "name": task["title"]})
                return {"task_id": task["id"], "l1_task_acceptance_allowed": True, "reward_still_pending": True}
            self.execute("FOUR-TASK-ACCEPT-" + assignee.upper(), "本人及同级不能验收，L1主管可验收" + pool[assignee]["username"] + "任务，验收不自动发奖", acceptance, verify_acceptance)
        assert set(task_ids) == {"employee", "other"}, "New task fixtures incomplete"
        self.state["test_task_ids"] = task_ids
        self.save()
        employee_task = task_ids["employee"]

        for action in ("approve", "reject"):
            before = self.balance()
            def forbidden(action=action, before=before):
                for actor in ("supervisor", "employee", "other"):
                    self.step(actor, actor, "POST", f"/beli/rewards/{employee_task}/review",
                        {"action": action, "comment": "non-L0 must not change reward"}, expected=403)
                self.account_step("unchanged_balance", before)
                self.step("reward_unchanged", "employee", "GET", "/beli/rewards")
            def verify_forbidden(values):
                assert next(r for r in values["reward_unchanged"] if r["todo_id"] == employee_task)["status"] == "pending"
                return {"forbidden_accounts": ["test_user2", "test_user3", "test_user4"], "reward_unchanged": True}
            self.execute("FOUR-REWARD-" + action.upper() + "-FORBIDDEN", "非L0主管和员工不能" + action + "奖励，即使是自己的下属", forbidden, verify_forbidden)

        before = self.balance()
        comment = self.prefix + " L0 rejection reason"
        def reject():
            self.step("reject", "manager", "POST", f"/beli/rewards/{employee_task}/review", {"action": "reject", "comment": comment},
                equals={"data.status": "rejected", "data.comment": comment})
            self.step("employee_reason", "employee", "GET", "/beli/rewards")
            self.step("task_still_done", "employee", "GET", f"/todo/{employee_task}", equals={"data.status": "done"})
            self.account_step("balance_unchanged", before)
        def verify_reject(values):
            row = next(r for r in values["employee_reason"] if r["todo_id"] == employee_task)
            assert row["status"] == "rejected" and row["comment"] == comment
            return {"reason_visible_to_owner": True, "task_remains_done": True, "no_money_changed": True}
        self.execute("FOUR-L0-REJECT", "L0可驳回，员工可见原因，任务仍完成且不扣贝利", reject, verify_reject)

        before = self.balance()
        ledger_before = {r["id"] for r in self.ledger()}
        def approve():
            for key in ("approve", "repeat"):
                self.step(key, "manager", "POST", f"/beli/rewards/{employee_task}/review", {"action": "approve"},
                    equals={"data.status": "approved", "data.amount": 30})
            self.account_step("paid_once", before, balance_delta=30)
        def verify_approve(values):
            added = [r for r in self.ledger() if r["id"] not in ledger_before]
            assert len(added) == 1 and Decimal(str(added[0]["amount"])) == 30
            return {"reward_amount": 30, "new_ledger_count": 1, "account_before": before["balance"], "account_after": self.balance()["balance"]}
        self.execute("FOUR-L0-APPROVE-ONCE", "L0可重新审核已驳回奖励，重复批准只发30贝利一次", approve, verify_approve)

        def visibility():
            for actor in ("supervisor", "employee", "other"):
                self.step(actor, actor, "GET", "/beli/rewards")
        def verify_visibility(values):
            for actor, rows in values.items():
                assert all(r["user_id"] == self.user_ids[actor] for r in rows)
                assert all("snapshot" not in r and "basic_salary" not in r for r in rows)
            assert not any(r["todo_id"] in task_ids.values() for r in values["supervisor"])
            return {"non_l0_only_own_rewards": 3, "l1_cannot_read_subordinate_rewards": True, "salary_not_leaked": True}
        self.execute("FOUR-REWARD-VISIBILITY", "非L0主管也只能看本人奖励，不能查看下属奖励和工资快照", visibility, verify_visibility)

        before = self.balance()
        ledger_before = {r["id"] for r in self.ledger()}
        def amount_boundaries():
            for index, (amount, expected) in enumerate((("0", 400), ("99999999999999999999999999", 422),
                    ("-9999999999999999999999", 422), ("0.0005", 422))):
                self.step("amount_" + str(index), "manager", "POST", f"/beli/accounts/{self.user_ids['employee']}/adjust",
                    {"amount": amount, "reason": self.prefix + " amount boundary", "request_key": str(uuid4())}, expected=expected)
            self.account_step("unchanged_account", before)
        def verify_amounts(_):
            assert {r["id"] for r in self.ledger()} == ledger_before
            return {"invalid_amounts": 4, "balance_frozen_leave_unchanged": True, "ledger_unchanged": True}
        self.execute("FOUR-ADJUST-BOUNDARIES", "调整余额0、超大正负数、0.0005均拒绝且不改变账户流水", amount_boundaries, verify_amounts)

        calendar = {row["day"]: row["is_workday"] for row in self.direct("employee", "GET", "/beli/calendar")}
        day = datetime.now(CN).date() + timedelta(days=1)
        while not calendar.get(day.isoformat(), day.weekday() < 5):
            day += timedelta(days=1)
        for reviewer, action in (("supervisor", "approve"), ("manager", "reject")):
            symbolic = str(uuid4())
            before = self.balance("other")
            leave_type = "annual" if action == "approve" else "personal"
            body = {"leave_type": leave_type, "start_at": day.isoformat() + "T09:00:00+08:00",
                "end_at": day.isoformat() + "T12:00:00+08:00", "reason": self.prefix + " hierarchical leave " + action}
            def leave_chain(reviewer=reviewer, action=action, symbolic=symbolic, body=body, before=before):
                self.step("create", "other", "POST", "/todo/leaves", body, response={"code": 0, "data": {"id": symbolic}})
                self.step("direct_pending", "supervisor", "GET", "/todo/leaves/team/pending")
                self.step("root_pending", "manager", "GET", "/todo/leaves/team/pending")
                for actor in ("employee", "other"):
                    self.step(actor + "_forbidden", actor, "POST", f"/todo/leaves/{symbolic}/" + action,
                        {"comment": "forbidden"} if action == "reject" else {}, expected=400)
                self.step("review", reviewer, "POST", f"/todo/leaves/{symbolic}/" + action,
                    {"comment": self.prefix + " hierarchy rejection"} if action == "reject" else {},
                    equals={"data.status": "approved" if action == "approve" else "rejected"})
                self.step("duplicate", reviewer, "POST", f"/todo/leaves/{symbolic}/" + action,
                    {"comment": "duplicate"} if action == "reject" else {}, expected=400)
                self.account_step("leave_count", before, actor="other", leave_delta=-.5 if action == "approve" else 0)
            def verify_leave(values, action=action):
                leave = values["create"]
                assert any(row["id"] == leave["id"] for row in values["direct_pending"])
                assert not any(row["id"] == leave["id"] for row in values["root_pending"])
                self.state["fixtures"].append({"type": "leave", "id": leave["id"], "name": self.prefix + " hierarchical leave " + action})
                return {"leave_id": leave["id"], "direct_manager_pending_only": True,
                    "annual_change": -.5 if action == "approve" else 0, "duplicate_rejected": True}
            self.execute("FOUR-LEAVE-CHAIN-" + action.upper(), "test_user4请假：同级和本人拒绝、" + ("L1直属主管通过只扣半天一次" if action == "approve" else "L0跨级主管可驳回且不扣假"), leave_chain, verify_leave)
            day += timedelta(days=1)
            while not calendar.get(day.isoformat(), day.weekday() < 5):
                day += timedelta(days=1)


def main():
    suite = Permissions()
    try:
        suite.run_all()
    finally:
        suite.cleanup()
        suite.state["final_account"] = suite.balance()
        suite.state["finished_at"] = datetime.now(CN).isoformat()
        suite.save()
        print("SUMMARY", json.dumps({"total": len(suite.state["scenarios"]), "success": sum(s["status"] == "success" for s in suite.state["scenarios"]),
            "failed": [s["code"] for s in suite.state["scenarios"] if s["status"] != "success"]}), flush=True)


if __name__ == "__main__":
    main()
