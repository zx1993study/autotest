import type { ResourceColumn, ResourceField } from '../types/resource-schema'
import { descriptionField, statusField, statusOptions } from './shared'

export const aiModelFields: ResourceField[] = [
  { key: 'name', label: '模型名称', required: true, placeholder: '例如：OpenAI GPT-4.1 Mini' },
  {
    key: 'data.provider',
    label: '模型厂商',
    type: 'select',
    defaultValue: 'openai_compatible',
    options: [
      { label: 'OpenAI兼容', value: 'openai_compatible' },
      { label: 'OpenAI', value: 'openai' },
      { label: '通义千问', value: 'dashscope' },
      { label: 'DeepSeek', value: 'deepseek' },
      { label: '本地模型', value: 'local' }
    ]
  },
  { key: 'data.base_url', label: '接口地址', placeholder: '例如：https://api.openai.com/v1' },
  { key: 'data.model', label: '模型标识', required: true, placeholder: '例如：gpt-4.1-mini' },
  { key: 'data.api_key', label: 'API Key', placeholder: '仅新建或替换时填写，平台会保存到文件' },
  { key: 'data.api_key_file', label: '密钥文件名', placeholder: '自动生成，只保存文件名' },
  { key: 'data.is_current', label: '设为当前模型', type: 'checkbox', defaultValue: false },
  { key: 'data.temperature', label: '温度', type: 'number', defaultValue: 0.2 },
  { key: 'data.timeout_sec', label: '超时秒数', type: 'number', defaultValue: 60 },
  statusField,
  descriptionField
]

export const aiModelColumns: ResourceColumn[] = [
  { key: 'name', label: '模型名称' },
  { key: 'data.provider', label: '厂商' },
  { key: 'data.model', label: '模型' },
  { key: 'data.base_url', label: '接口地址' },
  { key: 'data.api_key_file', label: '密钥文件' },
  { key: 'data.is_current', label: '当前模型', width: '90px' },
  { key: 'status', label: '状态', width: '90px' }
]

export const aiPromptTemplateFields: ResourceField[] = [
  { key: 'name', label: '模板名称', required: true, placeholder: '例如：Web页面用例生成' },
  {
    key: 'data.template_type',
    label: '模板类型',
    type: 'select',
    defaultValue: 'web_case_generation',
    options: [
      { label: 'Web页面功能生成', value: 'web_page_generation' },
      { label: 'Web用例生成', value: 'web_case_generation' },
      { label: 'Web功能元素获取', value: 'web_function_element_generation' },
      { label: 'API用例生成', value: 'api_case_generation' },
      { label: '元素识别建议', value: 'element_generation' }
    ]
  },
  {
    key: 'data.system_prompt',
    label: '系统提示词',
    type: 'textarea',
    full: true,
    rows: 5,
    placeholder: '定义模型角色、输出格式和安全边界'
  },
  {
    key: 'data.user_template',
    label: '用户提示词模板',
    type: 'textarea',
    full: true,
    rows: 12,
    placeholder: '可使用 {{context_json}} 和 {{user_prompt}} 占位符'
  },
  {
    key: 'data.output_schema',
    label: '输出格式 JSON',
    type: 'json',
    full: true,
    rows: 8,
    defaultValue: {
      elements: [],
      cases: []
    }
  },
  statusField,
  descriptionField
]

export const aiPromptTemplateColumns: ResourceColumn[] = [
  { key: 'name', label: '模板名称' },
  { key: 'data.template_type', label: '模板类型' },
  { key: 'status', label: '状态', width: '90px' },
  { key: 'updated_at', label: '更新时间', width: '180px' }
]

