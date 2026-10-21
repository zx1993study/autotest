"""Produce a reviewable, deterministic migration plan without database writes."""
import json

from catalog import GROUPS, classify, scenario_name
from compiler import compile_group, flatten, signature
from inventory import HERE, PROJECT_ID, fingerprint, save
from prerequisites import prepare_attendance, prepare_shop, product_fixtures

NOTICE = "配置归并，未重新执行；历史结果保留。复跑前须重新准备专用夹具、认证与余额预期，禁止重放历史订单/奖励/早会。"


def build(snapshot):
    cases = {c["id"]: c for c in snapshot["api_test_cases"]}
    branches, decisions = {}, []
    for flow in sorted(snapshot["execution_flows"], key=lambda x: x["id"]):
        group, reason = classify(flow)
        scenes = [s for s in snapshot["api_flow_scenarios"] if s["data"]["flow_id"] == flow["id"]]
        decision = {"flow_id": flow["id"], "name": flow["name"], "destination": group, "reason": reason,
                    "scene_ids": [s["id"] for s in scenes], "api_case_ids": []}
        for scene in scenes:
            steps = flatten(flow, scene, cases)
            decision["api_case_ids"].extend(s["case_id"] for s in steps)
            if group == "api":
                continue
            # Empty reasons are a parameter test, even if embedded in an adjustment chain.
            kept = []
            for step in steps:
                body = step["request"].get("body") or {}
                rejection = any(a.get("type") == "status" and a.get("expected", 200) >= 400 for a in step["assertions"])
                if rejection and "reason" in body and isinstance(body["reason"], str) and not body["reason"].strip():
                    continue
                kept.append(step)
            assert len(kept) >= 2, (flow["id"], "Not a multi-step business chain")
            branches.setdefault(group, []).append({"source_flow_id": flow["id"], "source_scene_id": scene["id"],
                "name": scenario_name(flow, scene), "description": scene.get("description") or flow["description"],
                "inputs": {**flow["data"].get("inputs", {}), **scene["data"].get("inputs", {})},
                "failure_policy": scene["data"].get("failure_policy", "stop"), "steps": kept})
        decision["api_case_ids"] = sorted(set(decision["api_case_ids"]))
        decisions.append(decision)
    canonical = {}
    base_cases = {}
    products = product_fixtures()
    for row in branches.get("shop", []):
        prepare_shop(row, products)
    for row in branches.get("attendance", []):
        prepare_attendance(row)
    for rows in branches.values():
        for row in rows:
            for step in row["steps"]:
                key = signature(step)
                canonical[key] = min(canonical.get(key, step["api_id"]), step["api_id"])
    groups = []
    for group, rows in branches.items():
        definition = compile_group(rows, canonical)
        for row in rows:
            for step in row["steps"]:
                key = repr((signature(step), step["auth_id"]))
                method, path = signature(step)
                base_cases[key] = {"project_id": PROJECT_ID, "source_id": canonical[(method, path)],
                    "name": "链路共享节点 " + method + " " + path + " / 认证" + str(step["auth_id"]),
                    "status": "active", "description": "共享参数化节点，业务输入及断言由功能场景提供；不要单独执行。",
                    "assertions": [], "steps": [], "data": {"method": method, "path": path,
                        "auth_id": step["auth_id"], "api_base_path": step["request"].get("api_base_path", "/api/v1"),
                        "content_type": step["request"].get("content_type", "application/json")}}
        groups.append({"key": group, "name": GROUPS[group][0], "description": GROUPS[group][1] + "。" + NOTICE,
                       "definition": definition, "branches": rows})
    return {"project_id": PROJECT_ID, "source_fingerprint": fingerprint(snapshot),
            "decisions": decisions, "groups": groups, "base_cases": base_cases}


def render(plan):
    lines = ["# PunkRecord 功能流程整理方案", "", "仅整理测试平台配置，不执行业务接口。", "",
        "功能流程按业务目标组织；场景是该链路的通过、拒绝、取消、重复操作等分支，不是单字段输入变体。",
        "空文本、纯空格、长文本、数值格式、独立授权与文档检查只保留在原 API 正式用例下。", "",
        "## 归并后的流程", "", "| 流程 | 场景数 | 模板节点数 | 链路 |", "|---|---:|---:|---|"]
    for group in plan["groups"]:
        lines.append(f"|{group['name']}|{len(group['branches'])}|{len(group['definition']['nodes'])}|{GROUPS[group['key']][1]}|")
    lines += ["", "## 执行与历史", "", "- 每个场景显式覆盖实际请求、认证节点、断言、提取及参数绑定；复用共享 API 节点，不把各参数变体再建成流程。",
        "- 同场景节点必须按原顺序执行，只跳过其他分支专有节点。原参数传递与失败策略保留。",
        "- 新场景不继承旧 latest_status/latest_run_id，不把历史通过冒充新场景通过。",
        "- 旧流程与场景软删除；原 API 用例、接口、历史运行记录及快照均保留。",
        "- 新模板保持停用。旧夹具/余额/日期不安全自动重放，准备新夹具并重新核对预期后才能启用。",
        "- 早会结算会影响全体人员；必须在隔离业务环境准备早会文稿/录音与员工名单后执行，不能用手工扣款替代。", "",
        "## 原条目去向", "", "| 原ID | 原流程 | 去向 | 原因 |", "|---:|---|---|---|"]
    for row in plan["decisions"]:
        destination = "原 API 正式用例" if row["destination"] == "api" else GROUPS[row["destination"]][0]
        lines.append(f"|{row['flow_id']}|{row['name']}|{destination}|{row['reason']}|")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    snapshot = json.loads((HERE / "before.json").read_text(encoding="utf-8"))
    result = build(snapshot)
    save(HERE / "plan.json", result)
    (HERE / "plan.md").write_text(render(result), encoding="utf-8")
    print(json.dumps({"flows_before": len(snapshot["execution_flows"]), "flows_after": len(result["groups"]),
        "api_only": sum(d["destination"] == "api" for d in result["decisions"]),
        "shared_cases": len(result["base_cases"]),
        "groups": [{"name": g["name"], "scenes": len(g["branches"]), "nodes": len(g["definition"]["nodes"])} for g in result["groups"]]}, ensure_ascii=True))
