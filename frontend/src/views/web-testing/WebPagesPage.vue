<template>
  <ResourcePage
    ref="resourcePageRef"
    title="Web 页面功能"
    description="按项目、路由、页面和功能维护 Web 测试资产，支持页面扫描和 Playwright 录制脚本解析。"
    api-path="/web-testing/pages"
    :row-actions="rowActions"
    :fields="webPageFields"
    :columns="webPageColumns"
    :initial-params="pageSearchParams"
    @custom-action="handleCustomAction"
  >
    <template #search-before-button>
      <select v-model="featureTypeFilter" class="feature-type-filter" aria-label="功能类型查询">
        <option value="">全部功能类型</option>
        <option v-for="option in pageFeatureTypeOptions" :key="String(option.value)" :value="option.value">
          {{ option.label }}
        </option>
      </select>
    </template>
  </ResourcePage>

  <div v-if="caseVisible" class="modal-backdrop" @click.self="closeCaseDialog">
    <section class="modal-panel case-modal" role="dialog" aria-modal="true">
      <header class="modal-header">
        <h3>生成 Web 用例</h3>
        <button class="modal-close" type="button" aria-label="关闭" @click="closeCaseDialog">×</button>
      </header>

      <form class="modal-form" @submit.prevent="saveCaseDraft">
        <div v-if="selectedCasePage" class="result-panel">
          <h4>{{ selectedCasePage.name }}</h4>
          <div class="result-grid">
            <span>页面 ID</span>
            <strong>{{ selectedCasePage.id }}</strong>
            <span>页面地址</span>
            <strong>{{ selectedCasePage.data.url || '-' }}</strong>
            <span>元素数量</span>
            <strong>{{ pageElements.length }} 个</strong>
          </div>
        </div>

        <WebCaseStepEditor :steps="normalSteps" @update:steps="handleNormalStepsUpdate" />

        <section class="strategy-panel">
          <div class="strategy-header">
            <strong>用例策略</strong>
            <small>可多选，用于生成正常、异常、边界等 Web 用例草稿</small>
          </div>
          <div class="strategy-list">
            <label v-for="strategy in strategies" :key="strategy.id" class="strategy-item">
              <input v-model="selectedStrategyIds" type="checkbox" :value="strategy.id" />
              <span>
                <b>{{ strategy.name }}</b>
                <small>{{ strategy.data.category || strategy.data.knowledge_key || '通用策略' }}</small>
              </span>
            </label>
          </div>
          <p v-if="!strategies.length" class="muted-text">暂无策略，请先在用例知识库新增策略。</p>
        </section>

        <p v-if="caseError" class="form-error">{{ caseError }}</p>

        <footer class="modal-actions">
          <button type="button" @click="closeCaseDialog">取消</button>
          <button type="submit" :disabled="caseSaving">{{ caseSaving ? '保存中...' : '保存到用例草稿' }}</button>
        </footer>
      </form>
    </section>
  </div>

  <WebPageParseDialog
    :visible="parseVisible"
    :selected-page="selectedPage"
    :parse-form="parseForm"
    :parse-result="parseResult"
    :parse-error="parseError"
    :parsing="parsing"
    :codegen-running="codegenRunning"
    :codegen-message="codegenMessage"
    @close="closeParseDialog"
    @submit="submitParse"
    @file-change="handleFileChange"
    @start-codegen="startCodegen"
  />
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  batchCreateResources,
  getWebCodegenStatus,
  listResources,
  parseWebScript,
  ResourceItem,
  startWebCodegen,
  stopWebCodegen,
  WebScriptParseResult
} from '../../api/http'
import ResourcePage from '../../components/ResourcePage.vue'
import WebCaseStepEditor from '../../components/resource/WebCaseStepEditor.vue'
import WebPageParseDialog from '../../components/resource/WebPageParseDialog.vue'
import { pageFeatureTypeOptions, webPageColumns, webPageFields } from '../../resourceSchemas'
import type { PageAction } from '../../types/page-actions'
import type { WebPageParseForm } from '../../types/web-page-parse'