export const aiGenerationTaskFields: ResourceField[] = [
  { key: 'name', label: '任务名称', required: true, placeholder: '例如：AI生成Web页面-外勤小星' },
  {
    key: 'data.task_type',
    label: '任务类型',
    type: 'select',
    defaultValue: 'web_page_generation',
    required: true,
    options: [
      { label: 'Web页面功能生成', value: 'web_page_generation' },
      { label: 'Web功能元素获取', value: 'web_function_element_generation' }
    ]
  },
  {
    key: 'project_id',
    label: '项目',
    type: 'select',
    required: true,
    placeholder: '请选择项目',
    remoteOptions: {
      path: '/projects/options',
      valueKey: 'id',
      labelKeys: ['name']
    }
  },
  {
    key: 'data.prompt_template_id',
    label: 'Prompt模板',
    type: 'select',
    placeholder: '不选择则使用默认模板',
    remoteOptions: {
      path: '/ai/prompt-templates/options',
      valueKey: 'id',
      labelKeys: ['name']
    }
  },
  {
    key: 'data.login_case_id',
    label: '页面登录用例',
    type: 'select',
    placeholder: '请选择功能为登录的Web正式用例',
    visibleWhen: { key: 'data.task_type', value: 'web_page_generation' },
    remoteOptions: {
      path: '/web-testing/cases/login-options',
      valueKey: 'id',
      labelKeys: ['name'],
      dependsOn: { project_id: 'project_id' }
    }
  },
  { key: 'status', label: '状态', type: 'select', defaultValue: 'queued', hidden: true, options: statusOptions },
  {
    key: 'data.scan_scope',
    label: '扫描方式',
    type: 'select',
    defaultValue: 'single',
    required: true,
    visibleWhen: { key: 'data.task_type', value: 'web_function_element_generation' },
    options: [
      { label: '单个页面', value: 'single' },
      { label: '多个页面', value: 'multiple' },
      { label: '所有页面', value: 'all' }
    ]
  },
  {
    key: 'data.page_id',
    label: '页面功能',
    type: 'select',
    required: true,
    placeholder: '请选择页面功能',
    visibleWhen: {
      all: [
        { key: 'data.task_type', value: 'web_function_element_generation' },
        { key: 'data.scan_scope', value: 'single' }
      ]
    },
    remoteOptions: {
      path: '/web-testing/pages/options',
      valueKey: 'id',
      labelKeys: ['name'],
      dependsOn: { project_id: 'project_id' }
    }
  },
  {
    key: 'data.page_ids',
    label: '页面功能',
    type: 'multiselect',
    required: true,
    placeholder: '请选择一个或多个页面功能',
    visibleWhen: {
      all: [
        { key: 'data.task_type', value: 'web_function_element_generation' },
        { key: 'data.scan_scope', value: 'multiple' }
      ]
    },
    remoteOptions: {
      path: '/web-testing/pages/options',
      valueKey: 'id',
      labelKeys: ['name'],
      dependsOn: { project_id: 'project_id' }
    }
  },
  {
    key: 'data.operation_timeout_sec',
    type: 'number',
    label: '单页自动扫描超时(秒)',
    defaultValue: 120,
    visibleWhen: { key: 'data.task_type', value: 'web_function_element_generation' }
  },
  {
    key: 'data.existing_element_strategy',
    label: '已有元素处理',
    type: 'select',
    defaultValue: 'update',
    visibleWhen: { key: 'data.task_type', value: 'web_function_element_generation' },
    options: [
      { label: '更新已有元素', value: 'update' },
      { label: '跳过保存', value: 'skip' }
    ]
  },
  {
    key: 'data.scan_instruction',
    label: '自动操作说明',
    type: 'textarea',
    rows: 5,
    full: true,
    visibleWhen: { key: 'data.task_type', value: 'web_function_element_generation' },
    defaultValue: '任务会在后台以无头模式加载带有页面鉴权信息的页面，由 AI 识别当前页面功能入口并操作。平台会自动点击入口、填写安全示例值、扫描弹窗或抽屉内元素并保存；删除类功能只打开确认区域后取消，不会提交真实删除。'
  },
  { key: 'data.discover_after_login', label: '登录后采集页面', type: 'checkbox', defaultValue: true, visibleWhen: { key: 'data.task_type', value: 'web_page_generation' } },
  { key: 'data.discovery_max_pages', label: '最多采集页面数', type: 'number', defaultValue: 30, visibleWhen: { key: 'data.task_type', value: 'web_page_generation' } },
  { key: 'data.discovery_timeout_ms', label: '单页超时(ms)', type: 'number', defaultValue: 15000, visibleWhen: { key: 'data.task_type', value: 'web_page_generation' } },
  { key: 'data.discovery_wait_ms', label: '渲染等待(ms)', type: 'number', defaultValue: 1000, visibleWhen: { key: 'data.task_type', value: 'web_page_generation' } },
  { key: 'data.discovery_headless', label: '无头采集', type: 'checkbox', defaultValue: true, visibleWhen: { key: 'data.task_type', value: 'web_page_generation' } },
  { key: 'data.include_existing_pages', label: '包含已有页面', type: 'checkbox', defaultValue: true, visibleWhen: { key: 'data.task_type', value: 'web_page_generation' } },
  { key: 'data.include_api_interfaces', label: '包含API接口', type: 'checkbox', defaultValue: true, visibleWhen: { key: 'data.task_type', value: 'web_page_generation' } },
  { key: 'data.include_knowledge', label: '包含知识库', type: 'checkbox', defaultValue: true, visibleWhen: { key: 'data.task_type', value: 'web_page_generation' } },
  { key: 'data.overwrite_existing', label: '覆盖已有页面', type: 'checkbox', defaultValue: false, visibleWhen: { key: 'data.task_type', value: 'web_page_generation' } },
  {
    key: 'data.user_prompt',
    label: '补充Prompt',
    type: 'textarea',
    rows: 4,
    full: true,
    defaultValue: '请先使用 Playwright 登录后的真实页面采集信息，结合页面截图、路由、页面文字、按钮入口和页面调用的 API，分析所有页面功能并保存到 Web 页面功能。同一路由下如果存在查询、新增、编辑、删除、详情、导入、导出等按钮或弹窗功能，请拆成多条页面功能记录，route/url 可以相同，但 name 和 feature_type 必须不同。'
  }
]

export const aiGenerationTaskColumns: ResourceColumn[] = [
  { key: 'name', label: '任务名称' },
  { key: 'project_id', label: '项目ID', width: '90px' },
  { key: 'data.task_type', label: '任务类型' },
  { key: 'data.result.saved_pages', label: '保存页面', width: '90px' },
  { key: 'data.result.skipped_pages', label: '跳过页面', width: '90px' },
  { key: 'status', label: '状态', width: '90px' },
  { key: 'updated_at', label: '更新时间', width: '180px' }
]

