import type { ResourceColumn, ResourceField } from '../types/resource-schema'
import {
  appDeviceConnectionStatusOptions,
  appDeviceFormFactorOptions,
  appElementTypeOptions,
  appEntryTypeOptions,
  appPlatformOptions,
  descriptionField,
  pageFeatureTypeOptions,
  projectIdField,
  statusField
} from './shared'

const appLocatorTypeOptions = [
  'resource_id',
  'accessibility_id',
  'text',
  'xpath',
  'android_uiautomator',
  'ios_predicate',
  'ios_class_chain',
  'class_name'
].map(value => ({ label: value, value }))

const appActionOptions = [
  'tap',
  'input',
  'clear',
  'select',
  'assert',
  'assert_text',
  'swipe',
  'back',
  'wait',
  'press_key',
  'hide_keyboard',
  'switch_context',
  'launch_app',
  'terminate_app'
].map(value => ({ label: value, value }))

const optionalProjectIdField: ResourceField = {
  ...projectIdField,
  required: false,
  placeholder: '可选；不选则作为通用设备'
}

export const appDeviceFields: ResourceField[] = [
  { key: 'name', label: '设备名称', required: true, placeholder: '扫描设备时自动填充；也可手动命名' },
  optionalProjectIdField,
  { key: 'data.platform', label: '平台', type: 'select', required: true, defaultValue: 'Android', options: appPlatformOptions },
  { key: 'data.device_form_factor', label: '设备类型', type: 'select', required: true, defaultValue: 'phone', options: appDeviceFormFactorOptions },
  { key: 'data.udid', label: '设备 UDID', placeholder: '自动识别时填充；手动添加时建议填写' },
  { key: 'data.node_key', label: '执行节点', type: 'select', remoteOptions: { path: '/agent/nodes/options', labelKeys: ['name'], valueKey: 'data.node_key' } },
  { key: 'data.device_name', label: '系统识别名', placeholder: '例如：Pixel 8 / iPhone 15' },
  { key: 'data.platform_version', label: '系统版本', placeholder: '例如：14 / 17.0' },
  { key: 'data.product_type', label: '设备型号', placeholder: '例如：iPhone17,1 / iPad8,10', visibleWhen: { key: 'data.platform', value: 'iOS' } },
  { key: 'data.appium_server_url', label: 'Appium Server', placeholder: '默认：http://127.0.0.1:4723' },
  { key: 'data.automation_name', label: 'AutomationName', placeholder: 'Android 默认 UiAutomator2，iOS 默认 XCUITest' },
  { key: 'data.system_port', label: 'Android systemPort', type: 'number' },
  { key: 'data.wda_local_port', label: 'iOS wdaLocalPort', type: 'number' },
  { key: 'data.wda_url', label: 'iOS WDA URL', placeholder: '例如：http://127.0.0.1:8200', visibleWhen: { key: 'data.platform', value: 'iOS' } },
  { key: 'data.wda_bundle_id', label: 'iOS WDA BundleId', placeholder: '默认：com.yios.wda.xctrunner', visibleWhen: { key: 'data.platform', value: 'iOS' } },
  { key: 'data.wda_bind_ip', label: 'iOS WDA 监听地址', placeholder: '默认：0.0.0.0，用于开放 WiFi 8100', visibleWhen: { key: 'data.platform', value: 'iOS' } },
  { key: 'data.wda_port', label: 'iOS WDA 代理端口', type: 'number', visibleWhen: { key: 'data.platform', value: 'iOS' } },
  { key: 'data.wda_remote_port', label: 'iOS WDA 设备端口', type: 'number', defaultValue: 8100, visibleWhen: { key: 'data.platform', value: 'iOS' } },
  { key: 'data.use_preinstalled_wda', label: '使用已安装 WDA', type: 'checkbox', defaultValue: true, visibleWhen: { key: 'data.platform', value: 'iOS' } },
  { key: 'data.use_new_wda', label: '启动时重装 WDA', type: 'checkbox', defaultValue: false, visibleWhen: { key: 'data.platform', value: 'iOS' } },
  { key: 'data.wda_status', label: 'iOS WDA 状态', placeholder: '检测后自动更新', visibleWhen: { key: 'data.platform', value: 'iOS' } },
  { key: 'data.chrome_driver_port', label: 'Chromedriver 端口', type: 'number' },
  { key: 'data.connection_status', label: '连接状态', type: 'select', defaultValue: 'unknown', options: appDeviceConnectionStatusOptions },
  { key: 'data.tags', label: '设备标签', placeholder: '例如：本机,冒烟,回归' },
  { key: 'data.capabilities', label: '设备 Capabilities JSON', type: 'json', full: true, rows: 5, defaultValue: {} },
  statusField,
  descriptionField
]

