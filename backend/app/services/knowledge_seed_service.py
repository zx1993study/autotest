from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.repositories.interfaces import ResourceRepository


DEFAULT_KNOWLEDGE_ITEMS: list[dict[str, Any]] = [
    {
        "name": "等价类划分策略",
        "description": "按有效等价类和无效等价类拆分输入条件，减少重复用例并覆盖关键输入集合。",
        "data": {
            "knowledge_key": "strategy.equivalence_class",
            "kind": "design_strategy",
            "domain": "COMMON",
            "category": "normal",
            "priority": "P1",
            "tags": ["等价类", "字段规则", "输入覆盖"],
            "content": "将输入值拆成有效等价类、无效等价类和空值类，每类至少生成 1 条代表性用例。",
            "template_json": {
                "rules": [
                    "从字段类型、枚举值、格式规则中提取有效输入",
                    "从非法格式、非法枚举、类型不匹配中提取无效输入",
                    "同类输入只保留代表性样本，避免用例膨胀",
                ]
            },
        },
    },
    {
        "name": "边界值分析策略",
        "description": "围绕长度、数值、日期、分页、金额等边界生成最小值、最大值和越界用例。",
        "data": {
            "knowledge_key": "strategy.boundary_value",
            "kind": "design_strategy",
            "domain": "COMMON",
            "category": "boundary",
            "priority": "P1",
            "tags": ["边界值", "长度", "数值", "分页"],
            "content": "对 min/max、长度限制、分页参数和日期范围生成边界内、边界点、边界外用例。",
            "template_json": {
                "rules": [
                    "字符串：空、最小长度、最大长度、最大长度 + 1",
                    "数字：min、min - 1、max、max + 1、0、负数",
                    "分页：page=1、pageSize=1、最大 pageSize、超大 pageSize",
                ]
            },
        },
    },
    {
        "name": "异常输入策略",
        "description": "针对类型错误、格式错误、特殊字符、SQL/XSS 注入样本生成异常用例。",
        "data": {
            "knowledge_key": "strategy.abnormal_input",
            "kind": "design_strategy",
            "domain": "COMMON",
            "category": "exception",
            "priority": "P1",
            "tags": ["异常输入", "安全", "非法格式"],
            "content": "对可输入字段生成类型不匹配、非法格式、特殊字符、注入片段和不可见字符用例。",
            "template_json": {
                "invalid_values": ["", "not-a-number", "<script>alert(1)</script>", "' OR '1'='1", "😀", " "]
            },
        },
    },
    {
        "name": "鉴权与权限策略",
        "description": "覆盖未登录、Token 过期、无权限、跨项目访问、重复登录等鉴权场景。",
        "data": {
            "knowledge_key": "strategy.auth_permission",
            "kind": "design_strategy",
            "domain": "COMMON",
            "category": "security",
            "priority": "P0",
            "tags": ["鉴权", "权限", "Token", "Cookie"],
            "content": "所有需要鉴权的接口、Web 页面和 App 页面都应覆盖未登录、无权限、过期凭证和跨项目数据访问。",
            "template_json": {
                "expected": ["401 未登录", "403 无权限", "Token 刷新后恢复访问", "不能访问其它项目数据"]
            },
        },
    },
    {
        "name": "状态流转策略",
        "description": "对草稿、启用、停用、删除、审核等状态流转生成正反向路径用例。",
        "data": {
            "knowledge_key": "strategy.state_transition",
            "kind": "design_strategy",
            "domain": "COMMON",
            "category": "flow",
            "priority": "P2",
            "tags": ["状态机", "流程", "审核"],
            "content": "识别实体状态和动作，覆盖合法流转、非法流转、重复操作和终态不可变更。",
            "template_json": {
                "rules": ["draft -> active", "active -> disabled", "disabled -> active", "deleted 后不可操作"]
            },
        },
    },
    {
        "name": "API 正常请求模板",
        "description": "根据接口字段示例生成一条基础成功请求。",
        "data": {
            "knowledge_key": "template.api.success",
            "kind": "case_template",
            "domain": "API",
            "category": "normal",
            "priority": "P1",
            "tags": ["API", "正常流程"],
            "content": "使用字段示例值或默认正常值发起请求，断言业务成功和状态码。",
            "template_json": {
                "name_pattern": "[正常] {method} {path}",
                "request": {"headers": "{auth_headers}", "query": "{normal_query}", "body": "{normal_body}"},
                "assertions": [{"type": "status", "expected": 200}, {"type": "business_success"}],
            },
        },
    },
    {
        "name": "API 必填参数缺失模板",
        "description": "对每个必填 query/header/body/path 字段生成缺失参数用例。",
        "data": {
            "knowledge_key": "template.api.required_missing",
            "kind": "case_template",
            "domain": "API",
            "category": "exception",
            "priority": "P1",
            "tags": ["API", "必填", "参数校验"],
            "content": "移除一个必填字段并发送请求，断言参数校验失败。",
            "template_json": {
                "name_pattern": "[缺失必填] {field_name}",
                "mutation": {"type": "remove_field", "field": "{field_name}", "location": "{location}"},
                "assertions": [{"type": "status", "expected": 400}, {"type": "message_contains", "expected": "{field_name}"}],
            },
        },
    },
    {
        "name": "API 字段类型错误模板",
        "description": "对数字、布尔、对象、数组等字段生成类型不匹配用例。",
        "data": {
            "knowledge_key": "template.api.type_mismatch",
            "kind": "case_template",
            "domain": "API",
            "category": "exception",
            "priority": "P2",
            "tags": ["API", "类型错误"],
            "content": "将字段值替换为不兼容类型，断言服务端返回明确校验错误。",
            "template_json": {
                "name_pattern": "[类型错误] {field_name}",
                "mutation": {"type": "replace_field", "value": "{invalid_by_type}"},
                "assertions": [{"type": "status", "expected": 400}],
            },
        },
    },
    {
        "name": "API 未登录访问模板",
        "description": "移除鉴权头或 Cookie 访问需要登录的接口。",
        "data": {
            "knowledge_key": "template.api.unauthorized",
            "kind": "case_template",
            "domain": "API",
            "category": "security",
            "priority": "P0",
            "tags": ["API", "鉴权", "401"],
            "content": "不携带 token/cookie 请求受保护接口，断言返回未登录。",
            "template_json": {
                "name_pattern": "[未登录] {method} {path}",
                "mutation": {"type": "remove_auth"},
                "assertions": [{"type": "status", "expected": 401}],
            },
        },
    },
    {
        "name": "Web 表单正常提交模板",
        "description": "按元素库中的 fill/select/click 步骤生成正常提交流程。",
        "data": {
            "knowledge_key": "template.web.form_success",
            "kind": "case_template",
            "domain": "WEB",
            "category": "normal",
            "priority": "P1",
            "tags": ["Web", "表单", "正常流程"],
            "content": "填写必填项和典型可选项，点击提交，断言成功提示或页面跳转。",
            "template_json": {
                "name_pattern": "[正常流程] {page_name}",
                "steps": ["fill_required_fields", "select_dropdowns", "click_submit"],
                "assertions": [{"type": "toast_or_url", "expected": "success"}],
            },
        },
    },
    {
        "name": "Web 必填为空模板",
        "description": "对新增/编辑弹窗中的必填输入框生成空值校验用例。",
        "data": {
            "knowledge_key": "template.web.required_empty",
            "kind": "case_template",
            "domain": "WEB",
            "category": "exception",
            "priority": "P1",
            "tags": ["Web", "必填", "弹窗"],
            "content": "清空一个必填输入项后提交，断言校验提示出现且弹窗不关闭。",
            "template_json": {
                "name_pattern": "[必填为空] {element_name}",
                "steps": ["open_feature_modal", "clear_field", "click_submit"],
                "assertions": [{"type": "validation_visible"}, {"type": "modal_still_visible"}],
            },
        },
    },
    {
        "name": "Web 删除二次确认模板",
        "description": "覆盖删除取消、删除确认、删除后列表刷新三类行为。",
        "data": {
            "knowledge_key": "template.web.delete_confirm",
            "kind": "case_template",
            "domain": "WEB",
            "category": "flow",
            "priority": "P2",
            "tags": ["Web", "删除", "确认弹窗"],
            "content": "点击删除后分别执行取消和确认，断言取消不变更数据、确认后数据消失。",
            "template_json": {
                "name_pattern": "[删除确认] {page_name}",
                "steps": ["click_delete", "assert_confirm_dialog", "cancel_or_confirm"],
                "assertions": [{"type": "list_changed_by_action"}],
            },
        },
    },
    {
        "name": "App 正常操作流程模板",
        "description": "按 App 页面元素生成 tap/input/select/submit 正常流程。",
        "data": {
            "knowledge_key": "template.app.flow_success",
            "kind": "case_template",
            "domain": "APP",
            "category": "normal",
            "priority": "P1",
            "tags": ["App", "正常流程", "设备执行"],
            "content": "根据页面元素顺序执行输入、选择、点击，断言目标页面或成功提示。",
            "template_json": {
                "name_pattern": "[正常流程] {page_name}",
                "steps": ["tap_inputs", "input_values", "tap_submit"],
                "assertions": [{"type": "toast_or_activity"}],
            },
        },
    },
    {
        "name": "App 网络异常模板",
        "description": "覆盖弱网、断网、接口超时后的页面提示和恢复行为。",
        "data": {
            "knowledge_key": "template.app.network_error",
            "kind": "case_template",
            "domain": "APP",
            "category": "exception",
            "priority": "P1",
            "tags": ["App", "网络", "异常恢复"],
            "content": "断网或模拟请求超时后执行关键操作，断言错误提示；恢复网络后可重新提交。",
            "template_json": {
                "name_pattern": "[网络异常] {page_name}",
                "steps": ["set_network_offline", "execute_action", "set_network_online", "retry_action"],
                "assertions": [{"type": "error_then_success"}],
            },
        },
    },
]


class KnowledgeSeedService:
    def __init__(self, repository: ResourceRepository) -> None:
        self.repository = repository

    def seed_defaults(self, project_id: int | None, overwrite: bool = False) -> dict[str, int]:
        rows, _ = self.repository.list("project_knowledge", None, None, 1, 10000)
        existing = {
            item.get("data", {}).get("knowledge_key"): item
            for item in rows
            if item.get("project_id") == project_id and item.get("data", {}).get("knowledge_key")
        }

        inserted = 0
        updated = 0
        skipped = 0
        for item in DEFAULT_KNOWLEDGE_ITEMS:
            payload = deepcopy(item)
            payload["project_id"] = project_id
            payload["status"] = "active"
            knowledge_key = payload["data"]["knowledge_key"]
            current = existing.get(knowledge_key)
            if current and overwrite:
                self.repository.update("project_knowledge", current["id"], payload)
                updated += 1
            elif current:
                skipped += 1
            else:
                self.repository.create("project_knowledge", payload)
                inserted += 1

        return {
            "inserted_count": inserted,
            "updated_count": updated,
            "skipped_count": skipped,
            "total_count": len(DEFAULT_KNOWLEDGE_ITEMS),
        }