const resourcePageRef = ref<{ load: () => Promise<void> } | null>(null)
const featureTypeFilter = ref('')
const pageSearchParams = computed(() => (
  featureTypeFilter.value ? { feature_type: featureTypeFilter.value } : {}
))
const selectedPage = ref<ResourceItem | null>(null)
const selectedCasePage = ref<ResourceItem | null>(null)
const caseVisible = ref(false)
const caseSaving = ref(false)
const caseError = ref('')
const caseJsonText = ref('')
const pageElements = ref<ResourceItem[]>([])
const normalSteps = ref<Record<string, unknown>[]>([])
const strategies = ref<ResourceItem[]>([])
const selectedStrategyIds = ref<number[]>([])
const RESOURCE_FETCH_PAGE_SIZE = 200
const parseVisible = ref(false)
const parsing = ref(false)
const parseError = ref('')
const parseResult = ref<WebScriptParseResult | null>(null)
const codegenRunning = ref(false)
const codegenMessage = ref('')
let codegenTimer: number | null = null
let activeCodegenSessionId = ''
let codegenPollBusy = false
const parseForm = ref<WebPageParseForm>({
  sourceType: 'codegen',
  existingElementStrategy: 'update',
  scriptText: '',
  file: null as File | null
})

const rowActions: PageAction[] = [
  {
    label: '元素',
    path: '/web/elements',
    type: 'route',
    payload: {
      page_id: '$id',
      project_id: '$project_id'
    }
  },
  {
    label: '用例',
    path: '',
    type: 'custom',
    name: 'case-generate'
  },
  {
    label: '解析',
    path: '',
    type: 'custom',
    name: 'parse-playwright'
  }
]

async function handleCustomAction(action: PageAction, item?: ResourceItem) {
  if (action.name === 'case-generate' && item) {
    await openCaseDialog(item)
    return
  }
  if (action.name === 'parse-playwright' && item) {
    openParseDialog(item)
  }
}

async function openCaseDialog(item: ResourceItem) {
  selectedCasePage.value = item
  caseError.value = ''
  caseJsonText.value = ''
  pageElements.value = []
  normalSteps.value = []
  strategies.value = []
  selectedStrategyIds.value = []
  caseVisible.value = true
  try {
    const [elements, strategyItems] = await Promise.all([
      listAllResourceItems('/web-testing/elements', {
        project_id: item.project_id,
        page_id: item.id
      }),
      listAllResourceItems('/project-knowledge')
    ])
    pageElements.value = elements
    normalSteps.value = buildNormalSteps(elements)
    strategies.value = strategyItems.filter(isWebStrategy)
    selectedStrategyIds.value = strategies.value
      .filter(strategy => strategy.data.domain === 'WEB' || strategy.data.domain === 'COMMON')
      .slice(0, 3)
      .map(strategy => strategy.id)
    caseJsonText.value = JSON.stringify(buildCaseDraftJson(item, normalSteps.value), null, 2)
  } catch (error) {
    caseError.value = getErrorMessage(error)
  }
}

async function listAllResourceItems(path: string, params: Record<string, unknown> = {}) {
  const firstPage = await listResources(path, {
    ...params,
    page: 1,
    pageSize: RESOURCE_FETCH_PAGE_SIZE
  })
  const items = [...firstPage.items]
  const totalPages = Math.ceil(firstPage.total / firstPage.pageSize)
  for (let page = 2; page <= totalPages; page += 1) {
    const nextPage = await listResources(path, {
      ...params,
      page,
      pageSize: RESOURCE_FETCH_PAGE_SIZE
    })
    items.push(...nextPage.items)
  }
  return items
}

function closeCaseDialog() {
  if (caseSaving.value) {
    return
  }
  caseVisible.value = false
  caseError.value = ''
}

