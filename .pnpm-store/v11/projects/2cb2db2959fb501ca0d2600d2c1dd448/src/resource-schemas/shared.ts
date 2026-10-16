import type { ResourceColumn, ResourceField, ResourceOption } from '../types/resource-schema'
import {
  caseDraftStatusOptions as caseStatusOptions,
  caseTypeOptions,
  executionPlanTestTypeOptions,
  resourceStatusOptions as statusOptions
} from '../constants/enums'

export const priorityOptions: ResourceOption[] = [
  { label: 'P0 阻塞', value: 'P0' },
  { label: 'P1 重要', value: 'P1' },
  { label: 'P2 普通', value: 'P2' },
  { label: 'P3 低', value: 'P3' }
]

export const caseCategoryOptions: ResourceOption[] = [
  { label: '正常流程', value: 'normal' },
  { label: '异常场景', value: 'exception' },
  { label: '边界场景', value: 'boundary' }
]

export const pageFeatureTypeOptions: ResourceOption[] = [
  { label: '页面', value: 'page' },
  { label: '登录', value: 'login' },
  { label: '查询', value: 'query' },
  { label: '新增', value: 'add' },
  { label: '编辑', value: 'edit' },
  { label: '删除', value: 'delete' },
  { label: '详情', value: 'detail' },
  { label: '导入', value: 'import' },
  { label: '导出', value: 'export' }
]

export const appElementTypeOptions: ResourceOption[] = [
  { label: '输入框', value: 'input' },
  { label: '按钮', value: 'button' },
  { label: '下拉框', value: 'select' },
  { label: '列表', value: 'list' },
  { label: '弹窗', value: 'dialog' },
  { label: '文本', value: 'text' },
  { label: '开关', value: 'switch' },
  { label: '系统控件', value: 'system' }
]

export const appPlatformOptions: ResourceOption[] = [
  { label: 'Android', value: 'Android' },
  { label: 'iOS', value: 'iOS' }
]

export const appDeviceFormFactorOptions: ResourceOption[] = [
  { label: '手机', value: 'phone' },
  { label: '平板', value: 'tablet' }
]

export const appTargetOptions: ResourceOption[] = [
  { label: 'Android 手机', value: 'android_phone' },
  { label: 'Android 平板', value: 'android_tablet' },
  { label: 'iPhone', value: 'ios_phone' },
  { label: 'iPad', value: 'ios_tablet' }
]

export const appDeviceConnectionStatusOptions: ResourceOption[] = [
  { label: '在线', value: 'online' },
  { label: '离线', value: 'offline' },
  { label: '占用', value: 'busy' },
  { label: '未知', value: 'unknown' }
]

export const appEntryTypeOptions: ResourceOption[] = [
  { label: '已安装 App', value: 'installed_app' },
  { label: '当前前台 App', value: 'current_app' },
  { label: '小程序宿主 App', value: 'miniapp_host' }
]

export const projectIdField: ResourceField = {
  key: 'project_id',
  label: '关联项目',
  type: 'select',
  required: true,
  placeholder: '请选择关联项目',
  remoteOptions: {
    path: '/projects/options',
    valueKey: 'id',
    labelKeys: ['name']
  }
}

export const projectSelectField: ResourceField = projectIdField

export const apiInterfaceSelectField: ResourceField = {
  key: 'data.interface_id',
  label: '所属接口',
  type: 'select',
  required: true,
  placeholder: '请选择所属接口',
  remoteOptions: {
    path: '/api-testing/interfaces/options',
    valueKey: 'id',
    labelKeys: ['method', 'path', 'name']
  }
}

export const apiSourceInterfaceField: ResourceField = {
  key: 'source_id',
  label: '来源接口',
  type: 'select',
  placeholder: '请选择来源接口',
  remoteOptions: {
    path: '/api-testing/interfaces/options',
    valueKey: 'id',
    labelKeys: ['method', 'path', 'name']
  }
}

export const authSelectField: ResourceField = {
  key: 'data.auth_id',
  label: '鉴权信息',
  type: 'select',
  placeholder: '请选择 API 鉴权信息',
  remoteOptions: {
    path: '/project-auth/options',
    valueKey: 'id',
    labelKeys: ['name'],
    params: { login_case_type: 'API' }
  }
}

export const webAuthSelectField: ResourceField = {
  key: 'data.auth_id',
  label: '鉴权信息',
  type: 'select',
  placeholder: '请选择 Web 鉴权信息',
  remoteOptions: {
    path: '/project-auth/options',
    valueKey: 'id',
    labelKeys: ['name'],
    params: { login_case_type: 'WEB' }
  }
}

export const descriptionField: ResourceField = {
  key: 'description',
  label: '说明',
  type: 'textarea',
  full: true,
  rows: 3
}

export const statusField: ResourceField = {
  key: 'status',
  label: '状态',
  type: 'select',
  defaultValue: 'active',
  options: statusOptions
}

export const baseColumns: ResourceColumn[] = [
  { key: 'name', label: '名称' },
  { key: 'status', label: '状态', width: '96px' },
  { key: 'updated_at', label: '更新时间', width: '180px' }
]

export const projectColumns: ResourceColumn[] = [
  { key: 'name', label: '项目名称' },
  { key: 'data.code', label: '项目编码' },
  { key: 'data.is_default', label: '默认项目', width: '90px' },
  { key: 'data.owner', label: '负责人' },
  { key: 'data.base_url', label: '项目地址' },
  { key: 'data.default_env', label: '默认环境' },
  { key: 'status', label: '状态', width: '90px' }
]

export { caseStatusOptions, caseTypeOptions, executionPlanTestTypeOptions, statusOptions }

