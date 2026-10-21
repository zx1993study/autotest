import type { ResourceColumn, ResourceField } from '../types/resource-schema'
import { caseTypeOptions, descriptionField, priorityOptions, projectColumns, projectSelectField, statusField } from './shared'

export const projectInfoFields: ResourceField[] = [
  { key: 'name', label: '项目名称', required: true, placeholder: '例如：外勤小星' },
  { key: 'data.code', label: '项目编码', placeholder: '例如：waiqin' },
  { key: 'data.owner', label: '负责人', placeholder: '项目负责人/测试负责人' },
  { key: 'data.base_url', label: '项目地址', required: true, placeholder: '例如：https://test.waiqin.yios.cn' },
  { key: 'data.miniapp_h5_url', label: '小程序 H5 地址', placeholder: '可选；小程序同源 H5 测试部署地址' },
  { key: 'data.default_env', label: '默认环境', placeholder: '例如：测试环境' },
  statusField,
  descriptionField
]

export const projectInfoColumns = projectColumns

export const projectAuthFields: ResourceField[] = [
  { key: 'name', label: '鉴权名称', required: true, placeholder: '例如：admin-web' },
  projectSelectField,
  {
    key: 'data.auth_type',
    label: '鉴权类型',
    type: 'select',
    required: true,
    defaultValue: 'bearer',
    options: [
      { label: 'Bearer Token', value: 'bearer' },
      { label: 'Cookie', value: 'cookie' },
      { label: 'API Key', value: 'api_key' },
      { label: 'Basic Auth', value: 'basic' }
    ]
  },
  {
    key: 'data.login_case_type',
    label: '登录用例类型',
    type: 'select',
    defaultValue: 'API',
    options: caseTypeOptions.filter(option => ['API', 'WEB'].includes(String(option.value)))
  },
  { key: 'data.login_case_id', label: '登录用例', type: 'number', full: true },
  { key: 'data.token_file', label: '鉴权文件名', placeholder: '例如 admin-web.json', visibleWhen: { key: 'data.auth_type', value: ['cookie', 'basic'] } },
  { key: 'data.token', label: 'Token 信息', full: true, visibleWhen: { key: 'data.auth_type', value: ['bearer', 'api_key'] } },
  { key: 'data.header_name', label: '请求头名称', placeholder: '例如：Authorization' },
  {
    key: 'data.refresh_strategy',
    label: '刷新策略',
    type: 'select',
    defaultValue: 'manual',
    options: [
      { label: '手动刷新', value: 'manual' },
      { label: '登录成功后刷新', value: 'on_login_success' },
      { label: '定时刷新', value: 'scheduled' }
    ]
  },
  statusField,
  descriptionField
]

export const projectAuthColumns: ResourceColumn[] = [
  { key: 'name', label: '鉴权名称' },
  { key: 'project_id', label: '项目 ID', width: '90px' },
  { key: 'data.auth_type', label: '类型' },
  { key: 'data.login_case_type', label: '用例类型' },
  { key: 'data.token_storage_label', label: '凭据存储' },
  { key: 'status', label: '状态', width: '90px' }
]

export const knowledgeFields: ResourceField[] = [
  { key: 'name', label: '原则名称', required: true, placeholder: '例如：边界测试' },
  { key: 'data.knowledge_key', label: '原则编码', required: true, placeholder: '例如：principle.boundary_testing' },
  {
    key: 'data.kind',
    label: '知识类型',
    type: 'select',
    defaultValue: 'test_principle',
    options: [
      { label: '测试原则', value: 'test_principle' }
    ]
  },
  {
    key: 'data.domain',
    label: '适用范围',
    type: 'select',
    defaultValue: 'COMMON',
    options: [
      { label: '通用', value: 'COMMON' },
      { label: 'Web', value: 'WEB' }
    ]
  },
  {
    key: 'data.category',
    label: '原则类型',
    type: 'select',
    defaultValue: 'boundary',
    options: [
      { label: '条件覆盖', value: 'condition' },
      { label: '边界测试', value: 'boundary' },
      { label: '异常测试', value: 'exception' },
      { label: '冒烟测试', value: 'smoke' },
      { label: '测试数据', value: 'data' },
      { label: '交互验证', value: 'interaction' }
    ]
  },
  { key: 'data.priority', label: '优先级', type: 'select', defaultValue: 'P2', options: priorityOptions },
  { key: 'data.tags', label: '标签', placeholder: '多个标签用逗号分隔' },
  { key: 'data.content', label: '原则内容', type: 'textarea', required: true, full: true, rows: 5 },
  { key: 'data.template_json', label: '场景模板 JSON', type: 'json', full: true, rows: 8, defaultValue: {} },
  statusField,
  descriptionField
]

