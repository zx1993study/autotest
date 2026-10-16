"""Validation shared by template editing, scenario sync and execution."""

from jsonpointer import JsonPointer, JsonPointerException
from pydantic import ValidationError

from app.core.exceptions import BusinessRuleError
from app.schemas.execution_flow import FlowDefinition


def parse_definition(data):
    try:
        return FlowDefinition.model_validate(data).model_dump()
    except ValidationError as exc:
        raise BusinessRuleError("流程模板格式不正确", str(exc)) from exc


def validate_references(repository, project_id, definition, scenario=None, running=False):
    nodes = definition["nodes"]
    positions = {node["key"]: index for index, node in enumerate(nodes)}
    if len(positions) != len(nodes):
        raise BusinessRuleError("节点标识不能重复")
    overrides = (scenario or {}).get("nodes", {})
    if set(overrides) - positions.keys():
        raise BusinessRuleError("场景引用了已删除的节点，请同步模板")
    if running and not nodes:
        raise BusinessRuleError("流程至少需要一个节点")
    if (scenario or {}).get("expected_end", "auto") not in {"auto", *positions}:
        raise BusinessRuleError("预期结束节点不存在")
    for node in nodes:
        override = overrides.get(node["key"], {})
        _validate_node_resource(repository, project_id, node, override, running)
        _validate_targets(node, positions)
        bindings = override.get("bindings") if override.get("bindings") is not None else node["bindings"]
        conditions = [override["condition"]] if override.get("condition") else []
        if override.get("mode") == "condition" and not conditions:
            raise BusinessRuleError(f"{node['name']}缺少执行条件")
        for reference in [*bindings, *conditions]:
            source = reference["source"]
            if source != "global" and (source not in positions or positions[source] >= positions[node["key"]]):
                raise BusinessRuleError(f"{node['name']}只能引用前置节点或场景输入")
        extracts = override.get("extracts") if override.get("extracts") is not None else node["extracts"]
        names = [item["name"] for item in extracts]
        if len(set(names)) != len(names):
            raise BusinessRuleError(f"{node['name']}的提取变量名重复")
        for spec in [*bindings, *extracts, *node["routes"]]:
            if spec.get("target") in {"params", "headers", "query", "body"} or spec.get("source") == "body":
                try:
                    paths = spec["paths"] if spec.get("mode") == "array" else [spec.get("path", "")]
                    for path in paths:
                        JsonPointer(path)
                except JsonPointerException as exc:
                    raise BusinessRuleError(f"{node['name']}包含无效的 JSON Pointer 路径") from exc
        for configured in (node, override):
            for path in configured.get("request_removals", []):
                try:
                    JsonPointer(path)
                except JsonPointerException as exc:
                    raise BusinessRuleError(f"{node['name']}包含无效的参数删除路径") from exc


def _validate_node_resource(repository, project_id, node, override, running):
    interface = repository.get("api_interfaces", node["api_id"])
    if not interface or interface.get("project_id") != project_id:
        raise BusinessRuleError(f"{node['name']}的 API 不存在或不属于当前项目")
    auth_id = node.get("auth_id")
    if auth_id:
        auth = repository.get("project_auth", auth_id)
        if not auth or auth.get("project_id") != project_id:
            raise BusinessRuleError("认证配置必须属于当前项目")
    case_id = override.get("case_id") or node.get("case_id")
    if not case_id:
        if running and override.get("mode") != "skip":
            raise BusinessRuleError(f"{node['name']}尚未选择节点用例")
        return
    case = repository.get("api_test_cases", case_id)
    if not case or case.get("project_id") != project_id or case.get("source_id") != node["api_id"]:
        raise BusinessRuleError(f"{node['name']}的用例与当前 API 或项目不匹配")
    if running and str(case.get("status", "active")) != "active":
        raise BusinessRuleError(f"{node['name']}的用例未启用")


def _validate_targets(node, positions):
    for target in [node["next"], *(route["target"] for route in node["routes"])]:
        if target in {"auto", "end"}:
            continue
        if target not in positions or positions[target] <= positions[node["key"]]:
            raise BusinessRuleError(f"{node['name']}的后续节点必须位于当前节点之后")
    names = [item["name"] for item in node["extracts"]]
    if len(set(names)) != len(names):
        raise BusinessRuleError(f"{node['name']}的提取变量名重复")
