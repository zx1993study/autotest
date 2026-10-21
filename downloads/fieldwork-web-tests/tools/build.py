"""Build deterministic source contracts without inventing write scenarios."""

import json
import re
import shutil
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8-sig"))


def save(name, value):
    target = ROOT / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def route_of(value):
    parts = urlsplit(value or "")
    return (parts.fragment if parts.fragment.startswith("/") else parts.path).rstrip("/") or "/"


def step(name, action, locator, **extra):
    return {"name": name, "action": action, "locator_type": "css", "locator": locator,
            "require_unique": True, **extra}


def plan_feature(feature, inventory, origin):
    route = route_of(feature["data"].get("route") or feature["data"].get("url"))
    binding = next((item for item in inventory["routes"] if item["route"].rstrip("/") == route), None)
    source = inventory["components"].get((binding or {}).get("component"), {})
    kind = feature["data"].get("feature_type")
    result = {"feature_id": feature["id"], "name": feature["name"], "route": route,
              "feature_type": kind, "url": origin + route, "source": source.get("source"),
              "source_sha256": source.get("sha256"), "commit": inventory["commit"],
              "status": "blocked", "reason": "", "candidate": None,
              "fields": source.get("fields", []), "rules": source.get("rules", []),
              "api": source.get("api", []), "list_api": source.get("list_api", []), "search_fields": []}
    if not binding or not source or source.get("error"):
        result["reason"] = "Route/component is absent or cannot be parsed; no guessed alias is used"
    elif ":" in route:
        result["reason"] = "Dynamic route requires a run-owned record ID"
    elif feature.get("status") != "active":
        result["reason"] = "Feature is disabled"
    elif kind == "page" and re.search("新增|添加|删除|审批|提交|导出|编辑", feature["name"]):
        result["reason"] = "Feature name describes a business action but stored type is page; review classification first"
    elif kind not in {"page", "query"}:
        result["reason"] = "Requires confirmed business steps, run-owned fixtures and explicit write approval"
    else:
        result = readonly_plan(result, source, inventory)
    return result


def readonly_plan(result, source, inventory):
    tables = [table for table in source.get("tables", []) if not table["hidden"]]
    toolbars = [bar for bar in source.get("toolbars", []) if not bar["hidden"]]
    if len(tables) != 1:
        result["reason"] = "A unique top-level list table cannot be proven from source"
        return result
    header = next(iter(tables[0].get("headers", [])), None)
    if not header:
        result["reason"] = "No stable unconditional table header; visibility alone is not a business assertion"
        return result
    steps = [step("Wait for the source list header", "assert", ".app-main .el-table:visible", expected=header)]
    result["table_data"] = tables[0]["data"]
    if result["feature_type"] == "query":
        if len(toolbars) != 1 or not toolbars[0].get("name"):
            result["reason"] = "Query uses a custom/dynamic toolbar; needs a page-specific adapter"
            return result
        config = inventory["configs"].get(toolbars[0]["name"], {})
        result["search_fields"] = [field for field in config.get("fields", []) if field and field.get("search")]
        if not result["search_fields"]:
            result["reason"] = "Search field configuration cannot be resolved statically"
            return result
        if len(result["list_api"]) != 1:
            result["reason"] = "List request cannot be uniquely linked to getList; no guessed endpoint is used"
            return result
        steps += [step("Query", "click", '.unified-list__actions button:has-text("查询"):visible'),
                  step("List header remains visible", "assert", ".app-main .el-table:visible", expected=header)]
    result.update(status="source_ready", reason="Generated from source; real DOM replay still required",
                  candidate={"name": result["name"], "url": result["url"], "steps": steps,
                             "input_info": {}, "source_evidence": {key: result[key] for key in (
                                 "commit", "source", "source_sha256", "feature_id")}})
    return result


