"""Repair scenario fixtures and assertions without changing application code."""
import json
import re
from copy import deepcopy
from datetime import date, timedelta

from bootstrap import HERE
from flow_reorganization.compiler import compile_group, flatten, signature
from plan import binding, equal, extract
from review_assertions import account_checks
from review_extra import extras
from review_common import (EMPLOYEE, GROUPS, OLD_PROJECT, OTHER, account_baseline,
                           delta, node, post_to_created, project_bound, project_fixture, replace_strings)


def normalize(branch, group):
    keys, replacements = {}, {OLD_PROJECT: "{{bound_campaign_project_id}}"}
    for step in branch["steps"]:
        request = step["request"]
        for field in ("api_path", "api_method", "project_name", "case_type"):
            request.pop(field, None)
        request["params"] = {key: value for key, value in request.get("params", {}).items()
                             if not any(b["target"] == "params" and b["path"] == "/" + key for b in step["bindings"])}
        old_key = (request.get("body") or {}).get("request_key")
        if old_key:
            keys.setdefault(old_key, "request_uuid_" + str(len(keys) + 1))
            request["body"]["request_key"] = "{{" + keys[old_key] + "}}"
    branch["steps"] = replace_strings(branch["steps"], replacements)
    branch["inputs"].update({key: "{{uuid}}" for key in keys.values()})
    branch["inputs"].update(run_tag="回归-{{timestamp_ms}}", run_uuid="{{uuid}}")
    for step in branch["steps"]:
        project_bound(step)
        for extraction in step["extracts"]:
            selection = extraction.get("selection")
            if selection and "{{run_tag}}" in str(selection):
                if step["request"]["path"].endswith("/todos"):
                    extraction.update(path="/data/0/id", selection=None)
                else:
                    assert not any(b["source"] == step["old_key"] and b["name"] == extraction["name"]
                                   for row in branch["steps"] for b in row["bindings"])
                    extraction.update(required=False, selection=None, path="/data/0/id")
    if group == "shop" and branch["id"] == 21136:
        for step in branch["steps"]:
            if step["request"]["method"] == "POST" and step["request"]["path"] == "/beli/products":
                step["request"]["body"]["price"] = "{{exact_price}}"
    if branch["id"] == 21122:
        for step in branch["steps"]:
            if step["request"]["path"].endswith("/adjust"):
                field = "decrease_amount" if float(step["request"]["body"]["amount"]) < 0 else "restore_amount"
                step["request"]["body"]["amount"] = "{{" + field + "}}"
    account_checks(branch, group)


def fixtures(branch, group):
    steps = branch["steps"]
    auths = {s["auth_id"] for s in steps if s["request"]["path"] == "/beli/accounts" and s["auth_id"] in {20375, 20376}}
    if group in {"reward", "adjust", "shop", "leave"}:
        auths.add(20375)
    prefix = [account_baseline(auth) for auth in sorted(auths)]
    if group in {"project", "task", "reward", "bug"}:
        prefix.append(project_fixture())
        for step in steps:
            if step["request"].get("body", {}).get("due_at") and group != "reward":
                step["request"]["body"]["due_at"] = "{{task_due_at}}"
            for task in step["request"].get("body", {}).get("tasks", []):
                task["due_at"] = "{{task_due_at}}"
        if group == "reward":
            created = next(s for s in steps if s["request"]["path"] == "/todo" and s["request"]["method"] == "POST")
            steps.append(post_to_created("cleanup_reward", "POST", "/todo/{new_id}/status", created, {"status": "open"}))
        cleanup = node("cleanup_project", "DELETE", "/project/projects/{campaign_project_id}")
        cleanup["bindings"] = [binding("fixture_project", "campaign_project_id", "params")]
        steps.append(cleanup)
    if group == "leave":
        prepare_leave(branch, prefix)
    branch["steps"] = prefix + steps


def prepare_leave(branch, prefix):
    created = next(s for s in branch["steps"] if s["request"]["path"] == "/todo/leaves" and s["request"]["method"] == "POST")
    actor = created["auth_id"]
    if actor == 20376 and branch["id"] == 21112:
        grant = node("prepare_leave", "POST", "/beli/accounts/" + OTHER + "/adjust", body={
            "amount": ".5", "leave_type": "annual", "reason": "本轮请假审批夹具-{{run_tag}}", "request_key": "{{grant_uuid}}"})
        prefix.insert(0, grant)
        branch["inputs"]["grant_uuid"] = "{{uuid}}"
    created["request"]["body"].update(start_at="{{leave_start}}", end_at="{{leave_end}}")
    # Compare task count before and after this leave, not a historical list total.
    count = next((s for s in branch["steps"] if s["request"]["path"] == "/todo/my"), None)
    if count:
        count["extracts"].append(extract("todo_count", "/data/total"))
        for step in branch["steps"]:
            if step is count or step["request"]["path"] != "/todo/my":
                continue
            step["bindings"].append(binding(count["old_key"], "todo_count"))
            step["assertions"] = [a for a in step["assertions"] if a.get("path") != "data.total"]
            step["assertions"].append(equal("/data/total", "{{bound_todo_count}}"))


def build(snapshot):
    cases = {row["id"]: row for row in snapshot["api_test_cases"]}
    groups = []
    canonical = {}
    for api in snapshot["api_interfaces"]:
        try:
            key = signature({"request": api["data"]})
            canonical[key] = min(canonical.get(key, api["id"]), api["id"])
        except KeyError:
            continue
    for flow in sorted(snapshot["execution_flows"], key=lambda row: row["id"]):
        if flow["id"] not in GROUPS:
            continue
        group, branches = GROUPS[flow["id"]], []
        for scene in sorted(snapshot["api_flow_scenarios"], key=lambda row: row["id"]):
            if scene["data"]["flow_id"] != flow["id"]:
                continue
            branch = {"id": scene["id"], "name": scene["name"], "inputs": {}, "failure_policy": "stop",
                      "steps": flatten(flow, scene, cases)}
            branches.append(branch)
        branches += extras(group, branches)
        for branch in branches:
            normalize(branch, group)
            fixtures(branch, group)
        for branch in branches:
            for step in branch["steps"]:
                key = signature(step)
                if key not in canonical:
                    canonical[key] = -1 - sum(value < 0 for value in canonical.values())
                step["api_id"] = canonical[key]
        definition = compile_group(branches, canonical)
        renames = {item["key"]: "review_" + item["key"] for item in definition["nodes"]}
        for item in definition["nodes"]:
            item["key"] = renames[item["key"]]
        for branch in branches:
            data = branch["compiled"]
            data["nodes"] = {renames[key]: value for key, value in data["nodes"].items()}
            data["expected_end"] = renames[data["expected_end"]]
            for item in data["nodes"].values():
                for configured in item.get("bindings", []):
                    if configured["source"] != "global":
                        configured["source"] = renames[configured["source"]]
        groups.append({"id": flow["id"], "version": flow["data"]["version"], "group": group,
                       "definition": definition, "branches": branches})
    return groups


if __name__ == "__main__":
    from bootstrap import save
    source = json.loads((HERE / "current-inventory.json").read_text(encoding="utf-8"))
    result = build(source)
    save(HERE / "review-plan.json", result)
    print(json.dumps([{"id": g["id"], "group": g["group"], "scenes": len(g["branches"]),
                       "nodes": len(g["definition"]["nodes"])} for g in result]))
