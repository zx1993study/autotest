import type { ResourceColumn, ResourceField } from '../types/resource-schema'
import { descriptionField, pageFeatureTypeOptions, projectIdField, statusField, webAuthSelectField, webElementTypeOptions } from './shared'

export const webPageFields: ResourceField[] = [
  { key: 'name', label: '页面/功能名称', required: true, placeholder: '例如：登录页/新增客户' },
  projectIdField,
  { key: 'data.route', label: '页面路由', placeholder: '例如：/login 或 /customer/add' },
  { key: 'data.url', label: '页面地址', required: true, placeholder: '完整地址或相对路径' },
  {
    key: 'data.feature_type',
    label: '功能类型',
    type: 'select',
    defaultValue: 'page',
    options: pageFeatureTypeOptions
  },
  webAuthSelectField,
  statusField,
  descriptionField
]

export const webPageColumns: ResourceColumn[] = [
  { key: 'name', label: '页面/功能名称' },
  { key: 'data.route', label: '路由' },
  { key: 'data.url', label: '页面地址' },
  { key: 'data.feature_type', label: '功能类型' },
  { key: 'status', label: '状态', width: '90px' }
]

export const webElementFields: ResourceField[] = [
  { key: 'name', label: '元素名称', required: true },
  projectIdField,
  { key: 'data.page_id', label: '页面 ID', type: 'number', required: true },
  {
    key: 'data.element_type',
    label: '元素类型',
    type: 'select',
    defaultValue: 'input',
    options: webElementTypeOptions
  },
  {
    key: 'data.action',
    label: '默认交互',
    type: 'select',
    defaultValue: 'click',
    options: ['click', 'fill', 'select', 'multi_select', 'check', 'uncheck', 'assert', 'hover', 'wait'].map(value => ({ label: value, value }))
  },
  {
    key: 'data.locator_type',
    label: '定位方式',
    type: 'select',
    defaultValue: 'css',
    options: ['css', 'xpath', 'text', 'role', 'testid'].map(value => ({ label: value, value }))
  },
  { key: 'data.locator', label: '定位表达式', required: true, full: true },
  { key: 'data.required', label: '是否必填', type: 'checkbox', defaultValue: false },
  { key: 'data.default_value', label: '默认值' },
  { key: 'data.example', label: '输入示例' },
  statusField,
  descriptionField
]

export const webElementColumns: ResourceColumn[] = [
  { key: 'id', label: '元素 ID', width: '90px' },
  { key: 'name', label: '元素名称' },
  { key: 'data.page_name', label: '页面功能名称', width: '160px' },
  { key: 'data.page_id', label: '页面 ID', width: '90px' },
  { key: 'data.element_type', label: '类型' },
  { key: 'data.action', label: '交互' },
  { key: 'data.default_value', label: '默认值' },
  { key: 'data.locator', label: '定位' },
  { key: 'status', label: '状态', width: '90px' }
]

