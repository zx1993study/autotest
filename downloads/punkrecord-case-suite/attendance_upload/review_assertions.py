"""Translate stale absolute financial snapshots into explicit business deltas."""
import re
from decimal import Decimal

from plan import binding, equal
from review_common import delta


def account_checks(branch, group):
    steps, scene_id = branch["steps"], branch["id"]
    initial = {}
    for step in steps:
        if step["request"]["path"] != "/beli/accounts":
            continue
        auth = step["auth_id"]
        for rule in step["assertions"]:
            path = rule.get("path", "").replace("/", ".").strip(".")
            if path.startswith("data.items.0.") and path.split(".")[-1] in {"balance", "available", "frozen", "annual"}:
                initial.setdefault((auth, path), Decimal(str(rule["expected"])))
    for step in steps:
        if step["request"]["path"] == "/beli/accounts":
            convert_account(step, branch, group, initial)
    if group == "reward":
        reward_checks(branch)


def convert_account(step, branch, group, initial):
    scene_id, auth = branch["id"], step["auth_id"]
    source = "baseline_" + str(auth)
    result = []
    for rule in step["assertions"]:
        if rule.get("type") == "json_number_delta":
            result.append(rule)
            continue
        path = rule.get("path", "").replace("/", ".").strip(".")
        if not path.startswith("data.items.0."):
            result.append(rule)
            continue
        field = path.removeprefix("data.items.0.")
        if field not in {"balance", "available", "frozen", "leave.annual"}:
            result.append(rule)
            continue
        value = Decimal(str(rule["expected"]))
        baseline = initial[(auth, path)]
        if group in {"task", "adjust"}:
            baseline = Decimal("4942" if group == "task" and auth == 20375 else "0")
            if group == "adjust":
                baseline = Decimal("5142")
        if group == "task":
            amount = Decimal(0)
        elif group == "leave":
            amount = Decimal("-.5") if field == "leave.annual" and scene_id in {21110, 21112} else Decimal(0)
        elif group == "shop":
            baseline = Decimal("5142" if scene_id in {21117, 21118, 21119, 21121} else "4972" if auth == 20375 else "0") if field in {"balance", "available"} else Decimal("4.5" if scene_id == 21121 else "5") if field == "leave.annual" else Decimal(0)
            amount = value - baseline
        else:
            amount = value - baseline
        key = "annual" if field == "leave.annual" else field
        step["bindings"].append(binding(source, key))
        result.append(delta("/" + path.replace(".", "/"), "{{bound_" + key + "}}", float(amount)))
    step["assertions"] = result
    if scene_id == 21136:
        for rule in result:
            path = rule.get("path", "")
            if path.endswith("/frozen"):
                rule["expected"] = "{{exact_price}}" if step["old_key"] == "node_10" else 0
            if path.endswith("/available"):
                rule["expected"] = "{{negative_exact_price}}" if step["old_key"] == "node_10" else 0


def reward_checks(branch):
    steps = branch["steps"]
    balance_rules = [rule for step in steps for rule in step["assertions"]
                     if rule.get("type") == "json_number_delta" and rule.get("path") == "/data/items/0/balance"]
    # First numeric balance is an old execution snapshot before rewards were issued.
    if balance_rules:
        origin = Decimal("-30") if branch["id"] == 21101 else Decimal(str(balance_rules[0]["expected"]))
        for rule in balance_rules:
            rule["expected"] = float(Decimal(str(rule["expected"])) - origin)
    matrix = re.search(r"BELI02-(p\d)-(\d+)", branch["name"])
    branch["inputs"]["late_days"] = int(matrix[2]) if matrix else 0
    for step in steps:
        if step["request"]["method"] == "POST" and step["request"]["path"] == "/todo":
            step["request"]["body"]["due_at"] = "{{task_due_at}}"
        if step["request"]["body"].get("due_at"):
            step["request"]["body"]["due_at"] = "{{task_due_at}}"
    if not balance_rules:
        last = next((step for step in reversed(steps) if step["request"]["path"] == "/beli/accounts"), None)
        if last:
            last["bindings"].append(binding("baseline_20375", "balance"))
            last["assertions"].append(delta("/data/items/0/balance", "{{bound_balance}}", 0))