export const appDeviceColumns: ResourceColumn[] = [
  { key: 'name', label: '设备名称' },
  { key: 'data.platform', label: '平台', width: '90px' },
  { key: 'data.device_form_factor', label: '类型', width: '90px' },
  { key: 'data.platform_version', label: '系统', width: '90px' },
  { key: 'data.udid', label: 'UDID' },
  { key: 'data.source', label: '来源', width: '100px' },
  { key: 'data.connection_status', label: '连接', width: '90px' },
  { key: 'data.wda_status', label: 'WDA', width: '90px' },
  { key: 'status', label: '状态', width: '90px' }
]

export const appEntryFields: ResourceField[] = [
  { key: 'name', label: '应用入口名称', required: true, placeholder: '例如：进销存 App / 微信小程序入口' },
  projectIdField,
  { key: 'data.entry_type', label: '入口类型', type: 'select', required: true, defaultValue: 'installed_app', options: appEntryTypeOptions },
  { key: 'data.platform', label: '平台', type: 'select', defaultValue: 'Android', options: appPlatformOptions },
  { key: 'data.package_name', label: 'Android 包名', placeholder: '例如：com.example.app', visibleWhen: { key: 'data.platform', value: 'Android' } },
  { key: 'data.activity', label: 'Android Activity', placeholder: '例如：.MainActivity', visibleWhen: { key: 'data.platform', value: 'Android' } },
  { key: 'data.bundle_id', label: 'iOS BundleId', placeholder: '例如：com.example.ios', visibleWhen: { key: 'data.platform', value: 'iOS' } },
  { key: 'data.host_app', label: '小程序宿主', placeholder: '微信 / 企业微信 / 支付宝 / 自定义', visibleWhen: { key: 'data.entry_type', value: 'miniapp_host' } },
  { key: 'data.miniapp_name', label: '小程序名称', visibleWhen: { key: 'data.entry_type', value: 'miniapp_host' } },
  { key: 'data.miniapp_entry_mode', label: '小程序进入方式', placeholder: '手动已打开 / 搜索 / scheme / 扫码', visibleWhen: { key: 'data.entry_type', value: 'miniapp_host' } },
  { key: 'data.context_keyword', label: 'Context 关键字', placeholder: '例如 WEBVIEW 或小程序名称', visibleWhen: { key: 'data.entry_type', value: 'miniapp_host' } },
  { key: 'data.auto_webview', label: '自动切换 WebView', type: 'checkbox', defaultValue: false, visibleWhen: { key: 'data.entry_type', value: 'miniapp_host' } },
  { key: 'data.no_reset', label: '不重置应用', type: 'checkbox', defaultValue: true },
  { key: 'data.capabilities', label: '入口 Capabilities JSON', type: 'json', full: true, rows: 5, defaultValue: {} },
  statusField,
  descriptionField
]

export const appEntryColumns: ResourceColumn[] = [
  { key: 'name', label: '入口名称' },
  { key: 'data.entry_type', label: '入口类型' },
  { key: 'data.platform', label: '平台', width: '90px' },
  { key: 'data.package_name', label: '包名' },
  { key: 'data.bundle_id', label: 'BundleId' },
  { key: 'data.miniapp_name', label: '小程序' },
  { key: 'status', label: '状态', width: '90px' }
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
  { key: 'data.platform', label: '平台', type: 'select', defaultValue: 'Android', options: appPlatformOptions },
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
    options: appActionOptions
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
