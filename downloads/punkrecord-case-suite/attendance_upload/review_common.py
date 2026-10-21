"""Scenario configuration helpers, not application execution logic."""
import re
from copy import deepcopy

from bootstrap import HERE, save
from flow_reorganization.compiler import signature
from plan import OK, binding, equal, extract

EMPLOYEE = "640d1a5c-bff5-4df0-9e02-cb42f8b46413"
OTHER = "b65fa560-e319-4363-84b0-5dbf9e2f2728"
MANAGER = "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9"
OLD_PROJECT = "4b1cca48-28f1-4e90-bb20-cce59ab7d3a7"
GROUPS = {21062: "project", 21066: "task", 21070: "bug", 21072: "reward", 21107: "adjust",
          21109: "leave", 21114: "product", 21116: "shop"}
PREFIX = re.compile(r"CASE_\d{8}_\d{6}")


def node(key, method, path, auth=20373, body=None, assertions=None):
    return {"old_key": key, "api_id": None, "case_id": 0, "auth_id": auth,
            "request": {"method": method, "path": path, "body": body or {}, "query": {}, "params": {},
                        "auth_id": auth, "content_type": "application/json", "api_base_path": "/api/v1"},
            "bindings": [], "extracts": [], "assertions": deepcopy(OK if assertions is None else assertions)}


def delta(path, baseline, amount):
    return {"type": "json_number_delta", "path": path, "baseline": baseline, "expected": amount}


def account_baseline(auth):
    result = node("baseline_" + str(auth), "GET", "/beli/accounts", auth)
    result["extracts"] = [extract(key, "/data/items/0/" + path) for key, path in (
        ("balance", "balance"), ("available", "available"), ("frozen", "frozen"), ("annual", "leave/annual"))]
    result["assertions"] += [equal("/data/items/0/user_id", OTHER if auth == 20376 else EMPLOYEE)]
    return result


def replace_strings(value, replacements):
    if isinstance(value, dict):
        return {key: replace_strings(item, replacements) for key, item in value.items()}
    if isinstance(value, list):
        return [replace_strings(item, replacements) for item in value]
    if isinstance(value, str):
        value = PREFIX.sub("{{run_tag}}", value)
        for old, new in replacements.items():
            value = value.replace(old, new)
    return value


def project_fixture():
    result = node("fixture_project", "POST", "/project/projects", body={
        "name": "回归隔离项目-{{run_tag}}", "project_no": "REG-{{run_uuid}}", "project_type": "b2b",
        "pm_user_id": MANAGER, "description": "只供本轮自动化回归；通过API清理"})
    result["extracts"] = [extract("campaign_project_id", "/data/id")]
    return result


def project_bound(step):
    if "{{bound_campaign_project_id}}" in str(step["request"]):
        step["bindings"].append(binding("fixture_project", "campaign_project_id"))
        path = step["request"]["path"]
        if "{{bound_campaign_project_id}}" in path:
            step["request"]["path"] = path.replace("{{bound_campaign_project_id}}", "{campaign_project_id}")
            step["bindings"].append(binding("fixture_project", "campaign_project_id", "params"))


def post_to_created(key, method, path, created, body=None):
    result = node(key, method, path, body=body)
    source, name = created["old_key"], created["extracts"][-1]["name"]
    result["request"]["path"] = path.replace("{new_id}", "{" + name + "}")
    result["bindings"] = [binding(source, name, "params")]
    return result
