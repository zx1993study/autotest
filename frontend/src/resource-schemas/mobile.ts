import type { ResourceColumn, ResourceField } from '../types/resource-schema'
import { appElementTypeOptions, descriptionField, pageFeatureTypeOptions, projectIdField, statusField } from './shared'

export const appPageFields: ResourceField[] = [
  { key: 'name', label: 'App 页面/功能名称', required: true },
  projectIdField,
  {
    key: 'data.platform',
    label: '平台',
    type: 'select',
    defaultValue: 'Android',
    options: [
      { label: 'Android', value: 'Android' },
      { label: 'iOS', value: 'iOS' }
    ]
  },
  { key: 'data.appium_server_url', label: 'Appium Server', placeholder: '例如：http://127.0.0.1:4723' },
  { key: 'data.udid', label: '设备 UDID', placeholder: 'Android/iOS 设备唯一标识' },
  { key: 'data.device_name', label: '设备名称', placeholder: '例如：emulator-5554 / iPhone 15' },
  { key: 'data.platform_version', label: '系统版本', placeholder: '例如：14 / 17.0' },
  { key: 'data.automation_name', label: 'AutomationName', placeholder: 'Android 默认 UiAutomator2，iOS 默认 XCUITest' },
  { key: 'data.package_name', label: '包名', placeholder: 'Android package / iOS bundleId' },
  { key: 'data.bundle_id', label: 'iOS BundleId', placeholder: 'iOS 应用 bundleId' },
  { key: 'data.activity', label: 'Activity/页面标识' },
  { key: 'data.no_reset', label: '不重置应用', type: 'checkbox', defaultValue: true },
  { key: 'data.implicit_wait_sec', label: '隐式等待(秒)', type: 'number', defaultValue: 10 },
  { key: 'data.step_wait_ms', label: '步骤等待(ms)', type: 'number', defaultValue: 0 },
  { key: 'data.capabilities', label: '扩展 Capabilities JSON', type: 'json', full: true, rows: 5, defaultValue: {} },
  { key: 'data.route', label: '页面路由/页面名' },
  {
    key: 'data.feature_type',
    label: '功能类型',
    type: 'select',
    defaultValue: 'page',
    options: pageFeatureTypeOptions
  },
  statusField,
  descriptionField
]

export const appPageColumns: ResourceColumn[] = [
  { key: 'name', label: '页面/功能名称' },
  { key: 'data.platform', label: '平台' },
  { key: 'data.package_name', label: '包名' },
  { key: 'data.activity', label: '页面标识' },
  { key: 'status', label: '状态', width: '90px' }
]

export const appElementFields: ResourceField[] = [
  { key: 'name', label: 'App 元素名称', required: true },
  projectIdField,
  { key: 'data.page_id', label: '页面 ID', type: 'number', required: true },
  { key: 'data.platform', label: '平台', type: 'select', defaultValue: 'Android', options: [{ label: 'Android', value: 'Android' }, { label: 'iOS', value: 'iOS' }] },
  {
    key: 'data.element_type',
    label: '元素类型',
    type: 'select',
    defaultValue: 'input',
    options: appElementTypeOptions
  },
  {
    key: 'data.locator_type',
    label: '定位方式',
    type: 'select',
    defaultValue: 'resource_id',
    options: ['resource_id', 'accessibility_id', 'text', 'xpath', 'android_uiautomator', 'ios_predicate', 'ios_class_chain', 'class_name'].map(value => ({ label: value, value }))
  },
  { key: 'data.locator', label: '定位表达式', full: true },
  { key: 'data.resource_id', label: 'resource-id' },
  { key: 'data.text', label: 'text' },
  { key: 'data.content_desc', label: 'content-desc' },
  { key: 'data.xpath', label: 'XPath', full: true },
  {
    key: 'data.action',
    label: '默认交互',
    type: 'select',
    defaultValue: 'tap',
    options: ['tap', 'input', 'select', 'assert', 'swipe', 'wait'].map(value => ({ label: value, value }))
  },
  { key: 'data.required', label: '是否必填', type: 'checkbox', defaultValue: false },
  { key: 'data.default_value', label: '默认值' },
  { key: 'data.example', label: '输入示例' },
  { key: 'data.take_screenshot', label: '执行后截图', type: 'checkbox', defaultValue: false },
  statusField,
  descriptionField
]

export const appElementColumns: ResourceColumn[] = [
  { key: 'name', label: '元素名称' },
  { key: 'data.page_id', label: '页面 ID', width: '90px' },
  { key: 'data.platform', label: '平台' },
  { key: 'data.element_type', label: '类型' },
  { key: 'data.resource_id', label: 'resource-id' },
  { key: 'data.locator_type', label: '定位方式' },
  { key: 'data.action', label: '交互' }
]

