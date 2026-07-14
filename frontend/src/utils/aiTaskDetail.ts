export interface RouteFeature {
  key: string
  name: string
  route: string
  url: string
  feature_type: string
  status: string
  description: string
}

export interface RouteItem {
  key: string
  label: string
  route: string
  url: string
  screenshot_url: string
  screenshot_file: string
  features: RouteFeature[]
}

export interface RouteGroup {
  key: string
  label: string
  children: RouteItem[]
}

export interface ScanOperationStep {
  key: string
  step_id: string
  element_name: string
  action: string
  value: string
  locator: string
  purpose: string
  matched: boolean | null
  executed: boolean | null
}

export interface ScanElementRow {
  key: string
  id: string
  name: string
  element_type: string
  action: string
  locator_type: string
  locator: string
  default_value: string
}

export interface ScanPageItem {
  key: string
  page_id: string
  page_name: string
  target_url: string
  screenshot_url: string
  screenshot_file: string
  screenshot_error: string
  element_count: number
  warnings: string[]
  operation_steps: ScanOperationStep[]
  executed_steps: Record<string, unknown>[]
  elements: ScanElementRow[]
  script_text: string
}

const DETAIL_SCRIPT_TEXT_LIMIT = 20_000

export function stringifyJson(value: unknown) {
  if (value == null || value === '') {
    return '-'
  }
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

export function truncateDetailText(value: unknown, limit: number) {
  const text = String(value ?? '')
  if (text.length <= limit) {
    return text
  }
  return `${text.slice(0, limit)}\n\n...内容过长，已截断前 ${limit} 个字符用于详情展示。`
}

export function formatStatus(status: unknown) {
  const map: Record<string, string> = {
    queued: '排队中',
    running: '执行中',
    success: '成功',
    partial_success: '部分成功',
    failed: '失败',
    inactive: '停用',
    active: '启用'
  }
  const key = String(status || '')
  return map[key] || key || '-'
}

export function statusClass(status: unknown) {
  const key = String(status || '')
  if (key === 'success') {
    return 'success'
  }
  if (key === 'partial_success') {
    return 'warning'
  }
  if (key === 'failed') {
    return 'danger'
  }
  if (key === 'running' || key === 'queued') {
    return 'info'
  }
  return ''
}

export function formatTaskType(type: unknown) {
  const map: Record<string, string> = {
    web_page_generation: 'Web 页面功能生成',
    web_case_generation: 'Web 用例生成'
  }
  const key = String(type || '')
  return map[key] || key || '-'
}

export function formatFeatureType(type: unknown) {
  const map: Record<string, string> = {
    page: '页面',
    query: '查询',
    add: '新增',
    edit: '编辑',
    delete: '删除',
    detail: '详情',
    import: '导入',
    export: '导出',
    login: '登录',
    audit: '审核',
    submit: '提交'
  }
  const key = String(type || '')
  return map[key] || key || '-'
}

export function formatAction(action: unknown) {
  const map: Record<string, string> = {
    click: '点击',
    fill: '输入',
    input: '输入',
    select: '下拉选择',
    check: '勾选',
    uncheck: '取消勾选',
    hover: '悬停',
    press: '按键'
  }
  const key = String(action || '')
  return map[key] || key || '-'
}

export function formatLocatorType(type: unknown) {
  const map: Record<string, string> = {
    role: '角色',
    css: 'CSS',
    xpath: 'XPath',
    text: '文本',
    placeholder: '占位符',
    label: '标签',
    testid: 'TestId'
  }
  const key = String(type || '')
  return map[key] || key || '-'
}

export function formatScanScope(scope: unknown) {
  const map: Record<string, string> = {
    single: '单个页面',
    multiple: '多个页面',
    all: '所有页面'
  }
  const key = String(scope || '')
  return map[key] || key || '-'
}

export function formatStepStatus(step: ScanOperationStep) {
  if (step.matched === false) {
    return '未匹配'
  }
  if (step.executed === false) {
    return '已跳过'
  }
  if (step.executed === true) {
    return '已执行'
  }
  if (step.matched === true) {
    return '已匹配'
  }
  return '计划'
}

export function stepStatusClass(step: ScanOperationStep) {
  if (step.matched === false) {
    return 'failed'
  }
  if (step.executed === false) {
    return 'queued'
  }
  if (step.executed === true || step.matched === true) {
    return 'success'
  }
  return 'info'
}

export function normalizeScanPage(page: Record<string, unknown>, index: number): ScanPageItem {
  const aiPlan = toRecord(page.ai_plan)
  const plannedSteps = arrayRecords(aiPlan.operation_steps)
  const executedSteps = arrayRecords(page.executed_ai_steps)
  const executedByStepId = new Map<string, Record<string, unknown>>()
  for (const executed of executedSteps) {
    const key = String(executed.step_id ?? '')
    if (key) {
      executedByStepId.set(key, executed)
    }
  }
  const operationSteps = plannedSteps.map((step, stepIndex) => normalizeScanOperationStep(step, executedByStepId, stepIndex))
  for (const executed of executedSteps) {
    const stepId = String(executed.step_id ?? '')
    if (stepId && operationSteps.some(step => step.step_id === stepId)) {
      continue
    }
    operationSteps.push(normalizeExecutedOnlyStep(executed, operationSteps.length))
  }
  const elements = arrayRecords(page.elements).map((element, elementIndex) => normalizeScanElement(element, elementIndex))
  return {
    key: String(page.page_id ?? `${page.page_name || 'page'}-${index}`),
    page_id: String(page.page_id ?? ''),
    page_name: String(page.page_name ?? '-'),
    target_url: String(page.target_url ?? ''),
    screenshot_url: String(page.screenshot_url ?? ''),
    screenshot_file: String(page.screenshot_file ?? ''),
    screenshot_error: String(page.screenshot_error ?? ''),
    element_count: Number(page.element_count ?? elements.length) || elements.length,
    warnings: arrayStrings(page.warnings),
    operation_steps: operationSteps,
    executed_steps: executedSteps,
    elements,
    script_text: truncateDetailText(page.script_text, DETAIL_SCRIPT_TEXT_LIMIT)
  }
}

export function normalizeScanOperationStep(
  step: Record<string, unknown>,
  executedByStepId: Map<string, Record<string, unknown>>,
  index: number,
): ScanOperationStep {
  const stepId = String(step.step_id ?? index + 1)
  const executed = executedByStepId.get(stepId) || {}
  return {
    key: `step-${stepId}-${index}`,
    step_id: stepId,
    element_name: String(executed.element_name ?? step.element_name ?? step.name ?? ''),
    action: String(executed.action ?? step.action ?? ''),
    value: String(executed.value ?? step.value ?? step.default_value ?? ''),
    locator: String(executed.locator ?? step.locator ?? ''),
    purpose: String(step.purpose ?? step.description ?? ''),
    matched: booleanOrNull(executed.matched),
    executed: booleanOrNull(executed.executed)
  }
}

export function normalizeExecutedOnlyStep(executed: Record<string, unknown>, index: number): ScanOperationStep {
  const stepId = String(executed.step_id ?? index + 1)
  return {
    key: `executed-${stepId}-${index}`,
    step_id: stepId,
    element_name: String(executed.element_name ?? ''),
    action: String(executed.action ?? ''),
    value: String(executed.value ?? ''),
    locator: String(executed.locator ?? ''),
    purpose: '',
    matched: booleanOrNull(executed.matched),
    executed: booleanOrNull(executed.executed)
  }
}

export function normalizeScanElement(element: Record<string, unknown>, index: number): ScanElementRow {
  const data = toRecord(element.data)
  return {
    key: String(element.id ?? `${element.name || 'element'}-${index}`),
    id: String(element.id ?? ''),
    name: String(element.name ?? ''),
    element_type: String(data.element_type ?? data.type ?? ''),
    action: String(data.action ?? ''),
    locator_type: String(data.locator_type ?? data.locator_method ?? ''),
    locator: String(data.locator ?? data.locator_args ?? ''),
    default_value: String(data.default_value ?? data.example ?? '')
  }
}

export function toRecord(value: unknown): Record<string, unknown> {
  return isRecord(value) ? value : {}
}

export function arrayRecords(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value) ? value.filter(isRecord) : []
}

