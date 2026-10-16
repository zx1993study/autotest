<template>
  <section class="dashboard-page">
    <header class="page-header">
      <div>
        <h2>执行看板</h2>
        <p>面向 API 用例的快速调试与结果查看。</p>
      </div>
    </header>

    <div class="dashboard-layout">
      <section class="control-panel" aria-label="执行配置">
        <div class="field-grid">
          <label class="field">
            <span>项目<b>*</b></span>
            <select v-model.number="selectedProjectId">
              <option :value="0">请选择项目</option>
              <option v-for="project in projects" :key="project.id" :value="project.id">
                {{ project.name }}
              </option>
            </select>
          </label>

          <label class="field">
            <span>API</span>
            <ApiSelect v-model="selectedApiId" :options="apiOptions" label="API" :disabled="!selectedProjectId" :loading="loadingOptions" />
          </label>

          <label class="field">
            <span>API Token</span>
            <select v-model.number="selectedAuthId" :disabled="!selectedProjectId || loadingOptions">
              <option :value="0">不使用鉴权</option>
              <option v-for="auth in authOptions" :key="auth.id" :value="auth.id">
                {{ auth.name || `#${auth.id}` }}
              </option>
            </select>
          </label>

          <label class="field">
            <span>API 用例<b>*</b></span>
            <select v-model.number="selectedCaseId" :disabled="!selectedProjectId || loadingOptions">
              <option :value="0">请选择 API 用例</option>
              <option v-for="item in filteredCaseOptions" :key="item.id" :value="item.id">
                {{ caseOptionLabel(item) }}
              </option>
            </select>
          </label>
        </div>

        <label class="field full">
          <span>参数 JSON</span>
          <textarea
            v-model="paramsJson"
            class="json-editor"
            rows="18"
            spellcheck="false"
          ></textarea>
        </label>

        <p v-if="formError" class="form-error">{{ formError }}</p>

        <footer class="control-actions">
          <button type="button" :disabled="executing || loadingOptions" @click="resetParamsFromSelection">
            重置参数
          </button>
          <button class="primary" type="button" :disabled="executing || !canExecute" @click="executeCase">
            {{ executing ? '执行中...' : '执行' }}
          </button>
        </footer>
      </section>

      <section class="result-panel" aria-label="执行结果">
        <header class="result-header">
          <div>
            <h3>API 返回结果</h3>
            <p>{{ resultSubtitle }}</p>
          </div>
          <span class="status-pill" :class="resultStatusClass">{{ resultStatusText }}</span>
        </header>

        <div v-if="activeRecord" class="result-content">
          <dl class="result-meta">
            <div>
              <dt>记录 ID</dt>
              <dd>#{{ activeRecord.id }}</dd>
            </div>
            <div>
              <dt>HTTP 状态</dt>
              <dd>{{ recordData.response_status ?? '-' }}</dd>
            </div>
            <div>
              <dt>耗时</dt>
              <dd>{{ formatDuration(recordData.duration_ms) }}</dd>
            </div>
            <div>
              <dt>错误</dt>
              <dd>{{ recordData.error || '-' }}</dd>
            </div>
          </dl>

          <section v-if="assertions.length" class="assertion-strip">
            <span
              v-for="(assertion, index) in assertions"
              :key="index"
              class="assertion-pill"
              :class="{ passed: assertionPassed(assertion), failed: assertionPassed(assertion) === false }"
            >
              {{ assertionLabel(assertion) }}
            </span>
          </section>

          <details open class="result-block">
            <summary>响应体</summary>
            <pre>{{ responseBodyText }}</pre>
          </details>

          <details class="result-block">
            <summary>请求信息</summary>
            <pre>{{ stringifyJson(recordData.request || {}) }}</pre>
          </details>

          <details class="result-block">
            <summary>响应头</summary>
            <pre>{{ stringifyJson(recordData.response_headers || {}) }}</pre>
          </details>
        </div>

        <div v-else class="empty-result">
          <strong>暂无执行结果</strong>
          <span>选择 API 用例并执行后，返回信息会显示在这里。</span>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import ApiSelect from '../../components/common/ApiSelect.vue'

import {
  getResource,
  listProjectOptions,
  listRemoteOptions,
  listResources,
  ProjectOption,
  ResourceItem,
  SelectOptionRecord,
  resolveDefaultProjectId
} from '../../api/http'
import { ExecutionMode } from '../../constants/enums'
import { runApiCases } from '../../services/api-case.service'
import { formatJsonLikeText } from '../../utils/jsonFormatter'

type ExecutionRecord = ResourceItem & {
  data: Record<string, unknown>
}

type ExecutionSummary = {
  total: number
  success_count: number
  failed_count: number
  queued_count: number
  records: ExecutionRecord[]
}