export const knowledgeColumns: ResourceColumn[] = [
  { key: 'name', label: '原则名称' },
  { key: 'data.kind', label: '类型' },
  { key: 'data.knowledge_key', label: '编码' },
  { key: 'data.domain', label: '适用范围' },
  { key: 'data.category', label: '原则类型' },
  { key: 'data.priority', label: '优先级' },
  { key: 'status', label: '状态', width: '90px' }
]

export const appKnowledgeFields: ResourceField[] = [
  { key: 'name', label: '知识标题', required: true, placeholder: '例如：登录页账号输入失败经验' },
  projectSelectField,
  { key: 'data.knowledge_key', label: '知识编码', required: true, placeholder: '例如：app.login.input_rule' },
  {
    key: 'data.kind',
    label: '知识类型',
    type: 'select',
    defaultValue: 'app_failure_lesson',
    options: [
      { label: '失败经验', value: 'app_failure_lesson' },
      { label: '定位策略', value: 'locator_strategy' },
      { label: '弹窗处理', value: 'popup_handling' },
      { label: '等待策略', value: 'wait_strategy' },
      { label: '输入规则', value: 'input_rule' },
      { label: '业务规则', value: 'business_rule' },
      { label: '设备特征', value: 'device_trait' }
    ]
  },
  {
    key: 'data.domain',
    label: '适用范围',
    type: 'select',
    defaultValue: 'APP',
    options: [{ label: 'App', value: 'APP' }]
  },
  {
    key: 'data.category',
    label: '分类',
    type: 'select',
    defaultValue: 'failure',
    options: [
      { label: '失败修复', value: 'failure' },
      { label: '元素定位', value: 'locator' },
      { label: '弹窗处理', value: 'popup' },
      { label: '等待同步', value: 'wait' },
      { label: '输入数据', value: 'input' },
      { label: '设备连接', value: 'device' },
      { label: '业务流程', value: 'business' }
    ]
  },
  { key: 'data.priority', label: '优先级', type: 'select', defaultValue: 'P2', options: priorityOptions },
  {
    key: 'data.platform',
    label: '平台',
    type: 'select',
    defaultValue: 'COMMON',
    options: [
      { label: '通用', value: 'COMMON' },
      { label: 'Android', value: 'Android' },
      { label: 'iOS', value: 'iOS' }
    ]
  },
  { key: 'data.feature_id', label: '关联功能 ID', type: 'number', placeholder: '可选' },
  { key: 'data.device_id', label: '关联设备 ID', type: 'number', placeholder: '可选' },
  { key: 'data.trigger_signature', label: '触发特征', placeholder: '例如：登录失败、元素找不到、WDA 连接超时' },
  { key: 'data.content', label: '知识内容', type: 'textarea', required: true, full: true, rows: 5 },
  { key: 'data.repair_strategy', label: '修复策略', type: 'textarea', full: true, rows: 4 },
  { key: 'data.locator_strategy', label: '定位策略', type: 'textarea', full: true, rows: 4 },
  { key: 'data.tags', label: '标签', placeholder: '多个标签用逗号分隔' },
  { key: 'data.template_json', label: '脚本模板 JSON', type: 'json', full: true, rows: 8, defaultValue: {} },
  statusField,
  descriptionField
]

export const appKnowledgeColumns: ResourceColumn[] = [
  { key: 'name', label: '知识标题' },
  { key: 'project_id', label: '项目 ID', width: '90px' },
  { key: 'data.kind', label: '类型' },
  { key: 'data.knowledge_key', label: '编码' },
  { key: 'data.category', label: '分类' },
  { key: 'data.priority', label: '优先级', width: '90px' },
  { key: 'data.platform', label: '平台', width: '90px' },
  { key: 'status', label: '状态', width: '90px' }
]

