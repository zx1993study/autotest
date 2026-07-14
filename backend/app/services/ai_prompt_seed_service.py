from __future__ import annotations

from typing import Any

from app.repositories.interfaces import ResourceRepository
from app.services.ai_generation_service import (
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_WEB_CASE_USER_TEMPLATE,
    DEFAULT_WEB_PAGE_USER_TEMPLATE,
)

DEFAULT_WEB_FUNCTION_ELEMENT_USER_TEMPLATE = """请根据以下脱敏后的 Web 页面功能上下文，生成“后台自动操作并解析元素步骤”的操作建议。
你只负责生成建议，平台负责在后台无头模式加载页面、加载鉴权、自动操作、解析和保存。不要输出真实密码、token、cookie，不要输出 Markdown，只输出合法 JSON。

目标流程：
1. 在 AI 生成任务中选择任务类型“Web功能元素获取”、扫描方式和目标页面功能。
2. 后台使用 Playwright 自动进入对应页面；如果页面功能绑定了 Web 鉴权信息，进入页面前应加载对应 cookie。
3. 根据页面功能类型执行最小闭环操作：
   - login：输入账号、密码，点击登录，并等待登录成功。
   - query：填写查询条件，记录所有查询条件元素和按钮，最后点击查询按钮。
   - add：点击新增入口，等待弹窗/抽屉/新页面出现，填写必填项和典型字段，记录所有功能元素，最后点击保存/确定按钮。
   - edit：进入编辑入口，等待弹窗/抽屉/新页面出现，修改可编辑字段，记录所有功能元素，最后点击保存/确定按钮。
   - delete：点击删除入口，记录确认弹窗元素；不要真实删除业务数据，优先点击取消。
   - detail：进入详情入口，记录关键只读文本或断言元素。
   - import/export：记录上传/导入/导出入口、文件选择、确认按钮和结果提示，导入类功能最后点击确认按钮。
4. 操作完成后，后台将自动生成的 Playwright 脚本交给平台解析器。
5. 解析时只保存和当前功能直接相关的元素步骤，忽略菜单导航、分页器、无关搜索框和无关按钮。

解析与保存规则：
1. 同一个元素既有 click 又有 fill/input 时，只保存输入操作。
2. get_by_role 定位方式保存为 role；定位内容只保存括号中的核心信息，例如 get_by_role("button", name="登 录") 保存为 locator_type=role，locator=button, name="登 录"。
3. 下拉框先点击展开再点击选项时，只保存下拉框元素；选项文本保存到 default_value。
4. 多选下拉需要再次点击才关闭时，element_type 使用 multi_select，action 使用 multi_select。
5. readonly input、placeholder 为“请选择...”的输入框、Element UI el-select、Ant Design select 必须按下拉框保存，禁止保存为 fill 输入框。
6. 日期弹窗按输入框保存，日期值保存到 default_value。
7. 弹窗/抽屉中的元素需要标记 container=modal/drawer，并保留步骤顺序。
8. 最后一个有效步骤 take_screenshot=true，其余默认 false；skip 默认 false。

返回结构必须是：
{
  "recording_plan": [
    {
      "step_id": 1,
      "instruction": "后台无头打开目标页面并加载鉴权",
      "expected": "进入目标页面并识别当前功能入口"
    }
  ],
  "operation_steps": [
    {
      "step_id": 1,
      "element_name": "新增按钮",
      "action": "click",
      "value": "",
      "purpose": "打开新增弹窗"
    }
  ],
  "element_steps": [
    {
      "step_id": 1,
      "element_name": "新增按钮",
      "element_type": "button",
      "action": "click",
      "locator_type": "role",
      "locator": "button, name=\"新增\"",
      "default_value": "",
      "container": "page",
      "required": false,
      "take_screenshot": false,
      "skip": false
    }
  ],
  "save_rules": [
    "解析脚本后保存到 Web 元素库，并同步生成页面功能步骤 JSON"
  ],
  "warnings": []
}

页面功能上下文：
{{context_json}}

补充需求：
{{user_prompt}}"""


