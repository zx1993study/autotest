"""Apply business step labels through flow/scenario services, without executing APIs."""
import argparse
import json
import re
from copy import deepcopy

from bootstrap import HERE, CampaignRepository, fingerprint, save
from flow_reorganization.compiler import signature

TYPES = {"morning": "早会", "weekly": "周会", "project": "项目会议", "review": "复盘会议",
         "brainstorm": "头脑风暴", "other": "其他"}
ACTORS = {20373: "L0管理员（test_user1）", 20374: "直属主管（test_user2）",
          20375: "员工（test_user3）", 20376: "员工（test_user4）"}
STEPS = {
    ("GET", "/beli/accounts"): "查询贝利余额及假期额度",
    ("GET", "/beli/attendance"): "核对早会考勤与扣款状态",
    ("GET", "/beli/ledger"): "核对贝利变动流水",
    ("GET", "/beli/orders"): "查询商城订单及审批状态",
    ("POST", "/beli/orders"): "购买商品并创建兑换订单",
    ("POST", "/beli/orders/{id}/action"): "审核或处理商城订单",
    ("GET", "/beli/products"): "查询商品及库存",
    ("POST", "/beli/products"): "创建测试商品",
    ("PUT", "/beli/products/{id}"): "更新商品上下架状态",
    ("GET", "/beli/rewards"): "查询待审核贝利奖励",
    ("POST", "/beli/rewards/{id}/review"): "审核贝利奖励",
    ("POST", "/beli/accounts/{id}/adjust"): "调整测试账号贝利或假期额度",
    ("GET", "/meeting/records"): "查询会议列表",
    ("POST", "/meeting/records"): "创建会议",
    ("GET", "/meeting/records/{id}"): "查看会议详情与参会人",
    ("DELETE", "/meeting/records/{id}"): "删除本次创建的会议",
    ("POST", "/meeting/records/{id}/upload-transcript"): "上传会议文稿",
    ("POST", "/project/projects"): "创建隔离测试项目",
    ("DELETE", "/project/projects/{id}"): "清理本次测试项目",
    ("GET", "/project/projects/{id}/bugs"): "查询项目缺陷",
    ("GET", "/project/projects/{id}/todos"): "查询项目开发任务",
    ("GET", "/project/projects/{id}/stages"): "查询项目阶段与功能清单",
    ("PATCH", "/project/projects/{id}/stages/{id}"): "更新项目阶段及功能清单",
    ("POST", "/project/projects/{id}/sync-dev-tasks"): "同步项目开发任务",
    ("POST", "/project/projects/{id}/generate-dev-tasks"): "生成项目开发任务",
    ("POST", "/project/projects/{id}/todos/{id}/plan"): "规划项目任务工时与截止日期",
    ("GET", "/todo/my"): "查询我的待办任务",
    ("POST", "/todo"): "创建业务任务",
    ("GET", "/todo/{id}"): "查看任务详情与验收状态",
    ("PATCH", "/todo/{id}"): "更新任务信息与状态",
    ("POST", "/todo/{id}/status"): "变更任务业务状态",
    ("POST", "/todo/{id}/submit"): "提交任务完成并申请验收",
    ("POST", "/todo/{id}/approve"): "验收任务：同意通过",
    ("POST", "/todo/{id}/reject"): "验收任务：拒绝",
    ("GET", "/todo/leaves/my"): "查询我的请假申请",
    ("GET", "/todo/leaves/team/pending"): "查看团队待审批请假",
    ("POST", "/todo/leaves"): "提交请假申请",
    ("POST", "/todo/leaves/{id}/approve"): "审核请假：同意通过",
    ("POST", "/todo/leaves/{id}/reject"): "审核请假：拒绝",
}


def node_name(request, actor=None, inputs=None):
    request = {**request, "path": re.sub(r"\{\{[^{}]+\}\}", "{id}", request["path"])}
    route = signature({"request": request})
    name = STEPS[route]  # Unknown routes require an explicit mapping, never guess business semantics.
    body = request.get("body") or {}
    if route == ("POST", "/meeting/records"):
        kind = body.get("meeting_type")
        if kind == "{{meeting_type}}":
            kind = (inputs or {}).get("meeting_type")
        if kind in TYPES:
            name = "创建早会-类型：" + TYPES[kind] if kind == "morning" else "创建会议-类型：" + TYPES[kind]
    if route in {("POST", "/beli/orders/{id}/action"), ("POST", "/beli/rewards/{id}/review")}:
        action = body.get("action")
        actions = {"approve": "同意通过", "reject": "拒绝", "cancel": "取消订单", "ship": "确认发货"}
        if action in actions:
            name = ("审核订单" if "/orders/" in route[1] else "审核贝利奖励") + "：" + (actor or "当前操作人") + actions[action]
    elif actor and route[1].endswith(("/approve", "/reject")):
        name = name.replace("：", "：" + actor, 1)
    return name