export const miniappPageFields: ResourceField[] = [
  { key: 'name', label: '小程序页面/功能名称', required: true },
  projectIdField,
  {
    key: 'data.host_app',
    label: '宿主应用',
    type: 'select',
    defaultValue: 'wechat',
    options: [
      { label: '微信', value: 'wechat' },
      { label: '企业微信', value: 'wecom' },
      { label: '支付宝', value: 'alipay' },
      { label: '自定义', value: 'custom' }
    ]
  },
  { key: 'data.miniapp_name', label: '小程序名称', placeholder: '用于匹配 WebView context' },
  { key: 'data.appium_server_url', label: 'Appium Server', placeholder: '例如：http://127.0.0.1:4723' },
  { key: 'data.platform', label: '平台', type: 'select', defaultValue: 'Android', options: [{ label: 'Android', value: 'Android' }, { label: 'iOS', value: 'iOS' }] },
  { key: 'data.udid', label: '设备 UDID' },
  { key: 'data.device_name', label: '设备名称' },
  { key: 'data.platform_version', label: '系统版本' },
  { key: 'data.package_name', label: '宿主包名', placeholder: '微信：com.tencent.mm' },
  { key: 'data.activity', label: '宿主 Activity', placeholder: '微信：.ui.LauncherUI' },
  { key: 'data.bundle_id', label: 'iOS BundleId' },
  { key: 'data.context', label: 'WebView Context', placeholder: '可选，例如 WEBVIEW_com.tencent.mm' },
  { key: 'data.context_keyword', label: 'Context 关键字', placeholder: '可选，优先用小程序名称匹配' },
  { key: 'data.auto_webview', label: '自动进入 WebView', type: 'checkbox', defaultValue: false },
  { key: 'data.chrome_driver_port', label: 'Chromedriver 端口', type: 'number' },
  { key: 'data.system_port', label: 'System Port', type: 'number' },
  { key: 'data.chrome_driver_executable', label: 'Chromedriver 路径', full: true },
  { key: 'data.route', label: '页面路径/路由', placeholder: '例如 pages/index/index' },
  {
    key: 'data.feature_type',
    label: '功能类型',
    type: 'select',
    defaultValue: 'page',
    options: pageFeatureTypeOptions
  },
  { key: 'data.capabilities', label: '扩展 Capabilities JSON', type: 'json', full: true, rows: 5, defaultValue: {} },
  { key: 'data.chrome_options', label: 'ChromeOptions JSON', type: 'json', full: true, rows: 4, defaultValue: {} },
  { key: 'data.implicit_wait_sec', label: '隐式等待(秒)', type: 'number', defaultValue: 10 },
  { key: 'data.step_wait_ms', label: '步骤等待(ms)', type: 'number', defaultValue: 0 },
  statusField,
  descriptionField
]

export const miniappPageColumns: ResourceColumn[] = [
  { key: 'name', label: '页面/功能名称' },
  { key: 'data.host_app', label: '宿主应用' },
  { key: 'data.miniapp_name', label: '小程序名称' },
  { key: 'data.route', label: '页面路径' },
  { key: 'data.context', label: 'Context' },
  { key: 'status', label: '状态', width: '90px' }
]

export const miniappElementFields: ResourceField[] = [
  { key: 'name', label: '小程序元素名称', required: true },
  projectIdField,
  { key: 'data.page_id', label: '页面 ID', type: 'number', required: true },
  {
    key: 'data.element_type',
    label: '元素类型',
    type: 'select',
    defaultValue: 'input',
    options: appElementTypeOptions
  },
  {
    key: 'data.locator_type',
    label: '定位方式',
    type: 'select',
    defaultValue: 'css',
    options: ['css', 'xpath', 'text', 'resource_id', 'accessibility_id', 'android_uiautomator', 'ios_predicate', 'ios_class_chain'].map(value => ({ label: value, value }))
  },
  { key: 'data.locator', label: '定位表达式', full: true },
  { key: 'data.css', label: 'CSS 选择器', full: true },
  { key: 'data.resource_id', label: 'resource-id' },
  { key: 'data.text', label: 'text' },
  { key: 'data.content_desc', label: 'content-desc' },
  { key: 'data.xpath', label: 'XPath', full: true },
  {
    key: 'data.action',
    label: '默认交互',
    type: 'select',
    defaultValue: 'tap',
    options: ['tap', 'input', 'select', 'assert', 'swipe', 'wait'].map(value => ({ label: value, value }))
  },
  { key: 'data.required', label: '是否必填', type: 'checkbox', defaultValue: false },
  { key: 'data.default_value', label: '默认值' },
  { key: 'data.example', label: '输入示例' },
  { key: 'data.take_screenshot', label: '执行后截图', type: 'checkbox', defaultValue: false },
  statusField,
  descriptionField
]

export const miniappElementColumns: ResourceColumn[] = [
  { key: 'name', label: '元素名称' },
  { key: 'data.page_id', label: '页面 ID', width: '90px' },
  { key: 'data.element_type', label: '类型' },
  { key: 'data.locator_type', label: '定位方式' },
  { key: 'data.css', label: 'CSS' },
  { key: 'data.locator', label: '定位' },
  { key: 'data.action', label: '交互' }
]

