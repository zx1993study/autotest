import type { ResourceColumn, ResourceField } from '../types/resource-schema'
import { descriptionField, pageFeatureTypeOptions, projectIdField, statusField, webAuthSelectField } from './shared'

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