async function saveCaseDraft() {
  caseError.value = ''
  if (!selectedCasePage.value) {
    caseError.value = '请选择页面功能'
    return
  }
  syncCaseJsonFromSteps()
  let caseJson: Record<string, unknown>
  try {
    caseJson = JSON.parse(caseJsonText.value) as Record<string, unknown>
  } catch {
    caseError.value = '用例草稿数据异常，请重新打开用例弹窗生成'
    return
  }
  const page = selectedCasePage.value
  const drafts = buildDrafts(page, caseJson)
  caseSaving.value = true
  try {
    const payloads = drafts.map(draft => {
      const assertions = caseAssertions(draft)
      const strategyIds = caseStrategyIds(draft)
      const cleanDraft = withoutCaseMeta(draft)
      return {
        name: String(cleanDraft.name || `[正常流程] ${page.name}`),
        project_id: page.project_id,
        source_id: page.id,
        status: 'draft',
        case_json: cleanDraft,
        data: cleanDraft,
        assertions,
        strategy_ids: strategyIds
      }
    })
    await batchCreateResources('/web-testing/case-drafts', payloads)
    caseVisible.value = false
  } catch (error) {
    caseError.value = getErrorMessage(error)
  } finally {
    caseSaving.value = false
  }
}

function buildNormalSteps(elements: ResourceItem[]) {
  const steps = [...elements].sort(compareElementsById).map((element, index) => {
    const data = element.data || {}
    const elementType = String(data.element_type || data.type || 'button')
    const action = String(data.action || defaultAction(elementType))
    return {
      步骤标识: index + 1,
      element_id: element.id,
      元素名称: element.name,
      元素值: defaultStepValue(data, action, element.name),
      交互类型: action,
      是否截图: false,
      是否跳过: false
    }
  })
  return initializeStepFlags(steps)
}

function initializeStepFlags(steps: Record<string, unknown>[]) {
  const sorted = normalizeCaseSteps(steps)
  sorted.forEach(step => {
    step['是否截图'] = false
  })
  if (sorted.length) {
    sorted[sorted.length - 1]['是否截图'] = true
  }
  return sorted
}

function normalizeCaseSteps(steps: Record<string, unknown>[]) {
  const sorted = [...steps].sort(compareCaseSteps)
  sorted.forEach(step => {
    if (!('是否截图' in step)) {
      step['是否截图'] = false
    }
    if (!('是否跳过' in step)) {
      step['是否跳过'] = false
    }
  })
  return sorted
}

function reindexCaseSteps(steps: Record<string, unknown>[]) {
  return steps.map((step, index) => {
    const order = index + 1
    const nextStep = { ...step }
    if (Object.prototype.hasOwnProperty.call(nextStep, '步骤标识') || !hasStepOrderField(nextStep)) {
      nextStep['步骤标识'] = order
    }
    nextStep.sort_order = order
    if (Object.prototype.hasOwnProperty.call(nextStep, 'step_id')) {
      nextStep.step_id = order
    }
    if (Object.prototype.hasOwnProperty.call(nextStep, 'order')) {
      nextStep.order = order
    }
    if (Object.prototype.hasOwnProperty.call(nextStep, 'index')) {
      nextStep.index = order
    }
    return nextStep
  })
}

function hasStepOrderField(step: Record<string, unknown>) {
  return ['步骤标识', 'step_id', 'sort_order', 'order', 'index'].some(key => (
    Object.prototype.hasOwnProperty.call(step, key)
  ))
}

function handleNormalStepsUpdate(steps: Record<string, unknown>[]) {
  normalSteps.value = steps
  syncCaseJsonFromSteps()
}

function syncCaseJsonFromSteps() {
  if (!selectedCasePage.value) {
    return
  }
  let caseJson: Record<string, unknown>
  try {
    caseJson = JSON.parse(caseJsonText.value || '{}') as Record<string, unknown>
  } catch {
    caseJson = buildCaseDraftJson(selectedCasePage.value, normalSteps.value)
  }
  caseJson.steps = normalSteps.value
  caseJsonText.value = JSON.stringify(caseJson, null, 2)
}

function stepOrder(step: Record<string, unknown>, index: number) {
  return step['步骤标识'] ?? step.step_id ?? step.sort_order ?? step.order ?? step.index ?? index + 1
}

function stepElementId(step: Record<string, unknown>) {
  return step.element_id ?? step['元素ID'] ?? step['元素 ID']
}


