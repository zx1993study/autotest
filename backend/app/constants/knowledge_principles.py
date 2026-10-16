"""System-managed test principle metadata."""

from __future__ import annotations

from app.constants.knowledge_principle_scenarios import PRINCIPLE_SCENARIOS
from app.core.types import JsonObject
from app.enums.business import KnowledgePrincipleEnum


KNOWLEDGE_VERSION = 2


def _principle(
    principle: KnowledgePrincipleEnum,
    description: str,
    category: str,
    priority: str,
    tags: list[str],
    content: str,
) -> JsonObject:
    """Build normalized system knowledge while keeping metadata reviewable."""

    return {
        "name": principle.desc,
        "description": description,
        "data": {
            "knowledge_key": f"principle.{principle.code}",
            "principle_code": principle.code,
            "kind": "test_principle",
            "domain": "COMMON",
            "category": category,
            "priority": priority,
            "tags": tags,
            "content": content,
            "template_json": {
                "scenarios": PRINCIPLE_SCENARIOS[principle.code],
            },
            "managed_by": "system",
            "version": KNOWLEDGE_VERSION,
        },
    }


DEFAULT_KNOWLEDGE_ITEMS: list[JsonObject] = [
    _principle(
        KnowledgePrincipleEnum.CONDITION_COVERAGE,
        "覆盖需求中的单条件、组合条件以及条件不成立时的分支。",
        "condition",
        "P1",
        ["条件覆盖", "组合条件", "业务规则"],
        "识别页面需求中的前置条件、可见条件、启停条件和互斥条件，覆盖真假分支与关键组合。",
    ),
    _principle(
        KnowledgePrincipleEnum.BOUNDARY_TESTING,
        "覆盖最小值、最大值、临界点和越界值。",
        "boundary",
        "P1",
        ["边界值", "临界点", "越界"],
        "从长度、数值、日期、数量和分页限制中提取边界，验证边界内、边界点和边界外。",
    ),
    _principle(
        KnowledgePrincipleEnum.EXCEPTION_TESTING,
        "覆盖非法格式、类型错误、重复操作和服务异常。",
        "exception",
        "P1",
        ["异常输入", "重复提交", "错误恢复"],
        "针对页面输入、重复操作、请求失败和权限异常验证错误提示、数据一致性与恢复能力。",
    ),
    _principle(
        KnowledgePrincipleEnum.SMOKE_TESTING,
        "优先验证页面可访问和核心业务链路可完成。",
        "smoke",
        "P0",
        ["冒烟", "核心流程", "可用性"],
        "用最少测试点确认页面加载、核心查询和核心新增或提交链路可用。",
    ),
    _principle(
        KnowledgePrincipleEnum.BULK_INSERT,
        "验证批量新增的数量、部分失败和重复数据处理。",
        "data",
        "P1",
        ["批量插入", "事务", "数据一致性"],
        "覆盖批量新增最小数量、正常批量、上限数量、重复数据和部分非法数据。",
    ),
    _principle(
        KnowledgePrincipleEnum.INPUT_OVERWRITE,
        "验证输入框已有内容在编辑和回填时是否被意外覆盖。",
        "interaction",
        "P1",
        ["输入框", "回填", "内容覆盖"],
        "验证页面初始化、异步回填、切换选项和保存失败后，用户已输入内容不会被意外覆盖。",
    ),
    _principle(
        KnowledgePrincipleEnum.TEXT_LENGTH_LIMIT,
        "验证文本框长度限制、计数提示和粘贴超限行为。",
        "boundary",
        "P1",
        ["文本框", "长度限制", "粘贴"],
        "对单行和多行文本验证最大长度、超限输入、粘贴、多字节字符和首尾空格。",
    ),
    _principle(
        KnowledgePrincipleEnum.NUMBER_RANGE_LIMIT,
        "验证数字输入框的范围、精度、步长和非法字符。",
        "boundary",
        "P1",
        ["数字输入框", "范围", "精度"],
        "验证数字最小值、最大值、超限值、负数、小数精度、步长和非数字输入。",
    ),
]


LEGACY_DEFAULT_KEYS = {
    "strategy.equivalence_class",
    "strategy.boundary_value",
    "strategy.abnormal_input",
    "strategy.auth_permission",
    "strategy.state_transition",
    "template.api.success",
    "template.api.required_missing",
    "template.api.type_mismatch",
    "template.api.unauthorized",
    "template.web.form_success",
    "template.web.required_empty",
    "template.web.delete_confirm",
    "template.app.flow_success",
    "template.app.network_error",
}
