import type { ResourceColumn, ResourceField } from '../types/resource-schema'
import { apiInterfaceSelectField, apiSourceInterfaceField, authSelectField, caseCategoryOptions, caseStatusOptions, caseTypeOptions, descriptionField, priorityOptions, projectIdField, statusField } from './shared'

export const apiInterfaceFields: ResourceField[] = [
  { key: 'name', label: '接口名称', required: true, placeholder: '例如：用户登录' },
  projectIdField,
  {
    key: 'data.method',
    label: '请求方法',
    type: 'select',
    required: true,
    defaultValue: 'GET',
    options: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'].map(value => ({ label: value, value }))
  },
  { key: 'data.path', label: '接口路径', required: true, placeholder: '例如：/api/login' },
  { key: 'data.module', label: '所属模块', placeholder: '例如：登录模块' },
  authSelectField,
  { key: 'data.content_type', label: '内容类型', placeholder: 'application/json' },
  { key: 'data.original_url', label: '导入原始 URL', placeholder: '可选，调试优先使用项目环境地址' },
  statusField,
  descriptionField
]

export const apiInterfaceColumns: ResourceColumn[] = [
  { key: 'data.method', label: '方法', width: '90px' },
  { key: 'data.path', label: '路径' },
  { key: 'name', label: '接口名称' },
  { key: 'data.module', label: '模块' },
  { key: 'status', label: '状态', width: '90px' }
]

export const apiFieldFields: ResourceField[] = [
  { key: 'name', label: '字段名称', required: true },
  projectIdField,
  apiInterfaceSelectField,
  {
    key: 'data.location',
    label: '参数位置',
    type: 'select',
    required: true,
    defaultValue: 'body',
    options: ['query', 'header', 'body', 'path', 'cookie'].map(value => ({ label: value, value }))
  },
  {
    key: 'data.field_type',
    label: '字段类型',
    type: 'select',
    defaultValue: 'string',
    options: ['string', 'number', 'integer', 'boolean', 'object', 'array'].map(value => ({ label: value, value }))
  },
  { key: 'data.required', label: '是否必填', type: 'checkbox', defaultValue: false },
  { key: 'data.example', label: '示例值', placeholder: '用于调试和生成用例' },
  { key: 'data.default_value', label: '默认值' },
  { key: 'data.rule', label: '校验/生成规则', type: 'textarea', full: true, rows: 3 },
  statusField,
  descriptionField
]

export const apiFieldColumns: ResourceColumn[] = [
  { key: 'name', label: '字段名称' },
  { key: 'data.interface_id', label: '接口 ID', width: '90px' },
  { key: 'data.location', label: '位置' },
  { key: 'data.field_type', label: '类型' },
  { key: 'data.required', label: '必填', width: '80px' },
  { key: 'data.example', label: '示例值' }
]

export const caseDraftFields: ResourceField[] = [
  { key: 'name', label: '用例名称', required: true },
  projectIdField,
  { key: 'source_id', label: '来源 ID', type: 'number' },
  { key: 'data.category', label: '覆盖类型', type: 'select', defaultValue: 'normal', options: caseCategoryOptions },
  { key: 'data.priority', label: '优先级', type: 'select', defaultValue: 'P2', options: priorityOptions },
  { key: 'case_json', label: '草稿 JSON', type: 'json', full: true, rows: 10, defaultValue: {} },
  { key: 'assertions', label: '断言 JSON', type: 'json', full: true, rows: 6, defaultValue: [] },
  { key: 'strategy_ids', label: '策略 ID JSON', type: 'json', full: true, rows: 3, defaultValue: [] },
  { key: 'review_comment', label: '审核意见', type: 'textarea', full: true, rows: 3 },
  { key: 'status', label: '状态', type: 'select', defaultValue: 'draft', options: caseStatusOptions },
  descriptionField
]