def unchanged_steps(data):
    value = deepcopy(data)
    value.pop("version", None)
    value.pop("template_version", None)
    nodes = value["nodes"].values() if isinstance(value["nodes"], dict) else value["nodes"]
    for node in nodes:
        node.pop("name", None)
    return value


def template_names(repo, flows):
    changes = []
    for flow in flows:
        data = deepcopy(flow["data"])
        for node in data["nodes"]:
            if re.match(r"^(GET|POST|PUT|PATCH|DELETE) ", node["name"]):
                api = repo.get("api_interfaces", node["api_id"])
                node["name"] = node_name(api["data"])
        if data != flow["data"]:
            assert unchanged_steps(data) == unchanged_steps(flow["data"])
            changes.append((flow, data))
    return changes


def apply_labels(apply=False):
    from app.db.session import SessionLocal
    from app.repositories.sqlalchemy_resource_repository import (
        SqlAlchemyResourceRepository,
    )
    from app.services.api_flow_scenario_service import ApiFlowScenarioService
    from app.services.api_flow_values import apply_request_override
    from app.services.execution_flow_service import ExecutionFlowService

    with SessionLocal() as db:
        repo = CampaignRepository(SqlAlchemyResourceRepository(db))
        flows, _ = repo.list("execution_flows", project_id=17796, page_size=100)
        scenes, _ = repo.list("api_flow_scenarios", project_id=17796, page_size=1000)
        batches, _ = repo.list("api_flow_runs", project_id=17796, page_size=1000)
        assert not any(row["status"] in {"running", "queued"} for row in batches)
        before = {row["id"]: fingerprint(row) for row in batches}
        templates = template_names(repo, flows)
        changes = []
        for scene in scenes:
            flow = next(flow for flow in flows if flow["id"] == scene["data"]["flow_id"])
            data = deepcopy(scene["data"])
            for node in flow["data"]["nodes"]:
                override = data["nodes"].setdefault(node["key"], {})
                case = repo.get("api_test_cases", override.get("case_id") or node.get("case_id"))
                request = deepcopy((case or {}).get("data") or repo.get("api_interfaces", node["api_id"])["data"])
                request = {**request.pop("request", {}), **request}
                for configured in (node, override):
                    apply_request_override(request, configured)
                auth = node.get("auth_id") or request.get("auth_id")
                label = node_name(request, ACTORS.get(auth), {**flow["data"]["inputs"], **data["inputs"]})
                if not re.match(r"^(GET|POST|PUT|PATCH|DELETE) ", node["name"]) and node["key"] not in {"create", "create_second"}:
                    label = node["name"]
                if node["key"] == "create_second":
                    label = label.replace("创建早会", "创建第二场早会")
                override["name"] = override.get("name") or label
            assert unchanged_steps(data) == unchanged_steps(scene["data"])
            changes.append((scene, data))
        if apply:
            backup = HERE / "node-name-before.json"
            if not backup.exists():
                save(backup, {"templates": [{"id": f["id"], "version": f["data"]["version"],
                    "names": {n["key"]: n["name"] for n in f["data"]["nodes"]}} for f, _ in templates],
                    "scenarios": [{"flow_id": s["data"]["flow_id"], "scene_id": s["id"],
                    "names": {key: node.get("name") for key, node in s["data"]["nodes"].items()}} for s, _ in changes]})
            versions = {}
            for flow, data in templates:
                updated = ExecutionFlowService(repo).update(flow["id"], {"data": data})
                versions[flow["id"]] = updated["data"]["version"]
            service = ApiFlowScenarioService(repo)
            for scene, data in changes:
                if data["flow_id"] in versions:
                    service.sync(data["flow_id"], scene["id"])
                    data["template_version"] = versions[data["flow_id"]]
                service.update_for_flow(data["flow_id"], scene["id"], {"data": data})
        after, _ = repo.list("api_flow_runs", project_id=17796, page_size=1000)
        assert before == {row["id"]: fingerprint(row) for row in after}, "Historical evidence must not change"
        return {"applied": apply, "templates": len(templates), "scenarios": len(changes),
                "examples": [{"scene_id": scene["id"], "names": {key: n["name"] for key, n in data["nodes"].items()
                    if key in {"create", "review_node_12", "review_node_14"}}}
                    for scene, data in changes if scene["id"] in {21310, 21314, 21117, 21118}]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    print(json.dumps(apply_labels(parser.parse_args().apply), ensure_ascii=True))
