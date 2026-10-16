from __future__ import annotations

from typing import Any

from app.repositories.interfaces import ResourceRepository
from app.services.ai_generation_service import (
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_WEB_CASE_USER_TEMPLATE,
    DEFAULT_WEB_PAGE_USER_TEMPLATE,
)
from app.utils.web_vision_prompts import (
    DEFAULT_ELEMENT_EXTRACTION_PROMPT,
    DEFAULT_FUNCTION_DISCOVERY_PROMPT,
    VISION_ELEMENT_TEMPLATE_TYPE,
    VISION_FUNCTION_TEMPLATE_TYPE,
)

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
]

DEFAULT_AI_PROMPTS.append(
    {
        "name": "Web视觉功能发现默认模板",
        "status": "active",
        "description": "根据页面截图识别页面上的业务功能入口，输出功能清单 JSON。",
        "data": {
            "template_type": VISION_FUNCTION_TEMPLATE_TYPE,
            "template_key": f"default.{VISION_FUNCTION_TEMPLATE_TYPE}",
            "system_prompt": DEFAULT_SYSTEM_PROMPT,
            "user_template": DEFAULT_FUNCTION_DISCOVERY_PROMPT,
            "output_schema": {
                "features": [
                    {"feature": "新增", "entry_hint": "新增", "risk": "safe"}
                ],
                "warnings": [],
            },
        },
    }
)

DEFAULT_AI_PROMPTS.append(
    {
        "name": "Web视觉元素提取默认模板",
        "status": "active",
        "description": "批量分析多个功能截图，并按功能提取可操作元素的执行信息。",
        "data": {
            "template_type": VISION_ELEMENT_TEMPLATE_TYPE,
            "template_key": f"default.{VISION_ELEMENT_TEMPLATE_TYPE}",
            "system_prompt": DEFAULT_SYSTEM_PROMPT,
            "user_template": DEFAULT_ELEMENT_EXTRACTION_PROMPT,
            "output_schema": {
                "features": [
                    {
                        "feature_id": "feature_1",
                        "feature": "新增",
                        "elements": [
                            {
                                "name": "客户名称",
                                "element_type": "input",
                                "action": "fill",
                                "description": "弹窗表单第一行输入框",
                                "required": True,
                                "default_value": "测试客户",
                            }
                        ],
                    }
                ]
            },
        },
    }
)


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
            }
            changed = current and any(current.get(key) != value for key, value in payload.items())
            if current and (overwrite or (should_refresh_default and changed)):
                self.repository.update("ai_prompt_templates", current["id"], payload)
                updated += 1
            elif not current:
                self.repository.create("ai_prompt_templates", payload)
                created += 1
        return {"created_count": created, "updated_count": updated}