def existing_cases(snapshot, features):
    plans = []
    lookup = {item["feature_id"]: item for item in features}
    for original in snapshot["cases"]:
        feature = lookup.get(original["source_id"], {})
        result = {"case_id": original["id"], "feature_id": original["source_id"],
                  "name": original["name"], "status": "blocked", "reason": "Recorded steps require business/input/assertion review before conversion",
                  "candidate": None, "input_info": {}, "original_step_count": len(original["steps"])}
        if feature.get("feature_type") == "query" and feature.get("status") == "source_ready":
            inputs = {}
            for item in original["steps"]:
                if item.get("skip") or item["action"] != "fill":
                    continue
                matches = [field for field in feature["search_fields"] if field.get("type", "input") == "input"
                           and (field["label"] in item["locator"])]
                if len(matches) == 1 and item["value"] not in (None, ""):
                    inputs[matches[0]["key"]] = item["value"]
            if inputs:
                field = next(field for field in feature["search_fields"] if field["key"] in inputs)
                candidate = json.loads(json.dumps(feature["candidate"]))
                candidate["steps"][1:1] = [
                    step("Select current query field", "select", ".unified-list__condition:visible .unified-list__field input", value=field["label"]),
                    step("Fill original query value", "fill", ".unified-list__condition:visible .unified-list__value input", value="{{" + field["key"] + "}}"),
                ]
                candidate["steps"].insert(5, step("Filtered result contains the original query value", "assert",
                    ".app-main .el-table:visible .el-table__body-wrapper", expected="{{" + field["key"] + "}}"))
                candidate["steps"].extend([
                    step("Reset search", "click", '.unified-list__actions button:has-text("重置"):visible'),
                    step("List remains visible after reset", "assert", ".app-main .el-table:visible", expected=candidate["steps"][0]["expected"]),
                ])
                result.update(status="source_ready", reason="Source toolbar replaces hidden legacy form; original input values retained",
                              candidate=candidate, input_info=inputs,
                              search_fields=feature["search_fields"], list_api=feature["list_api"])
        if feature.get("route") == "/login":
            result["reason"] = "Legacy login has no reliable expected outcome; requires per-case credentials/captcha and assertion review"
        if feature.get("feature_type") == "delete":
            result["reason"] = "Legacy delete has no owned record ID/row scope; historical records must not be selected"
        plans.append(result)
    return plans


def build():
    snapshot, inventory = read("platform-snapshot.json"), read("source-inventory.json")
    features = [plan_feature(item, inventory, snapshot["origin"]) for item in snapshot["features"]]
    cases = existing_cases(snapshot, features)
    catalog = {"project_id": snapshot["project_id"], "repository": inventory["repository"],
               "commit": inventory["commit"], "features": features, "cases": cases}
    save("catalog.json", catalog)
    save("inputs.json", {str(item["case_id"]): item["input_info"] for item in cases})
    summary = {"commit": inventory["commit"], "features": dict(Counter(item["status"] for item in features)),
               "existing_cases": dict(Counter(item["status"] for item in cases)),
               "original_cases": len(cases), "new_cases": 0}
    save("generation-summary.json", summary)
    bundle_runtime(features, cases)
    lines = ["# 管理端 Web 脚本生成报告", "", f"源码版本：`{inventory['commit']}`", "",
             "已有用例保留，不新建重复用例。source_ready 仅表示源码已生成，不表示页面回放或业务测试通过。", "",
             "## 已有用例", "", "| 用例 ID | 功能 ID | 名称 | 状态 | 说明 |", "|---:|---:|---|---|---|"]
    lines += [f"| {item['case_id']} | {item['feature_id']} | {item['name']} | {item['status']} | {item['reason']} |" for item in cases]
    lines += ["", "## 页面功能脚本", "", "| 功能 ID | 路由 | 类型 | 状态 | 说明 |", "|---:|---|---|---|---|"]
    lines += [f"| {item['feature_id']} | {item['route']} | {item['feature_type']} | {item['status']} | {item['reason']} |" for item in features]
    (ROOT / "generation-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary))


def bundle_runtime(features, cases):
    source = ROOT.parents[1] / "web_automation/src/web_automation"
    for relative in ("__init__.py", "engines/__init__.py", "engines/playwright.py"):
        target = ROOT / "web_automation" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if relative.endswith("__init__.py"):
            target.write_text("", encoding="utf-8")
        else:
            shutil.copyfile(source / relative, target)
    for feature in features:
        if not feature["candidate"]:
            continue
        save(f"scripts/feature_{feature['feature_id']}.json", feature["candidate"])
    for case in cases:
        if case["candidate"]:
            save(f"scripts/case_{case['case_id']}.json", case["candidate"])
        code = ("import sys\nfrom run import main\n\nif __name__ == '__main__':\n"
                f"    result = main(['--case', '{case['case_id']}', *sys.argv[1:]])\n"
                "    raise SystemExit(0 if result['status'] == 'passed' else 2 if result['status'] == 'blocked' else 1)\n")
        (ROOT / f"case_{case['case_id']}.py").write_text(code, encoding="utf-8")


if __name__ == "__main__":
    build()