const RESOURCE_FETCH_PAGE_SIZE = 200

const projects = ref<ProjectOption[]>([])
const apiOptions = ref<SelectOptionRecord[]>([])
const authOptions = ref<SelectOptionRecord[]>([])
const caseOptions = ref<ResourceItem[]>([])
const selectedProjectId = ref(0)
const selectedApiId = ref(0)
const selectedAuthId = ref(0)
const selectedCaseId = ref(0)
const paramsJson = ref('{}')
const formError = ref('')
const loadingOptions = ref(false)
const executing = ref(false)
const executionSummary = ref<ExecutionSummary | null>(null)

const filteredCaseOptions = computed(() => {
  if (!selectedApiId.value) {
    return caseOptions.value
  }
  return caseOptions.value.filter(item => Number(item.source_id || 0) === selectedApiId.value)
})

const activeRecord = computed<ExecutionRecord | null>(() => {
  const records = executionSummary.value?.records || []
  return records[0] || null
})

const recordData = computed(() => activeRecord.value?.data || {})

const assertions = computed<Record<string, unknown>[]>(() => {
  const value = recordData.value.assertions
  return Array.isArray(value) ? value.filter(isRecord) : []
})

const responseBodyText = computed(() => {
  return formatJsonLikeText(recordData.value.response_body)
})

const canExecute = computed(() => selectedProjectId.value > 0 && selectedCaseId.value > 0)

const resultStatusText = computed(() => {
  const status = String(activeRecord.value?.status || '')
  if (!status) {
    return '未执行'
  }
  const labels: Record<string, string> = {
    success: '成功',
    failed: '失败',
    queued: '排队中',
    running: '执行中'
  }
  return labels[status] || status
})

const resultStatusClass = computed(() => {
  const status = String(activeRecord.value?.status || '')
  if (status === 'success') {
    return 'success'
  }
  if (status === 'failed') {
    return 'failed'
  }
  return 'idle'
})

const resultSubtitle = computed(() => {
  if (!executionSummary.value) {
    return '等待执行'
  }
  return `共 ${executionSummary.value.total} 条，成功 ${executionSummary.value.success_count} 条，失败 ${executionSummary.value.failed_count} 条`
})

onMounted(async () => {
  projects.value = await listProjectOptions()
  selectedProjectId.value = resolveDefaultProjectId(projects.value)
})

watch(selectedProjectId, async projectId => {
  selectedApiId.value = 0
  selectedAuthId.value = 0
  selectedCaseId.value = 0
  apiOptions.value = []
  authOptions.value = []
  caseOptions.value = []
  paramsJson.value = '{}'
  executionSummary.value = null
  formError.value = ''
  if (!projectId) {
    return
  }
  await loadProjectOptions(projectId)
})

watch(selectedApiId, async apiId => {
  executionSummary.value = null
  formError.value = ''
  if (selectedCaseId.value && !filteredCaseOptions.value.some(item => item.id === selectedCaseId.value)) {
    selectedCaseId.value = 0
  }
  if (apiId && !selectedCaseId.value) {
    paramsJson.value = stringifyJson(await buildParamsFromFields(apiId))
  }
})

watch(selectedCaseId, async caseId => {
  executionSummary.value = null
  formError.value = ''
  if (!caseId) {
    return
  }
  const item = await getResource('/api-testing/cases', caseId)
  const sourceId = Number(item.source_id || 0)
  if (sourceId && selectedApiId.value !== sourceId) {
    selectedApiId.value = sourceId
  }
  paramsJson.value = stringifyJson(extractCaseParams(item))
})