export const apiCaseDraftFields: ResourceField[] = [
  { key: 'name', label: '用例名称', required: true },
  projectIdField,
  apiSourceInterfaceField,
  { key: 'data.category', label: '覆盖类型', type: 'select', defaultValue: 'normal', options: caseCategoryOptions },
  { key: 'data.priority', label: '优先级', type: 'select', defaultValue: 'P2', options: priorityOptions },
  { key: 'case_json', label: '草稿 JSON', type: 'json', full: true, rows: 10, defaultValue: {} },
  { key: 'assertions', label: '断言 JSON', type: 'json', full: true, rows: 6, defaultValue: [] },
  { key: 'strategy_ids', label: '策略 ID JSON', type: 'json', full: true, rows: 3, defaultValue: [] },
  { key: 'review_comment', label: '审核意见', type: 'textarea', full: true, rows: 3 },
  { key: 'status', label: '状态', type: 'select', defaultValue: 'draft', options: caseStatusOptions },
  descriptionField
]

export const caseDraftColumns: ResourceColumn[] = [
  { key: 'name', label: '用例名称' },
  { key: 'source_id', label: '来源 ID', width: '90px' },
  { key: 'data.category', label: '覆盖类型' },
  { key: 'data.priority', label: '优先级' },
  { key: 'strategy_ids', label: '策略 ID' },
  { key: 'status', label: '状态', width: '90px' },
  { key: 'updated_at', label: '更新时间', width: '180px' }
]

export const testCaseFields: ResourceField[] = [
  { key: 'name', label: '用例名称', required: true },
  projectIdField,
  { key: 'source_id', label: '来源 ID', type: 'number' },
  { key: 'data.case_type', label: '用例类型', type: 'select', options: caseTypeOptions },
  { key: 'data.priority', label: '优先级', type: 'select', defaultValue: 'P2', options: priorityOptions },
  { key: 'steps', label: '执行步骤 JSON', type: 'json', full: true, rows: 10, defaultValue: [] },
  { key: 'assertions', label: '断言 JSON', type: 'json', full: true, rows: 6, defaultValue: [] },
  { key: 'data.variables', label: '变量 JSON', type: 'json', full: true, rows: 5, defaultValue: {} },
  statusField,
  descriptionField
]

export const apiTestCaseFields: ResourceField[] = [
  { key: 'name', label: '用例名称', required: true },
  projectIdField,
  apiSourceInterfaceField,
  { key: 'data.case_type', label: '用例类型', type: 'select', options: caseTypeOptions },
  { key: 'data.priority', label: '优先级', type: 'select', defaultValue: 'P2', options: priorityOptions },
  { key: 'steps', label: '执行步骤 JSON', type: 'json', full: true, rows: 10, defaultValue: [] },
  { key: 'assertions', label: '断言 JSON', type: 'json', full: true, rows: 6, defaultValue: [] },
  { key: 'data.variables', label: '变量 JSON', type: 'json', full: true, rows: 5, defaultValue: {} },
  statusField,
  descriptionField
]

export const testCaseColumns: ResourceColumn[] = [
  { key: 'name', label: '用例名称' },
  { key: 'source_id', label: '来源 ID', width: '90px' },
  { key: 'data.case_type', label: '类型' },
  { key: 'data.priority', label: '优先级' },
  { key: 'status', label: '状态', width: '90px' },
  { key: 'updated_at', label: '更新时间', width: '180px' }
]

export const apiTestCaseColumns: ResourceColumn[] = [
  { key: 'name', label: '用例名称' },
  { key: 'data.project_name', label: '项目名称', width: '140px' },
  { key: 'data.api_method', label: 'API 方法', width: '100px' },
  { key: 'data.api_path', label: 'API 路径' },
  { key: 'data.case_type', label: '类型', width: '80px' },
  { key: 'data.priority', label: '优先级', width: '90px' },
  { key: 'status', label: '状态', width: '90px' },
  { key: 'updated_at', label: '更新时间', width: '180px' }
]