function compareCaseSteps(left: Record<string, unknown>, right: Record<string, unknown>) {
  const leftElementId = Number(stepElementId(left))
  const rightElementId = Number(stepElementId(right))
  if (Number.isFinite(leftElementId) && Number.isFinite(rightElementId) && leftElementId !== rightElementId) {
    return leftElementId - rightElementId
  }

  const leftOrder = Number(left['步骤标识'] ?? left.step_id ?? left.sort_order ?? left.order ?? left.index)
  const rightOrder = Number(right['步骤标识'] ?? right.step_id ?? right.sort_order ?? right.order ?? right.index)
  if (Number.isFinite(leftOrder) && Number.isFinite(rightOrder) && leftOrder !== rightOrder) {
    return leftOrder - rightOrder
  }
  return String(left['元素名称'] || left.element_name || left.name || '').localeCompare(String(right['元素名称'] || right.element_name || right.name || ''))
}

function compareElementsById(left: ResourceItem, right: ResourceItem) {
  return left.id - right.id
}

function buildCaseDraftJson(page: ResourceItem, steps: Record<string, unknown>[]) {
  return {
    name: `[正常流程] ${page.name}`,
    case_type: 'WEB',
    category: 'normal',
    priority: 'P1',
    url: page.data.url || '',
    route: page.data.route || '',
    feature_type: page.data.feature_type || 'page',
    steps
  }
}

function buildDrafts(page: ResourceItem, baseCaseJson: Record<string, unknown>) {
  const selectedStrategies = strategies.value.filter(strategy => selectedStrategyIds.value.includes(strategy.id))
  const normalDraft = attachStrategyInfo(withNormalizedSteps(baseCaseJson), selectedStrategies)
  const drafts: Record<string, unknown>[] = [normalDraft]

  for (const strategy of selectedStrategies) {
    const category = strategyCategory(strategy)
    if (category === 'normal') {
      continue
    }
    for (const draft of buildStrategyDrafts(page, normalDraft, strategy, category)) {
      drafts.push(draft)
    }
  }
  return drafts
}

function buildStrategyDrafts(
  page: ResourceItem,
  normalDraft: Record<string, unknown>,
  strategy: ResourceItem,
  category: string
) {
  const targets = category === 'required_empty' ? requiredEmptyTargets(normalDraft) : [null]
  return targets.map(target => {
    const draft = cloneJson(normalDraft)
    const targetLabel = target ? ` - ${target.name}` : ` - ${strategy.name}`
    draft.name = `[${categoryLabel(category)}] ${page.name}${targetLabel}`
    draft.category = category
    draft.priority = category === 'security' ? 'P1' : 'P2'
    draft.strategy_ids = [strategy.id]
    mutateDraftByStrategy(draft, category, target)
    return draft
  })
}

function withNormalizedSteps(caseJson: Record<string, unknown>) {
  const draft = cloneJson(caseJson)
  const steps = caseSteps(draft)
  draft.steps = normalizeCaseSteps(steps)
  delete draft.modal_step_index
  delete draft.modal_step
  return draft
}

function attachStrategyInfo(caseJson: Record<string, unknown>, selectedStrategies: ResourceItem[]) {
  const draft = cloneJson(caseJson)
  draft.strategy_ids = selectedStrategies.map(strategy => strategy.id)
  return draft
}

function caseAssertions(caseJson: Record<string, unknown>) {
  const assertions = caseJson.assertions
  return Array.isArray(assertions)
    ? assertions.filter((item): item is Record<string, unknown> => isRecord(item))
    : [
        { type: 'page_loaded', expected: true },
        { type: 'no_console_error', expected: true }
      ]
}

function caseStrategyIds(caseJson: Record<string, unknown>) {
  const values = Array.isArray(caseJson.strategy_ids) ? caseJson.strategy_ids : []
  return values
    .map(value => Number(value))
    .filter(value => Number.isInteger(value))
}

function withoutCaseMeta(caseJson: Record<string, unknown>) {
  const { assertions, strategies, strategy, strategy_ids, modal_step_index, modal_step, ...rest } = caseJson
  void assertions
  void strategies
  void strategy
  void strategy_ids
  void modal_step_index
  void modal_step
  return rest
}

