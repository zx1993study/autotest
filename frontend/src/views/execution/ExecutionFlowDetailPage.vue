<template>
  <section class="flow-detail-page">
    <header class="page-header">
      <div>
        <button class="back-button" type="button" @click="goBack">返回</button>
        <h2>{{ flow?.name || '执行流程详情' }}</h2>
      </div>
      <button class="primary" type="button" @click="openAddStep">添加步骤</button>
    </header>

    <p v-if="formError" class="form-error page-error">{{ formError }}</p>

    <section v-if="stepDrafts.length" class="step-panel">
      <div v-if="stepDrafts.length" class="step-card-row">
        <ExecutionFlowStepCard
          v-for="(draft, index) in stepDrafts"
          :key="draft.uid"
          :draft="draft"
          :index="index"
          :loading-options="loadingOptions"
          :auth-options="authOptions"
          :api-options="apiOptions"
          :case-options="filteredCaseOptionsForDraft(draft)"
          :can-save="canSaveDraft(draft)"
          :title="draftCaseTitle(draft)"
          :active-record="draftActiveRecord(draft)"
          :record-data="draftRecordData(draft)"
          :response-body-text="draftResponseBodyText(draft)"
          :result-status-text="draftResultStatusText(draft)"
          :result-status-class="draftResultStatusClass(draft)"
          :case-option-label="caseOptionLabel"
          :format-duration="formatDuration"
          :stringify-json="stringifyJson"
          @remove="removeStepDraft"
          @save="saveStepDraft"
          @run="runStepDraft"
          @api-change="handleDraftApiChange"
          @case-change="handleDraftCaseChange"
        />
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import ExecutionFlowStepCard from '../../components/execution/ExecutionFlowStepCard.vue'
import {
  getResource,
  listRemoteOptions,
  listResources,
  updateResource
} from '../../api/http'
import { ExecutionMode } from '../../constants/enums'
import { runApiCases } from '../../services/api-case.service'
import type { ResourceItem, SelectOptionRecord } from '../../api/http'
import type { ExecutionRecord, ExecutionSummary, FlowStep, StepDraft } from '../../types/execution-flow'
import { formatJsonLikeText } from '../../utils/jsonFormatter'
import { apiOptionLabel } from '../../utils/apiOptions'

const RESOURCE_FETCH_PAGE_SIZE = 200

const route = useRoute()
const router = useRouter()
const flow = ref<ResourceItem | null>(null)
const flowSteps = ref<FlowStep[]>([])
const stepDrafts = ref<StepDraft[]>([])
const apiOptions = ref<SelectOptionRecord[]>([])
const authOptions = ref<SelectOptionRecord[]>([])
const caseOptions = ref<ResourceItem[]>([])
const loadingOptions = ref(false)
const formError = ref('')
let nextDraftId = 1

const projectId = computed(() => Number(flow.value?.project_id || 0))

onMounted(async () => {
  await loadFlow()
})

async function loadFlow() {
  const flowId = Number(route.params.flowId || 0)
  if (!flowId) {
    formError.value = '流程 ID 不合法'
    return
  }
  flow.value = await getResource('/execution/flows', flowId)
  flowSteps.value = normalizeFlowSteps(flow.value.data.steps)
  stepDrafts.value = flowSteps.value.map((step, index) => createStepDraft(step, index))
  if (projectId.value) {
    await loadProjectOptions(projectId.value)
  }
}

