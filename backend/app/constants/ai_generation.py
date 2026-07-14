from __future__ import annotations

SENSITIVE_MARKERS = (
    "password",
    "passwd",
    "pwd",
    "token",
    "cookie",
    "authorization",
    "secret",
    "api_key",
    "apikey",
    "access_key",
)

AI_WEB_PAGE_API_BATCH_SIZE = 20
AI_WEB_PAGE_MAX_EXISTING_PAGES = 80
AI_WEB_PAGE_MAX_KNOWLEDGE = 30
AI_WEB_PAGE_MAX_CONSECUTIVE_ERRORS = 2
AI_TASK_RUNTIME_FIELDS = (
    "result",
    "progress",
    "batch_errors",
    "failed_batches",
    "current_batch",
    "batch_count",
    "finished_at",
    "duration_minutes",
    "discovery",
    "discovery_config",
    "error",
    "codegen_session_id",
    "codegen_browser_running",
)
AI_TASK_RESULT_SUMMARY_FIELDS = (
    "task_id",
    "task_type",
    "dry_run",
    "saved_pages",
    "skipped_pages",
    "updated_pages",
    "generated_pages",
    "batch_count",
    "success_batches",
    "failed_batches",
    "saved_elements",
    "created_elements",
    "updated_elements",
    "skipped_elements",
    "page_count",
    "success_pages",
    "failed_pages",
    "scan_scope",
    "batch_errors",
    "warnings",
    "error",
    "finished_at",
)
WEB_PAGE_FEATURE_TYPES = (
    "page",
    "login",
    "query",
    "add",
    "edit",
    "delete",
    "detail",
    "import",
    "export",
)
WEB_PAGE_FEATURE_TYPE_TEXT = "|".join(WEB_PAGE_FEATURE_TYPES)


DEFAULT_SYSTEM_PROMPT = """你是自动化测试平台的测试分析助手。
你只生成建议，不执行测试、不保存数据、不需要真实账号密码。
你必须输出合法 JSON，不要输出 Markdown。
不要输出真实密码、token、cookie。"""


DEFAULT_WEB_CASE_USER_TEMPLATE = """请根据以下脱敏后的 Web 页面上下文，生成页面元素建议和 Web 用例草稿。

要求：
1. 覆盖正常场景、异常场景、边界场景。
2. 每条用例都输出 steps，步骤字段使用 step_id、element_name、value、action、take_screenshot、skip。
3. take_screenshot 默认只有最后一步为 true，其他为 false。
4. 不要输出 Playwright 原始脚本。
5. 输出结构必须符合：
{
  "elements": [
    {
      "name": "元素名称",
      "element_type": "input|button|select|multi_select|checkbox|radio|link|text",
      "action": "fill|click|select|multi_select|check|uncheck|assert|wait",
      "locator_type": "role|css|xpath|text|testid",
      "locator": "定位表达式",
      "default_value": "安全示例值",
      "required": true
    }
  ],
  "cases": [
    {
      "name": "[正常流程] 登录页",
      "category": "normal|exception|boundary",
      "priority": "P1|P2|P3",
      "strategy_ids": [1],
      "steps": [
        {
          "step_id": 1,
          "element_name": "用户名",
          "value": "test_user",
          "action": "fill",
          "take_screenshot": false,
          "skip": false
        }
      ],
      "assertions": [
        {"type": "page_loaded", "expected": true}
      ]
    }
  ]
}

上下文：
{{context_json}}

补充需求：
{{user_prompt}}"""


DEFAULT_WEB_PAGE_USER_TEMPLATE = """请根据以下脱敏后的项目上下文，推导该 Web 项目应该维护的页面功能清单。

你只生成建议，平台负责校验、去重和保存。不要输出账号、密码、token、cookie。
必须只输出合法 JSON，不要输出 Markdown。

返回结构必须是：
{
  "pages": [
    {
      "name": "页面/功能名称",
      "route": "/customer/list",
      "url": "https://example.com/customer/list",
      "feature_type": "%s",
      "description": "页面功能说明",
      "module": "所属模块",
      "priority": "P1|P2|P3"
    }
  ]
}

生成原则：
1. 优先根据 discovered_web_pages 中真实登录后采集到的路由、截图、页面文字、可见按钮和页面 API 调用分析功能，不要只按接口路径猜。
2. 一个路由可以对应多个页面功能；同一路由下的查询、新增、编辑、删除、详情、导入、导出必须拆成多条记录。
3. 页面容器使用 feature_type=page；登录使用 login；按钮/弹窗/操作入口使用 query、add、edit、delete、detail、import、export。
4. 如果新增、编辑、删除、导入、导出在同一个列表页弹窗中完成，route 和 url 可以相同，但 name 和 feature_type 必须不同。
5. 如果截图/页面文字中出现“新增、编辑、删除、详情、导入、导出、查询、重置、提交、审核”等操作，请按操作拆分页面功能。
6. URL 可以根据项目 base_url + route 生成；不确定时也要给 route。
7. 不要生成重复功能。平台会按项目、路由、URL、功能类型和名称综合去重。

项目上下文：
{{context_json}}

补充需求：
{{user_prompt}}""" % WEB_PAGE_FEATURE_TYPE_TEXT


DEFAULT_WEB_FUNCTION_ELEMENT_USER_TEMPLATE = """You are helping an autotest platform operate one existing Web page function.
The platform loads the target URL in a headless browser, applies safe Web auth cookies, and collects visible controls.
Return valid JSON only. Do not return Markdown. Do not output passwords, tokens, cookies, or secrets.

Goal:
1. Read the page function context.
2. Decide the smallest safe operation path needed to enter or exercise this function.
3. For add/edit/query/import, prefer operation_steps that open the target modal/drawer/page, fill typical editable fields, select typical dropdown values, and then click save/query/confirm after all related controls are collected.
4. For delete, open the confirm dialog only and avoid real deletion; prefer cancel/close.
5. Treat readonly inputs, "请选择" placeholders, Element UI el-select, and Ant Design select controls as select elements; never return fill for them.
6. Ignore unrelated navigation, pagination, profile menus, and global layout controls.

Return schema:
{
  "recording_plan": [
    {"step_id": 1, "instruction": "Open add button", "expected": "Add modal is visible"}
  ],
  "operation_steps": [
    {
      "step_id": 1,
      "element_name": "Add",
      "action": "click",
      "value": "",
      "locator": "button, name=Add",
      "purpose": "Open add modal"
    }
  ],
  "element_steps": [
    {
      "step_id": 1,
      "element_name": "Name",
      "element_type": "input|button|select|multi_select|checkbox|radio|link|text",
      "action": "fill|click|select|multi_select|check|uncheck|assert|wait",
      "locator_type": "role|css|xpath|text|placeholder|testid",
      "locator": "stable locator",
      "default_value": "safe sample value",
      "container": "page|modal|drawer",
      "required": false,
      "take_screenshot": false,
      "skip": false
    }
  ],
  "warnings": []
}

Context:
{{context_json}}

Extra instruction:
{{user_prompt}}"""