function mutateDraftByStrategy(
  draft: Record<string, unknown>,
  category: string,
  target?: Record<string, unknown> | null
) {
  const steps = caseSteps(draft)

  const sortedSteps = normalizeCaseSteps(steps)

  if (category === 'required_empty') {
    const requiredFill = target
      ? sortedSteps.find(step => sameRequiredTarget(step, target))
      : sortedSteps.find(step => stepAction(step) === 'fill')
    if (requiredFill) {
      setStepValue(requiredFill, '')
      draft.focus = stepLabel(requiredFill)
      draft.empty_field = stepLabel(requiredFill)
    }
  } else if (category === 'boundary') {
    for (const step of sortedSteps) {
      if (stepAction(step) === 'fill') {
        setStepValue(step, `${stepLabel(step) || 'boundary'}_` + 'x'.repeat(128))
      }
    }
  } else if (category === 'invalid') {
    const fillStep = sortedSteps.find(step => stepAction(step) === 'fill')
    if (fillStep) {
      setStepValue(fillStep, '<scr' + 'ipt>alert(1)</scr' + 'ipt>')
    }
  } else if (category === 'delete_confirm') {
    const clickStep = sortedSteps.find(step => stepAction(step) === 'click')
    if (clickStep) {
      draft.confirm_step = {
        name: stepLabel(clickStep),
        action: stepAction(clickStep),
        confirm_action: 'confirm'
      }
    }
  } else if (category === 'security') {
    const fillStep = sortedSteps.find(step => stepAction(step) === 'fill')
    if (fillStep) {
      setStepValue(fillStep, "' OR 1=1 --")
    }
  }

  draft.steps = sortedSteps
}

function requiredEmptyTargets(caseJson: Record<string, unknown>) {
  const steps = caseSteps(caseJson).filter(step => stepAction(step) === 'fill')
  const elementsByName = new Map(pageElements.value.map(element => [element.name, element]))
  const requiredSteps = steps.filter(step => Boolean(elementsByName.get(stepLabel(step))?.data.required))
  const candidates = requiredSteps.length ? requiredSteps : steps
  return candidates.map(step => ({
    key: step['步骤标识'] ?? step.step_id ?? step.name ?? stepLabel(step),
    name: stepLabel(step)
  }))
}

function sameRequiredTarget(step: Record<string, unknown>, target: Record<string, unknown>) {
  const stepKey = step['步骤标识'] ?? step.step_id ?? step.name ?? stepLabel(step)
  return String(stepKey) === String(target.key) && stepLabel(step) === String(target.name || '')
}

function caseSteps(caseJson: Record<string, unknown>) {
  if (Array.isArray(caseJson.steps)) {
    return caseJson.steps.filter(step => isRecord(step)) as Record<string, unknown>[]
  }
  const request = ensureRecord(caseJson.request)
  return Array.isArray(request.steps)
    ? (request.steps.filter(step => isRecord(step)) as Record<string, unknown>[])
    : []
}

function stepLabel(step: Record<string, unknown>) {
  return String(step['元素名称'] || step.element_name || step.name || step.locator || step['交互类型'] || step.action || '')
}

function stepAction(step: Record<string, unknown>) {
  return String(step['交互类型'] || step.action || '').toLowerCase()
}

function setStepValue(step: Record<string, unknown>, value: unknown) {
  if ('元素值' in step || !('value' in step)) {
    step['元素值'] = value
    return
  }
  step.value = value
}

function isWebStrategy(item: ResourceItem) {
  const domain = item.data.domain
  const kind = item.data.kind
  return (domain === 'WEB' || domain === 'COMMON') && (kind === 'case_template' || kind === 'design_strategy')
}

function strategyCategory(strategy: ResourceItem) {
  const raw = [
    strategy.data.category,
    strategy.data.knowledge_key,
    strategy.name,
    strategy.description
  ].map(value => String(value || '').toLowerCase()).join(' ')

  if (raw.includes('normal') || raw.includes('success') || raw.includes('正常')) {
    return 'normal'
  }
  if (raw.includes('boundary') || raw.includes('边界')) {
    return 'boundary'
  }
  if (raw.includes('required') || raw.includes('empty') || raw.includes('必填') || raw.includes('为空')) {
    return 'required_empty'
  }
  if (raw.includes('delete') || raw.includes('删除')) {
    return 'delete_confirm'
  }
  if (raw.includes('auth') || raw.includes('permission') || raw.includes('security') || raw.includes('鉴权') || raw.includes('权限') || raw.includes('安全')) {
    return 'security'
  }
  if (raw.includes('abnormal') || raw.includes('invalid') || raw.includes('异常')) {
    return 'invalid'
  }
  return 'strategy'
}

