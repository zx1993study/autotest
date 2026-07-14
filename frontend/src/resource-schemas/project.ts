import type { ResourceColumn, ResourceField } from '../types/resource-schema'
import { caseTypeOptions, descriptionField, priorityOptions, projectColumns, projectSelectField, statusField } from './shared'

export const projectInfoFields: ResourceField[] = [
  { key: 'name', label: '项目名称', required: true, placeholder: '例如：外勤小星' },
  { key: 'data.code', label: '项目编码', placeholder: '例如：waiqin' },
  { key: 'data.owner', label: '负责人', placeholder: '项目负责人/测试负责人' },
  { key: 'data.base_url', label: '项目地址', required: true, placeholder: '例如：https://test.waiqin.yios.cn' },
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
    defaultValue: 'WEB',
    options: caseTypeOptions
  },
  { key: 'data.login_case_id', label: '登录用例 ID', type: 'number' },
  { key: 'data.token_file', label: '鉴权文件名', placeholder: '只保存文件名，例如 auth/admin-web.json' },
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
  { key: 'data.token_file', label: '鉴权文件' },
  { key: 'status', label: '状态', width: '90px' }
]

export const knowledgeFields: ResourceField[] = [
  { key: 'name', label: '知识名称', required: true, placeholder: '例如：手机号边界规则' },
  { key: 'data.knowledge_key', label: '策略/模板编码', required: true, placeholder: '例如：template.api.required_missing' },
  {
    key: 'data.kind',
    label: '知识类型',
    type: 'select',
    defaultValue: 'case_template',
    options: [
      { label: '测试设计策略', value: 'design_strategy' },
      { label: '通用用例模板', value: 'case_template' }
    ]
  },
  {
    key: 'data.domain',
    label: '适用范围',
    type: 'select',
    defaultValue: 'COMMON',
    options: [
      { label: '通用', value: 'COMMON' },
      { label: 'API', value: 'API' },
      { label: 'Web', value: 'WEB' },
      { label: 'App', value: 'APP' }
    ]
  },
  {
    key: 'data.category',
    label: '策略类型',
    type: 'select',
    defaultValue: 'boundary',
    options: [
      { label: '边界测试', value: 'boundary' },
      { label: '异常测试', value: 'exception' },
      { label: '正常测试', value: 'normal' },
      { label: '流程测试', value: 'flow' },
      { label: '安全权限', value: 'security' },
      { label: '断言规则', value: 'assertion' },
      { label: '测试数据', value: 'data' }
    ]
  },
  { key: 'data.priority', label: '优先级', type: 'select', defaultValue: 'P2', options: priorityOptions },
  { key: 'data.tags', label: '标签', placeholder: '多个标签用逗号分隔' },
  { key: 'data.content', label: '知识内容', type: 'textarea', required: true, full: true, rows: 5 },
  { key: 'data.template_json', label: '策略/模板 JSON', type: 'json', full: true, rows: 8, defaultValue: {} },
  statusField,
  descriptionField
]

export const knowledgeColumns: ResourceColumn[] = [
  { key: 'name', label: '知识名称' },
  { key: 'data.kind', label: '类型' },
  { key: 'data.knowledge_key', label: '编码' },
  { key: 'data.domain', label: '适用范围' },
  { key: 'data.category', label: '策略类型' },
  { key: 'data.priority', label: '优先级' },
  { key: 'status', label: '状态', width: '90px' }
]