async function loadProjectOptions(projectId: number) {
  loadingOptions.value = true
  try {
    const [apis, auths, cases] = await Promise.all([
      listRemoteOptions('/api-testing/interfaces/options', { project_id: projectId }),
      listRemoteOptions('/project-auth/options', { project_id: projectId, login_case_type: 'API' }),
      listAllResourceItems('/api-testing/cases', { project_id: projectId })
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

async function buildParamsFromFields(apiId: number) {
  const fields = await listAllResourceItems('/api-testing/fields', {
    project_id: selectedProjectId.value,
    interface_id: apiId
  })
  const params: Record<string, unknown> = {}
  for (const field of fields) {
    const data = field.data || {}
    const name = String(data.name || field.name || '').trim()
    if (!name) {
      continue
    }
    params[name] = exampleValue(data, name)
  }
  return params
}

function extractCaseParams(item: ResourceItem): Record<string, unknown> {
  const data = item.data || {}
  const request = isRecord(data.request) ? data.request : {}
  const params = isRecord(data.params) ? data.params : request.params
  if (isRecord(params)) {
    return cloneRecord(params)
  }
  return {}
}

async function resetParamsFromSelection() {
  formError.value = ''
  if (selectedCaseId.value) {
    const item = await getResource('/api-testing/cases', selectedCaseId.value)
    paramsJson.value = stringifyJson(extractCaseParams(item))
    return
  }
  if (selectedApiId.value) {
    paramsJson.value = stringifyJson(await buildParamsFromFields(selectedApiId.value))
    return
  }
  paramsJson.value = '{}'
}

async function executeCase() {
  formError.value = ''
  if (!canExecute.value) {
    formError.value = '请选择项目和 API 用例'
    return
  }

  let params: Record<string, unknown>
  try {
    params = parseJsonObject(paramsJson.value, '参数 JSON')
  } catch (error) {
    formError.value = error instanceof Error ? error.message : '参数 JSON 不合法'
    return
  }

  executing.value = true
  try {
    executionSummary.value = await runApiCases({
      project_id: selectedProjectId.value,
      auth_id: selectedAuthId.value || null,
      case_ids: [selectedCaseId.value],
      mode: ExecutionMode.LOCAL_HEADLESS,
      config: { params }
    })
  } catch (error) {
    formError.value = getErrorMessage(error)
  } finally {
    executing.value = false
  }
}

function caseOptionLabel(item: ResourceItem): string {
  const method = String(item.data.api_method || item.data.method || '').toUpperCase()
  const path = String(item.data.api_path || item.data.path || '')
  return [method, path].filter(Boolean).join(' ') || String(item.name || '')
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
  if (type === 'integer') {
    return 1
  }
  if (type === 'number') {
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

function assertionPassed(assertion: Record<string, unknown>): boolean | null {
  if (typeof assertion.passed === 'boolean') {
    return assertion.passed
  }
  return null
}

function assertionLabel(assertion: Record<string, unknown>): string {
  const type = String(assertion.type || 'assertion')
  const passed = assertionPassed(assertion)
  const result = passed == null ? '' : passed ? '通过' : '失败'
  return [type, result].filter(Boolean).join(' ')
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
  return error instanceof Error ? error.message : '执行失败'
}

function cloneRecord(value: Record<string, unknown>): Record<string, unknown> {
  return JSON.parse(JSON.stringify(value)) as Record<string, unknown>
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}
</script>

<style scoped>
.dashboard-page {
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
  margin: 0;
  color: #111827;
  font-size: 22px;
}

.page-header p {
  margin: 6px 0 0;
  color: #6b7280;
  font-size: 14px;
}

.dashboard-layout {
  --dashboard-panel-initial-height: 850px;
  display: grid;
  grid-template-columns: minmax(360px, 460px) minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}

.control-panel,
.result-panel {
  min-width: 0;
  min-height: var(--dashboard-panel-initial-height);
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 10px 28px rgb(15 23 42 / 6%);
}

.control-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 18px;
}

.field-grid {
  display: grid;
  grid-template-columns: 1fr;
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

.field select:disabled,
.filter-input:disabled {
  background: #f9fafb;
  color: #9ca3af;
}

.json-editor {
  min-height: 320px;
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

.control-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.control-actions button {
  height: 38px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  color: #374151;
  cursor: pointer;
  padding: 0 16px;
}

.control-actions button.primary {
  border-color: #2563eb;
  background: #2563eb;
  color: #fff;
}

.control-actions button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.result-panel {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid #e5e7eb;
  padding: 18px;
}

.result-header h3 {
  margin: 0;
  color: #111827;
  font-size: 18px;
}

.result-header p {
  margin: 5px 0 0;
  color: #6b7280;
  font-size: 13px;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 68px;
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
  flex: 1;
  flex-direction: column;
  gap: 14px;
  padding: 18px;
}

.result-meta {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin: 0;
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

.assertion-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.assertion-pill {
  border-radius: 999px;
  background: #f3f4f6;
  color: #4b5563;
  padding: 5px 10px;
  font-size: 12px;
  font-weight: 700;
}

.assertion-pill.passed {
  background: #dcfce7;
  color: #166534;
}

.assertion-pill.failed {
  background: #fee2e2;
  color: #991b1b;
}

.result-block {
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #fff;
}

.result-block summary {
  cursor: pointer;
  padding: 11px 12px;
  color: #111827;
  font-weight: 700;
}

.result-block pre {
  max-height: 420px;
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

.empty-result {
  display: flex;
  flex: 1;
  min-height: 420px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #6b7280;
  text-align: center;
}

.empty-result strong {
  color: #111827;
}

@media (max-width: 1100px) {
  .dashboard-layout {
    grid-template-columns: 1fr;
  }

  .control-panel,
  .result-panel {
    min-height: auto;
  }

  .result-meta {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .page-header,
  .result-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .result-meta {
    grid-template-columns: 1fr;
  }
}
</style>