function categoryLabel(category: string) {
  const labels: Record<string, string> = {
    normal: '正常流程',
    boundary: '边界场景',
    required_empty: '必填为空',
    delete_confirm: '删除确认',
    security: '安全校验',
    invalid: '异常场景',
    strategy: '策略场景'
  }
  return labels[category] || '策略场景'
}

function defaultAction(elementType: string) {
  const normalizedType = elementType.toLowerCase()
  if (['input', 'textarea', 'text'].includes(normalizedType)) {
    return 'fill'
  }
  if (['select', 'dropdown'].includes(normalizedType)) {
    return 'select'
  }
  if (normalizedType === 'multi_select') {
    return 'multi_select'
  }
  if (['checkbox', 'radio'].includes(normalizedType)) {
    return 'check'
  }
  return 'click'
}

function defaultStepValue(data: Record<string, unknown>, action: string, name: string) {
  if (data.default_value != null && data.default_value !== '') {
    return data.default_value
  }
  if (data.example != null && data.example !== '') {
    return data.example
  }
  if (action === 'fill') {
    const credentialValue = credentialFallbackValue(data, name)
    if (credentialValue !== null) {
      return credentialValue
    }
    return `${name || 'value'}_${Math.random().toString(36).slice(2, 8)}`
  }
  if (action === 'select') {
    return data.option || data.label || ''
  }
  if (action === 'multi_select') {
    return data.option || '-2'
  }
  if (action === 'check') {
    return true
  }
  return null
}

function credentialFallbackValue(data: Record<string, unknown>, name: string) {
  const text = [
    name,
    data.name,
    data.label,
    data.placeholder,
    data.locator,
    data.locator_args,
    data.role_name
  ].map(value => String(value || '').toLowerCase()).join(' ')
  if (['password', 'passwd', 'pwd', '密码', '口令'].some(marker => text.includes(marker))) {
    return '123456'
  }
  if (['phone', 'mobile', '手机号', '手机'].some(marker => text.includes(marker))) {
    return '13800138000'
  }
  if (['email', 'mail', '邮箱'].some(marker => text.includes(marker))) {
    return 'test@example.com'
  }
  if (['username', 'user name', 'account', 'login', '账号', '账户', '用户名'].some(marker => text.includes(marker))) {
    return 'test_user'
  }
  return null
}

function ensureRecord(value: unknown): Record<string, unknown> {
  return isRecord(value) ? value : {}
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function cloneJson<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T
}

function openParseDialog(item: ResourceItem) {
  selectedPage.value = item
  parseError.value = ''
  parseResult.value = null
  parseForm.value = { sourceType: 'codegen', existingElementStrategy: 'update', scriptText: '', file: null }
  codegenMessage.value = ''
  parseVisible.value = true
}

async function closeParseDialog() {
  if (parsing.value) {
    return
  }
  stopCodegenPolling()
  if (activeCodegenSessionId) {
    try {
      await stopWebCodegen(activeCodegenSessionId)
    } catch {
      // The browser may already have been closed outside the platform.
    }
  }
  activeCodegenSessionId = ''
  codegenRunning.value = false
  parseVisible.value = false
}

function handleFileChange(event: Event) {
  const files = (event.target as HTMLInputElement).files
  parseForm.value.file = files?.[0] || null
}

async function submitParse() {
  parseError.value = ''
  parseResult.value = null
  if (!selectedPage.value) {
    parseError.value = '请选择页面'
    return
  }
  if (!parseForm.value.file && !parseForm.value.scriptText.trim()) {
    parseError.value = '请上传脚本文件或粘贴脚本内容'
    return
  }
  parsing.value = true
  try {
    parseResult.value = await parseWebScript(
      Number(selectedPage.value.project_id || 0),
      selectedPage.value.id,
      parseForm.value.sourceType,
      parseForm.value.scriptText,
      parseForm.value.file,
      parseForm.value.existingElementStrategy
    )
    await resourcePageRef.value?.load()
  } catch (error) {
    parseError.value = getErrorMessage(error)
  } finally {
    parsing.value = false
  }
}

