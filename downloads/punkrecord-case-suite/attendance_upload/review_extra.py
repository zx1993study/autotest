"""Missing state-transition branches added to the existing business flows."""
from copy import deepcopy

from plan import binding, equal, extract
from review_common import EMPLOYEE, OTHER, account_baseline, delta, node


def extras(group, branches):
    if group == "task":
        branch = deepcopy(branches[0])
        branch.update(id=None, name="TASK-EARLY-REVIEW 未提交的任务不能验收，任务状态与余额不变")
        created = deepcopy(branch["steps"][0])
        approve = node("early_review", "POST", "/todo/{task_id}/approve", assertions=[{"type": "status", "expected": 400}])
        created["extracts"] = [extract("task_id", "/data/id")]
        approve["bindings"] = [binding(created["old_key"], "task_id", "params")]
        detail = node("task_state", "GET", "/todo/{task_id}", 20375)
        detail["bindings"] = deepcopy(approve["bindings"])
        detail["assertions"] += [equal("/data/status", "open")]
        branch["steps"] = [created, approve, detail]
        return [branch]
    if group == "reward":
        branch = deepcopy(next(b for b in branches if b["id"] == 21087))
        branch.update(id=None, name="REWARD-REJECT-REVIEW 奖励拒绝不发钱，重新审核通过后仅到账一次")
        award = next(step for step in branch["steps"] if step["request"]["path"].endswith("/review"))
        rejected = deepcopy(award)
        rejected["old_key"] = "reject_reward"
        rejected["request"]["body"] = {"action": "reject", "comment": "本轮拒绝后重审-{{run_tag}}"}
        rejected["assertions"] = [equal("/code", 0), equal("/data/status", "rejected"), {"type": "status", "expected": 200}]
        rejected["extracts"] = []
        index = branch["steps"].index(award)
        check = account_baseline(20375)
        check["old_key"] = "rejected_balance"
        check["bindings"] = [binding("baseline_20375", "balance")]
        check["assertions"] += [delta("/data/items/0/balance", "{{bound_balance}}", 0)]
        branch["steps"][index:index] = [rejected, check]
        return [branch]
    if group == "leave":
        before = node("leave_before", "GET", "/todo/leaves/my", 20376)
        before["extracts"] = [extract("leaves", "/data")]
        attempt = node("leave_attempt", "POST", "/todo/leaves", 20376, {
            "leave_type": "annual", "start_at": "{{leave_start}}", "end_at": "{{leave_end}}",
            "reason": "假期不足拒绝链路-{{run_tag}}"}, [{"type": "status", "expected": 400}])
        after = deepcopy(before)
        after["old_key"] = "leave_after"
        after["bindings"] = [binding("leave_before", "leaves")]
        after["assertions"] += [equal("/data", "{{bound_leaves}}")]
        final = account_baseline(20376)
        final["old_key"] = "leave_balance_after"
        final["bindings"] = [binding("baseline_20376", "annual")]
        final["assertions"] += [delta("/data/items/0/leave/annual", "{{bound_annual}}", 0)]
        return [{"id": None, "name": "LEAVE-INSUFFICIENT 假期额度不足不创建申请、不扣假", "inputs": {},
                 "failure_policy": "stop", "steps": [before, attempt, after, final]}]
    if group == "project":
        branch = deepcopy(next(b for b in branches if b["id"] == 21064))
        branch.update(id=None, name="PROJECT-EMPTY-SYNC 空功能清单重复同步不产生任务")
        for step in branch["steps"]:
            if "feature_list" in step["request"].get("body", {}):
                step["request"]["body"]["feature_list"] = "[]"
            if step["request"]["path"].endswith("/sync-dev-tasks"):
                step["assertions"] = [{"type": "status", "expected": 200}, equal("/code", 0)] + [
                    equal("/data/" + field, 0) for field in ("created", "deleted", "feature_total")]
            if step["request"]["path"].endswith("/todos"):
                step["extracts"] = []
                step["assertions"] = [{"type": "status", "expected": 200}, equal("/code", 0), equal("/data", [])]
        return [branch]
    return []