DEFAULT_AI_PROMPTS: list[dict[str, Any]] = [
    {
        "name": "Web页面用例生成默认模板",
        "status": "active",
        "description": "根据脱敏页面上下文、元素库和用例策略生成元素建议与Web用例草稿。",
        "data": {
            "template_type": "web_case_generation",
            "template_key": "default.web_case_generation",
            "system_prompt": DEFAULT_SYSTEM_PROMPT,
            "user_template": DEFAULT_WEB_CASE_USER_TEMPLATE,
            "output_schema": {
                "elements": [
                    {
                        "name": "元素名称",
                        "element_type": "input",
                        "action": "fill",
                        "locator_type": "role",
                        "locator": 'textbox, name="用户名"',
                        "default_value": "test_user",
                        "required": True,
                    }
                ],
                "cases": [
                    {
                        "name": "[正常流程] 登录页",
                        "category": "normal",
                        "priority": "P1",
                        "strategy_ids": [],
                        "steps": [
                            {
                                "step_id": 1,
                                "element_name": "用户名",
                                "value": "test_user",
                                "action": "fill",
                                "take_screenshot": False,
                                "skip": False,
                            }
                        ],
                        "assertions": [{"type": "page_loaded", "expected": True}],
                    }
                ],
            },
        },
    },
    {
        "name": "Web页面功能生成默认模板",
        "status": "active",
        "description": "根据项目地址、已有页面、API路径和用例知识库生成Web页面功能清单。",
        "data": {
            "template_type": "web_page_generation",
            "template_key": "default.web_page_generation",
            "system_prompt": DEFAULT_SYSTEM_PROMPT,
            "user_template": DEFAULT_WEB_PAGE_USER_TEMPLATE,
            "output_schema": {
                "pages": [
                    {
                        "name": "新增客户",
                        "route": "/customer",
                        "url": "https://example.test/customer",
                        "feature_type": "add",
                        "description": "客户列表页中的新增客户弹窗或入口",
                    }
                ]
            },
        },
    },
    {
        "name": "Web功能元素获取默认模板",
        "status": "active",
        "description": "指导后台使用无头 Playwright 自动操作目标页面功能，并解析保存 Web 元素步骤。",
        "data": {
            "template_type": "web_function_element_generation",
            "template_key": "default.web_function_element_generation",
            "system_prompt": DEFAULT_SYSTEM_PROMPT,
            "user_template": DEFAULT_WEB_FUNCTION_ELEMENT_USER_TEMPLATE,
            "output_schema": {
                "recording_plan": [
                    {
                        "step_id": 1,
                        "instruction": "后台无头打开目标页面并加载鉴权",
                        "expected": "进入目标页面并识别当前功能入口",
                    }
                ],
                "operation_steps": [
                    {
                        "step_id": 1,
                        "element_name": "新增按钮",
                        "action": "click",
                        "value": "",
                        "purpose": "打开新增弹窗",
                    }
                ],
                "element_steps": [
                    {
                        "step_id": 1,
                        "element_name": "新增按钮",
                        "element_type": "button",
                        "action": "click",
                        "locator_type": "role",
                        "locator": 'button, name="新增"',
                        "default_value": "",
                        "container": "page",
                        "required": False,
                        "take_screenshot": False,
                        "skip": False,
                    }
                ],
                "save_rules": ["解析脚本后保存到 Web 元素库，并同步生成页面功能步骤 JSON"],
                "warnings": [],
            },
        },
    },
]


class AiPromptSeedService:
    def __init__(self, repository: ResourceRepository) -> None:
        self.repository = repository

    def seed_defaults(self, overwrite: bool = False) -> dict[str, int]:
        rows, _ = self.repository.list("ai_prompt_templates", page_size=10000)
        existing = {
            item.get("data", {}).get("template_key"): item
            for item in rows
            if item.get("data", {}).get("template_key")
        }
        created = 0
        updated = 0
        for payload in DEFAULT_AI_PROMPTS:
            template_key = payload["data"]["template_key"]
            current = existing.get(template_key)
            should_refresh_default = current and template_key in {
                "default.web_page_generation",
                "default.web_function_element_generation",
            }
            if current and (overwrite or should_refresh_default):
                self.repository.update("ai_prompt_templates", current["id"], payload)
                updated += 1
            elif not current:
                self.repository.create("ai_prompt_templates", payload)
                created += 1
        return {"created_count": created, "updated_count": updated}