async function startCodegen() {
  parseError.value = ''
  codegenMessage.value = ''
  if (!selectedPage.value) {
    parseError.value = '请选择页面'
    return
  }
  const targetUrl = String(
    selectedPage.value.data.url
    || selectedPage.value.data.route
    || selectedPage.value.description
    || ''
  )
  if (!targetUrl) {
    parseError.value = '页面地址为空，无法启动 codegen'
    return
  }
  try {
    const session = await startWebCodegen(selectedPage.value.id, targetUrl, {
      projectId: Number(selectedPage.value.project_id || 0) || undefined,
      featureType: String(selectedPage.value.data.feature_type || ''),
      featureName: selectedPage.value.name
    })
    activeCodegenSessionId = session.session_id
    codegenRunning.value = true
    codegenMessage.value = `codegen 已启动，请在打开的浏览器中完成“${selectedPage.value.name}”功能操作后关闭浏览器。`
    pollCodegen(session.session_id)
  } catch (error) {
    activeCodegenSessionId = ''
    codegenRunning.value = false
    parseError.value = getErrorMessage(error)
  }
}

function pollCodegen(sessionId: string) {
  stopCodegenPolling()
  codegenTimer = window.setInterval(async () => {
    if (codegenPollBusy) {
      return
    }
    codegenPollBusy = true
    try {
      const session = await getWebCodegenStatus(sessionId)
      codegenMessage.value = `当前状态：${formatCodegenStatus(session.status)}`
      if (session.script_text) {
        parseForm.value.scriptText = session.script_text
        codegenMessage.value = session.ended_by_browser_close
          ? `检测到录制浏览器已关闭，脚本已生成：${session.script_path}`
          : `脚本已生成：${session.script_path}`
      }
      if (session.status !== 'running') {
        await finishCodegen(sessionId, session)
      }
    } catch (error) {
      stopCodegenPolling()
      codegenRunning.value = false
      activeCodegenSessionId = ''
      parseError.value = getErrorMessage(error)
    } finally {
      codegenPollBusy = false
    }
  }, 2000)
}

async function finishCodegen(sessionId: string, session: Awaited<ReturnType<typeof getWebCodegenStatus>>) {
  stopCodegenPolling()
  let finalSession = session
  try {
    finalSession = await stopWebCodegen(sessionId)
  } catch {
    // Keep the last successful status response when the process has already exited.
  }
  codegenRunning.value = false
  activeCodegenSessionId = ''

  if (finalSession.script_text) {
    parseForm.value.scriptText = finalSession.script_text
  }
  if (finalSession.status === 'failed') {
    parseError.value = 'codegen 录制失败，请确认后端已安装 playwright 和浏览器'
    return
  }
  if (!parseForm.value.scriptText.trim()) {
    codegenMessage.value = 'codegen 已结束，但没有生成脚本内容'
    return
  }

  codegenMessage.value = '浏览器已关闭，正在解析刚刚录制的脚本...'
  await submitParse()
  if (parseResult.value) {
    codegenMessage.value = `脚本解析完成，已保存 ${parseResult.value.element_count} 个元素。`
  }
}

function stopCodegenPolling() {
  if (codegenTimer != null) {
    window.clearInterval(codegenTimer)
    codegenTimer = null
  }
  codegenPollBusy = false
}

function formatCodegenStatus(status: string) {
  const labels: Record<string, string> = {
    running: '录制中',
    finished: '已生成',
    failed: '失败'
  }
  return labels[status] || status
}

function getErrorMessage(error: unknown) {
  const responseData = (error as { response?: { data?: { message?: string; detail?: unknown } } }).response?.data
  if (responseData?.message) {
    return responseData.message
  }
  if (typeof responseData?.detail === 'string') {
    return responseData.detail
  }
  if (responseData?.detail) {
    return JSON.stringify(responseData.detail)
  }
  return error instanceof Error ? error.message : '解析失败'
}
</script>

<style scoped>
.feature-type-filter {
  flex: 0 0 124px;
  width: 124px;
  min-width: 124px;
}

@media (max-width: 720px) {
  .feature-type-filter {
    flex: 1 1 100%;
    width: 100%;
    min-width: 0;
  }
}
</style>
