"""Default prompts for screenshot-driven Web feature and element discovery.

The text lives here so the discovery service works out of the box; seeded
prompt templates (same ``template_type``) override these defaults at runtime.
"""

VISION_FUNCTION_TEMPLATE_TYPE = "web_vision_function_discovery"
VISION_ELEMENT_TEMPLATE_TYPE = "web_vision_element_extraction"

DEFAULT_FUNCTION_DISCOVERY_PROMPT = """请观察这张 Web 系统页面截图，识别页面上可见的业务功能入口。

页面名称：{{page_name}}
页面地址：{{page_url}}

要求：
1. 只识别真实可见的功能入口，例如：查询、新增、编辑、删除、详情、导入、导出、审核等。
2. 每个功能给出入口的可见文案（按钮或链接上的文字），用于后续自动点击。
3. 删除、清空、禁用等会造成数据破坏的功能，risk 标记为 destructive，其余标记为 safe。
4. 如果页面上有“更多”类折叠菜单，且很可能藏有功能入口，在 warnings 中说明。
5. 不要识别浏览器自身控件、分页器、用户头像菜单等无关入口。

只输出合法 JSON，不要输出 Markdown：
{
  "features": [
    {"feature": "新增", "entry_hint": "新增", "risk": "safe"}
  ],
  "warnings": []
}

补充要求：{{user_prompt}}"""

DEFAULT_ELEMENT_EXTRACTION_PROMPT = """请观察传入的 Web 系统截图。每张截图展示一个功能打开后的弹窗、抽屉或页面区域，图片与功能标识会在下方列出。

页面名称：{{page_name}}

要求：
1. 分别提取每个功能区域内所有可操作元素：输入框、下拉框、日期选择、单选/复选框、按钮。
2. 每个元素给出：name（可见标签或占位文字）、element_type（input/select/multi_select/date/checkbox/radio/button/textarea）、action（fill/select/multi_select/click/check/uncheck）、description（元素位置或用途的一句话说明，供 AI 执行引擎定位）、required（是否必填）、default_value（安全的示例值，按钮留空）。
3. description 必须能让一个没见过页面的人找到元素，例如“弹窗顶部第一个输入框”、“表单底部左侧主按钮”。
4. 不要提取取消、关闭类按钮；不要提交任何表单。
5. default_value 使用安全的测试值，不要输出真实敏感数据。
6. 不要把不同图片、不同功能的元素混在一起。

批量输出格式会在调用时附加。只输出合法 JSON，不要输出 Markdown。

单个功能的元素结构示例：
{
  "elements": [
    {"name": "客户名称", "element_type": "input", "action": "fill", "description": "弹窗表单第一行输入框", "required": true, "default_value": "测试客户"}
  ]
}

补充要求：{{user_prompt}}"""