async function loadProjectOptions(currentProjectId: number) {
  loadingOptions.value = true
  try {
    const [apis, auths, cases] = await Promise.all([
      listRemoteOptions('/api-testing/interfaces/options', { project_id: currentProjectId }),
      listRemoteOptions('/project-auth/options', { project_id: currentProjectId, login_case_type: 'API' }),
      listAllResourceItems('/api-testing/cases', { project_id: currentProjectId })
    ])
    apiOptions.value = apis
    authOptions.value = auths
    caseOptions.value = cases.filter(item => item.status === 'active')
  } catch (error) {
    formError.value = getErrorMessage(error)
  } finally {
    loadingOptions.value = false
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

function openAddStep() {
  stepDrafts.value.push(createStepDraft())
}

async function saveStepDraft(index: number) {
  const draft = stepDrafts.value[index]
  if (!draft) {
    return
  }
  const step = buildStepFromDraft(draft)
  if (!step) {
    return
  }
  const nextSteps = stepDrafts.value
    .map((item, itemIndex) => (itemIndex === index ? step : draftToFlowStep(item)))
    .filter((item): item is FlowStep => Boolean(item))

  draft.saving = true
  try {
    await persistSteps(nextSteps)
    flowSteps.value = nextSteps
    draft.persistedIndex = index
    Object.assign(draft, step)
  } catch (error) {
    draft.formError = getErrorMessage(error)
  } finally {
    draft.saving = false
  }
}

async function removeStepDraft(index: number) {
  const nextDrafts = stepDrafts.value.filter((_, itemIndex) => itemIndex !== index)
  const nextSteps = nextDrafts
    .map(draftToFlowStep)
    .filter((item): item is FlowStep => Boolean(item))
  try {
    await persistSteps(nextSteps)
    stepDrafts.value = nextDrafts.map((draft, itemIndex) => ({ ...draft, persistedIndex: itemIndex }))
    flowSteps.value = nextSteps
  } catch (error) {
    formError.value = getErrorMessage(error)
  }
}

async function persistSteps(steps: FlowStep[]) {
  if (!flow.value) {
    return
  }
  const nextData = { ...(flow.value.data || {}), steps }
  const updated = await updateResource('/execution/flows', flow.value.id, {
    name: flow.value.name,
    project_id: flow.value.project_id,
    description: flow.value.description,
    data: nextData
  })
  flow.value = updated
}

async function runStepDraft(draft: StepDraft) {
  const step = buildStepFromDraft(draft)
  if (!step) {
    return
  }
  draft.executing = true
  draft.executionSummary = null
  try {
    draft.executionSummary = await executeStep(step)
  } finally {
    draft.executing = false
  }
}

async function executeStep(step: FlowStep): Promise<ExecutionSummary | null> {
  if (!projectId.value) {
    formError.value = '流程未绑定项目'
    return null
  }
  formError.value = ''
  try {
    return await runApiCases({
      project_id: projectId.value,
      auth_id: step.auth_id || null,
      case_ids: [step.case_id],
      mode: ExecutionMode.LOCAL_HEADLESS,
      config: { params: step.case_json || {} }
    })
  } catch (error) {
    formError.value = getErrorMessage(error)
    return null
  }
}

function createStepDraft(step?: FlowStep, persistedIndex: number | null = null): StepDraft {
  const source = step || {
    api_id: 0,
    api_label: '',
    auth_id: null,
    token_label: '',
    case_id: 0,
    case_label: '',
    case_json: {}
  }
  return {
    ...source,
    uid: `step-draft-${nextDraftId++}`,
    persistedIndex,
    selectedApiId: Number(source.api_id || 0),
    selectedAuthId: Number(source.auth_id || 0),
    selectedCaseId: Number(source.case_id || 0),
    caseTitle: source.case_label || '',
    caseJsonText: stringifyJson(source.case_json || {}),
    apiKeyword: source.api_label || '',
    formError: '',
    saving: false,
    executing: false,
    executionSummary: null
  }
}

function canSaveDraft(draft: StepDraft): boolean {
  return Boolean(projectId.value && draft.selectedCaseId)
}

function draftActiveRecord(draft: StepDraft): ExecutionRecord | null {
  return draft.executionSummary?.records[0] || null
}

function draftRecordData(draft: StepDraft): Record<string, unknown> {
  return draftActiveRecord(draft)?.data || {}
}

function draftResponseBodyText(draft: StepDraft): string {
  return formatJsonLikeText(draftRecordData(draft).response_body)
}

function draftResultStatusText(draft: StepDraft): string {
  const status = String(draftActiveRecord(draft)?.status || '')
  if (!status) {
    return '未运行'
  }
  const labels: Record<string, string> = {
    success: '成功',
    failed: '失败',
    queued: '排队中',
    running: '运行中'
  }
  return labels[status] || status
}

function draftResultStatusClass(draft: StepDraft): string {
  const status = String(draftActiveRecord(draft)?.status || '')
  if (status === 'success') {
    return 'success'
  }
  if (status === 'failed') {
    return 'failed'
  }
  return 'idle'
}

function draftToFlowStep(draft: StepDraft): FlowStep | null {
  if (!draft.selectedCaseId) {
    return null
  }
  try {
    return {
      api_id: draft.selectedApiId,
      api_label: draftApiLabel(draft),
      auth_id: draft.selectedAuthId || null,
      token_label: draftTokenLabel(draft),
      case_id: draft.selectedCaseId,
      case_label: draftCaseLabel(draft),
      case_json: parseJsonObject(draft.caseJsonText, '用例 JSON')
    }
  } catch {
    return null
  }
}

function buildStepFromDraft(draft: StepDraft): FlowStep | null {
  draft.formError = ''
  if (!draft.selectedCaseId) {
    draft.formError = '请选择 API 用例'
    return null
  }
  let caseJson: Record<string, unknown>
  try {
    caseJson = parseJsonObject(draft.caseJsonText, '用例 JSON')
  } catch (error) {
    draft.formError = error instanceof Error ? error.message : '用例 JSON 不合法'
    return null
  }
  return {
    api_id: draft.selectedApiId,
    api_label: draftApiLabel(draft),
    auth_id: draft.selectedAuthId || null,
    token_label: draftTokenLabel(draft),
    case_id: draft.selectedCaseId,
    case_label: draftCaseLabel(draft),
    case_json: caseJson
  }
}

function filteredCaseOptionsForDraft(draft: StepDraft): ResourceItem[] {
  if (!draft.selectedApiId) {
    return caseOptions.value
  }
  return caseOptions.value.filter(item => Number(item.source_id || 0) === draft.selectedApiId)
}

async function handleDraftApiChange(draft: StepDraft) {
  draft.executionSummary = null
  draft.formError = ''
  const selectedApi = apiOptions.value.find(api => api.id === draft.selectedApiId)
  draft.apiKeyword = selectedApi ? apiOptionLabel(selectedApi) : ''
  draft.api_label = draft.apiKeyword
  if (draft.selectedCaseId && !filteredCaseOptionsForDraft(draft).some(item => item.id === draft.selectedCaseId)) {
    draft.selectedCaseId = 0
    draft.case_label = ''
    draft.caseTitle = ''
  }
  if (draft.selectedApiId && !draft.selectedCaseId) {
    draft.caseJsonText = stringifyJson(await buildParamsFromFields(draft.selectedApiId))
  }
}

async function handleDraftCaseChange(draft: StepDraft) {
  draft.executionSummary = null
  draft.formError = ''
  if (!draft.selectedCaseId) {
    return
  }
  const item = await getResource('/api-testing/cases', draft.selectedCaseId)
  const sourceId = Number(item.source_id || 0)
  if (sourceId && draft.selectedApiId !== sourceId) {
    draft.selectedApiId = sourceId
    fillDraftApiKeyword(draft)
  }
  draft.caseJsonText = stringifyJson(extractCaseParams(item))
  draft.case_label = caseNameLabel(item)
  draft.caseTitle = caseNameLabel(item)
}

function fillDraftApiKeyword(draft: StepDraft) {
  const selectedApi = apiOptions.value.find(api => api.id === draft.selectedApiId)
  draft.apiKeyword = selectedApi ? apiOptionLabel(selectedApi) : draft.api_label || ''
}

function draftApiLabel(draft: StepDraft): string {
  const api = apiOptions.value.find(item => item.id === draft.selectedApiId)
  return api ? apiOptionLabel(api) : draft.api_label || ''
}

function draftTokenLabel(draft: StepDraft): string {
  const auth = authOptions.value.find(item => item.id === draft.selectedAuthId)
  return auth?.name ? String(auth.name) : draft.token_label || ''
}

function draftCaseLabel(draft: StepDraft): string {
  const item = caseOptions.value.find(caseItem => caseItem.id === draft.selectedCaseId)
  return item ? caseNameLabel(item) : draft.case_label || ''
}

function draftCaseTitle(draft: StepDraft): string {
  const item = caseOptions.value.find(caseItem => caseItem.id === draft.selectedCaseId)
  return item ? caseNameLabel(item) : draft.caseTitle || draft.case_label || ''
}

async function buildParamsFromFields(apiId: number) {
  const fields = await listAllResourceItems('/api-testing/fields', {
    project_id: projectId.value,
    interface_id: apiId
  })
  const params: Record<string, unknown> = {}
  for (const field of fields) {
    const data = field.data || {}
    const name = String(data.name || field.name || '').trim()
    if (name) {
      params[name] = exampleValue(data, name)
    }
  }
  return params
}

function extractCaseParams(item: ResourceItem): Record<string, unknown> {
  const data = item.data || {}
  const request = isRecord(data.request) ? data.request : {}
  const params = isRecord(data.params) ? data.params : request.params
  return isRecord(params) ? cloneRecord(params) : {}
}

function normalizeFlowSteps(value: unknown): FlowStep[] {
  if (!Array.isArray(value)) {
    return []
  }
  return value.filter(isRecord).map(item => ({
    api_id: toNumber(item.api_id),
    api_label: String(item.api_label || ''),
    auth_id: item.auth_id == null ? null : toNumber(item.auth_id),
    token_label: String(item.token_label || ''),
    case_id: toNumber(item.case_id),
    case_label: String(item.case_label || ''),
    case_json: isRecord(item.case_json) ? cloneRecord(item.case_json) : {}
  })).filter(item => item.case_id > 0)
}

function caseOptionLabel(item: ResourceItem): string {
  const method = String(item.data.api_method || item.data.method || '').toUpperCase()
  const path = String(item.data.api_path || item.data.path || '')
  return [method, path].filter(Boolean).join(' ') || String(item.name || '')
}

function caseNameLabel(item: ResourceItem): string {
  return String(item.name || '')
}

function parseJsonObject(value: string, label: string): Record<string, unknown> {
  if (!value.trim()) {
    return {}
  }
  const parsed = JSON.parse(value) as unknown
  if (!isRecord(parsed)) {
    throw new Error(`${label} 必须是 JSON 对象`)
  }
  return parsed
}

function stringifyJson(value: unknown): string {
  return JSON.stringify(value ?? {}, null, 2)
}

function exampleValue(data: Record<string, unknown>, fieldName: string): unknown {
  if (data.example != null && data.example !== '') {
    return data.example
  }
  if (data.default_value != null && data.default_value !== '') {
    return data.default_value
  }
  const type = String(data.field_type || data.type || 'string')
  if (type === 'integer' || type === 'number') {
    return 1
  }
  if (type === 'boolean') {
    return true
  }
  if (type === 'array') {
    return []
  }
  if (type === 'object') {
    return {}
  }
  return `${fieldName}_value`
}

function formatDuration(value: unknown): string {
  const duration = Number(value)
  return Number.isFinite(duration) ? `${duration} ms` : '-'
}

function getErrorMessage(error: unknown): string {
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
  return error instanceof Error ? error.message : '操作失败'
}

function cloneRecord(value: Record<string, unknown>): Record<string, unknown> {
  return JSON.parse(JSON.stringify(value)) as Record<string, unknown>
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function toNumber(value: unknown): number {
  const numberValue = Number(value)
  return Number.isFinite(numberValue) ? numberValue : 0
}

function goBack() {
  router.push('/execution/flows')
}
</script>

<style scoped>
.flow-detail-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
}

.page-header h2 {
  margin: 8px 0 0;
  color: #111827;
  font-size: 22px;
}

.page-header p {
  margin: 6px 0 0;
  color: #6b7280;
  font-size: 14px;
}

.back-button,
.step-item button,
.form-actions button,
.step-panel-header button,
.page-header button {
  height: 34px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  color: #374151;
  cursor: pointer;
  padding: 0 12px;
}

.primary,
.step-panel-header button.primary {
  border-color: #2563eb;
  background: #2563eb;
  color: #fff;
}

.danger {
  border-color: #fecaca;
  color: #dc2626;
}

.detail-layout {
  display: grid;
  grid-template-columns: minmax(300px, 360px) minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}

.flow-panel {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 10px 28px rgb(15 23 42 / 6%);
}

.flow-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 18px;
}

.flow-summary {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.flow-summary span,
.flow-summary small {
  color: #6b7280;
  font-size: 13px;
}

.flow-summary strong {
  color: #111827;
  font-size: 18px;
}

.steps-section header,
.step-panel-header,
.execution-result header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.steps-section h3,
.step-panel-header h3,
.execution-result h3 {
  margin: 0;
  color: #111827;
  font-size: 17px;
}

.steps-section header span,
.step-panel-header p {
  margin: 4px 0 0;
  color: #6b7280;
  font-size: 13px;
}

.step-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 12px;
}

.step-item {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 12px;
}

.step-item.active {
  border-color: #2563eb;
}

.step-item div {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.step-item b {
  color: #111827;
}

.step-item span,
.step-item small {
  color: #6b7280;
  font-size: 13px;
}

.step-item footer {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.step-panel {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 16px;
  padding: 0;
}

.step-card-row {
  display: flex;
  align-items: stretch;
  gap: 16px;
  overflow-x: auto;
  padding-bottom: 4px;
}

.step-card {
  display: flex;
  flex: 0 0 min(520px, calc(100vw - 64px));
  flex-direction: column;
  gap: 14px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  padding: 16px;
}

.step-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.step-card-header h3 {
  margin: 0;
  color: #111827;
  font-size: 17px;
}

.step-card-header p {
  margin: 4px 0 0;
  color: #6b7280;
  font-size: 13px;
}

.step-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.field-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 7px;
  color: #374151;
  font-size: 13px;
  font-weight: 600;
}

.field.full {
  grid-column: 1 / -1;
}

.field b {
  margin-left: 3px;
  color: #dc2626;
}

.field select,
.filter-input,
.json-editor {
  width: 100%;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  color: #111827;
  font: inherit;
}

.field select,
.filter-input {
  height: 38px;
  padding: 0 10px;
}

.json-editor {
  min-height: 260px;
  padding: 12px;
  font-family: Consolas, Monaco, 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.55;
  resize: vertical;
}

.form-error {
  margin: 0;
  color: #dc2626;
  font-size: 13px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.form-actions button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.empty-config,
.empty-text {
  color: #6b7280;
  font-size: 13px;
}

.empty-config {
  display: flex;
  min-height: 180px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: 1px dashed #d1d5db;
  border-radius: 8px;
  text-align: center;
}

.empty-config strong {
  color: #111827;
}

.execution-result {
  display: flex;
  flex-direction: column;
  gap: 14px;
  border-top: 1px solid #e5e7eb;
  padding-top: 16px;
}

.status-pill {
  display: inline-flex;
  min-width: 68px;
  justify-content: center;
  border-radius: 999px;
  padding: 5px 10px;
  font-size: 12px;
  font-weight: 700;
}

.status-pill.idle {
  background: #f3f4f6;
  color: #4b5563;
}

.status-pill.success {
  background: #dcfce7;
  color: #166534;
}

.status-pill.failed {
  background: #fee2e2;
  color: #991b1b;
}

.result-content {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.result-meta {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin: 0;
}

.step-card .result-meta {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.result-meta div {
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 10px;
}

.result-meta dt {
  color: #6b7280;
  font-size: 12px;
}

.result-meta dd {
  margin: 5px 0 0;
  color: #111827;
  font-size: 14px;
  font-weight: 700;
  word-break: break-word;
}

.result-block {
  border: 1px solid #e5e7eb;
  border-radius: 6px;
}

.result-block summary {
  cursor: pointer;
  padding: 11px 12px;
  color: #111827;
  font-weight: 700;
}

.result-block pre {
  max-height: 360px;
  overflow: auto;
  margin: 0;
  border-top: 1px solid #e5e7eb;
  background: #0f172a;
  color: #e5e7eb;
  padding: 14px;
  font-size: 13px;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
}

@media (max-width: 1120px) {
  .detail-layout {
    grid-template-columns: 1fr;
  }

  .result-meta {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .field-grid,
  .result-meta {
    grid-template-columns: 1fr;
  }

  .step-panel-header,
  .execution-result header {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