export function arrayStrings(value: unknown): string[] {
  return Array.isArray(value) ? value.map(item => String(item)).filter(Boolean) : []
}

export function booleanOrNull(value: unknown): boolean | null {
  if (typeof value === 'boolean') {
    return value
  }
  return null
}

export function upsertRouteItem(target: Map<string, RouteItem>, raw: Record<string, unknown>) {
  const route = normalizeRoute(raw.route)
  const url = String(raw.url || '')
  const key = routeKey(route, url)
  if (!key) {
    return
  }
  const existing = target.get(key)
  const label = String(raw.name || raw.name_hint || raw.title || route || url)
  const screenshotUrl = String(raw.screenshot_url || '')
  const screenshotFile = String(raw.screenshot_file || '')
  if (!existing) {
    target.set(key, {
      key,
      label,
      route,
      url,
      screenshot_url: screenshotUrl,
      screenshot_file: screenshotFile,
      features: []
    })
    return
  }
  existing.label = existing.label || label
  existing.route = existing.route || route
  existing.url = existing.url || url
  existing.screenshot_url = existing.screenshot_url || screenshotUrl
  existing.screenshot_file = existing.screenshot_file || screenshotFile
}

export function normalizeRoute(value: unknown) {
  const text = String(value || '').trim()
  if (!text) {
    return ''
  }
  if (/^https?:\/\//i.test(text)) {
    try {
      const url = new URL(text)
      return `${url.pathname || '/'}${url.search || ''}`
    } catch {
      return text
    }
  }
  return text.startsWith('/') ? text : `/${text}`
}

export function routeKey(route: string, url: string) {
  return route || url
}

export function firstRouteSegment(route: string) {
  const normalized = normalizeRoute(route).split('?')[0]
  const segments = normalized.split('/').filter(Boolean)
  return segments.length ? `/${segments[0]}` : '/'
}

export function formatDurationMinutes(minutes: number) {
  if (!Number.isFinite(minutes) || minutes < 0) {
    return '-'
  }
  if (minutes > 0 && minutes < 0.01) {
    return '< 0.01 分'
  }
  return `${minutes.toFixed(2)} 分`
}

export function toFiniteNumber(value: unknown) {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value
  }
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

export function toTimestampMs(value: unknown) {
  const numeric = toFiniteNumber(value)
  if (numeric != null) {
    return numeric > 100000000000 ? numeric : numeric * 1000
  }
  if (typeof value !== 'string' || value.trim() === '') {
    return 0
  }
  const parsed = Date.parse(value)
  return Number.isFinite(parsed) ? parsed : 0
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}
