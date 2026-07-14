<template>
  <ResourcePage
    ref="resourcePageRef"
    title="API 管理"
    description="维护 API 增删改查、OpenAPI 导入、调试入口和接口基础信息。"
    api-path="/api-testing/interfaces"
    :actions="actions"
    :row-actions="rowActions"
    :fields="apiInterfaceFields"
    :columns="apiInterfaceColumns"
    :initial-params="apiSearchParams"
    @custom-action="handleCustomAction"
  >
    <template #search-before-button>
      <select v-model.number="apiFilter.projectId" class="api-filter-select" aria-label="按项目筛选 API">
        <option :value="0">全部项目</option>
        <option v-for="project in projects" :key="project.id" :value="project.id">
          {{ project.name }}
        </option>
      </select>
      <select v-model="apiFilter.method" class="api-filter-select method-filter" aria-label="按请求方法筛选 API">
        <option value="">全部方法</option>
        <option v-for="method in httpMethods" :key="method" :value="method">
          {{ method }}
        </option>
      </select>
      <input
        v-model.trim="apiFilter.path"
        class="api-path-filter"
        type="search"
        placeholder="筛选接口路径"
        aria-label="按接口路径筛选 API"
      />
    </template>
    <template #search-actions>
      <button type="button" @click="resetApiFilters">重置筛选</button>
    </template>
  </ResourcePage>

  <div v-if="importVisible" class="modal-backdrop" @click.self="closeImportDialog">
    <section class="modal-panel" role="dialog" aria-modal="true">
      <header class="modal-header">
        <h3>导入 OpenAPI</h3>
        <button class="modal-close" type="button" aria-label="关闭" @click="closeImportDialog">×</button>
      </header>

      <form class="modal-form" @submit.prevent="submitImport">
        <div class="form-grid">
          <label class="field full">
            <span>所属项目<b>*</b></span>
            <select v-model="importForm.projectId">
              <option value="">请选择项目</option>
              <option v-for="project in projects" :key="project.id" :value="String(project.id)">
                {{ project.name }}
              </option>
            </select>
          </label>

          <label class="field full">
            <span>导入来源<b>*</b></span>
            <select v-model="importForm.sourceType">
              <option value="file">上传 JSON 文件</option>
              <option value="url">输入 URL 地址</option>
            </select>
          </label>

          <label v-if="importForm.sourceType === 'file'" class="field full">
            <span>OpenAPI JSON 文件<b>*</b></span>
            <input type="file" accept=".json,application/json" @change="handleFileChange" />
          </label>

          <label v-if="importForm.sourceType === 'url'" class="field full">
            <span>OpenAPI URL 地址<b>*</b></span>
            <input v-model.trim="importForm.url" type="url" placeholder="例如：https://example.com/openapi.json" />
          </label>

          <label class="field full checkbox-line">
            <span>导入方式</span>
            <span class="checkbox-field">
              <input v-model="importForm.overwrite" type="checkbox" />
              <small>覆盖该项目原有 API 接口和字段信息</small>
            </span>
          </label>
        </div>

        <p v-if="importError" class="form-error">{{ importError }}</p>

        <section v-if="importTask" class="result-panel">
          <h4>任务状态</h4>
          <div class="result-grid">
            <span>任务 ID</span>
            <strong>{{ importTask.id }}</strong>
            <span>状态</span>
            <strong>{{ statusText(importTask.status) }}</strong>
            <span>进度</span>
            <strong>{{ importTask.data.progress || '-' }}</strong>
            <span>来源</span>
            <strong>{{ importTask.data.source || '-' }}</strong>
          </div>
        </section>

        <section v-if="importResult" class="result-panel">
          <h4>导入详情</h4>
          <div class="result-grid">
            <span>项目 ID</span>
            <strong>{{ importResult.project_id }}</strong>
            <span>导入接口</span>
            <strong>{{ importResult.interface_count }} 个</strong>
            <span>导入字段</span>
            <strong>{{ importResult.field_count }} 个</strong>
            <span>覆盖导入</span>
            <strong>{{ importResult.overwrite ? '是' : '否' }}</strong>
          </div>
          <div class="result-list">
            <div v-for="item in importResult.interfaces" :key="item.id" class="result-row">
              <b>{{ item.method }}</b>
              <span>{{ item.path }}</span>
              <small>{{ item.name }} / 字段 {{ item.field_count }} 个</small>
            </div>
          </div>
        </section>

        <footer class="modal-actions">
          <button type="button" @click="closeImportDialog">关闭</button>
          <button type="submit" :disabled="importing">
            {{ importing ? '导入中...' : importForm.sourceType === 'url' ? '拉取并导入' : '上传并导入' }}
          </button>
        </footer>
      </form>
    </section>
  </div>

  <div v-if="caseVisible" class="modal-backdrop" @click.self="closeCaseDialog">
    <section class="modal-panel case-modal" role="dialog" aria-modal="true">
      <header class="modal-header">
        <h3>生成 API 用例</h3>
        <button class="modal-close" type="button" aria-label="关闭" @click="closeCaseDialog">×</button>
      </header>

      <form class="modal-form" @submit.prevent="saveCaseDraft">
        <div class="result-panel" v-if="selectedInterface">
          <h4>{{ selectedInterface.name }}</h4>
          <div class="result-grid">
            <span>接口 ID</span>
            <strong>{{ selectedInterface.id }}</strong>
            <span>请求方法</span>
            <strong>{{ selectedInterface.data.method || '-' }}</strong>
            <span>接口路径</span>
            <strong>{{ selectedInterface.data.path || '-' }}</strong>
          </div>
        </div>

        <label class="field full">
          <span>正常用例 JSON<b>*</b></span>
          <textarea v-model="caseJsonText" class="json-editor" rows="14" spellcheck="false"></textarea>
        </label>

        <section class="strategy-panel">
          <div class="strategy-header">
            <strong>用例策略</strong>
            <small>可多选，用于后续批量扩展异常、边界、安全等用例</small>
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
          <p v-if="!strategies.length" class="muted-text">暂无策略，请先在用例知识库初始化或新增策略。</p>
        </section>

        <p v-if="caseError" class="form-error">{{ caseError }}</p>

        <footer class="modal-actions">
          <button type="button" @click="closeCaseDialog">取消</button>
          <button type="submit" :disabled="caseSaving">{{ caseSaving ? '保存中...' : '保存到用例草稿' }}</button>
        </footer>
      </form>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  createResource,
  getOpenApiImportTask,
  importOpenApiFile,
  importOpenApiUrl,
  listProjectOptions,
  listResources,
  OpenApiImportTask,
  OpenApiImportResult,
  ProjectOption,
  ResourceItem
} from '../../api/http'
import ResourcePage from '../../components/ResourcePage.vue'
import { apiInterfaceColumns, apiInterfaceFields } from '../../resourceSchemas'
import type { PageAction } from '../../types/page-actions'

const actions: PageAction[] = [
  {
    label: '导入 OpenAPI',
    path: '',
    type: 'custom',
    name: 'openapi-import'
  }
]

const rowActions: PageAction[] = [
  {
    label: '字段',
    path: '/api/fields',
    type: 'route',
    payload: {
      interface_id: '$id',
      project_id: '$project_id'
    }
  },
  {
    label: '用例',
    path: '',
    type: 'custom',
    name: 'case-generate'
  }
]

const resourcePageRef = ref<{ load: () => Promise<void> } | null>(null)
const importVisible = ref(false)
const importing = ref(false)
const importError = ref('')
const importTask = ref<OpenApiImportTask | null>(null)
const importResult = ref<OpenApiImportResult | null>(null)
const projects = ref<ProjectOption[]>([])
const importForm = ref({
  projectId: '',
  sourceType: 'file' as 'file' | 'url',
  overwrite: true,
  file: null as File | null,
  url: ''
})
const caseVisible = ref(false)
const caseSaving = ref(false)
const caseError = ref('')
const selectedInterface = ref<ResourceItem | null>(null)
const caseJsonText = ref('')
const strategies = ref<ResourceItem[]>([])
const selectedStrategyIds = ref<number[]>([])
const RESOURCE_FETCH_PAGE_SIZE = 200
const httpMethods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']
const apiFilter = ref({
  projectId: 0,
  method: '',
  path: ''
})

const apiSearchParams = computed<Record<string, unknown>>(() => {
  const params: Record<string, unknown> = {}
  if (apiFilter.value.projectId) {
    params.project_id = apiFilter.value.projectId
  }
  if (apiFilter.value.method) {
    params.method = apiFilter.value.method
  }
  if (apiFilter.value.path) {
    params.path = apiFilter.value.path
  }
  return params
})

onMounted(async () => {
  projects.value = await listProjectOptions()
})

async function handleCustomAction(action: PageAction, item?: ResourceItem) {
  if (action.name === 'case-generate' && item) {
    await openCaseDialog(item)
    return
  }
  await openImportDialog()
}

async function openImportDialog() {
  importError.value = ''
  importTask.value = null
  importResult.value = null
  importForm.value = { projectId: '', sourceType: 'file', overwrite: true, file: null, url: '' }
  if (!projects.value.length) {
    projects.value = await listProjectOptions()
  }
  importVisible.value = true
}

async function resetApiFilters() {
  apiFilter.value = {
    projectId: 0,
    method: '',
    path: ''
  }
  await resourcePageRef.value?.load()
}

function closeImportDialog() {
  if (importing.value) {
    return
  }
  importVisible.value = false
}

function handleFileChange(event: Event) {
  const files = (event.target as HTMLInputElement).files
  importForm.value.file = files?.[0] || null
}

async function submitImport() {
  importError.value = ''
  importTask.value = null
  importResult.value = null
  const projectId = Number(importForm.value.projectId)
  if (!projectId) {
    importError.value = '请选择项目'
    return
  }
  if (importForm.value.sourceType === 'file' && !importForm.value.file) {
    importError.value = '请上传 OpenAPI JSON 文件'
    return
  }
  if (importForm.value.sourceType === 'url' && !importForm.value.url) {
    importError.value = '请输入 OpenAPI URL 地址'
    return
  }

  importing.value = true
  try {
    importTask.value = importForm.value.sourceType === 'url'
      ? await importOpenApiUrl(projectId, importForm.value.url, importForm.value.overwrite)
      : await importOpenApiFile(projectId, importForm.value.file as File, importForm.value.overwrite)
    await pollImportTask(importTask.value.id)
  } catch (error) {
    importError.value = getErrorMessage(error)
  } finally {
    importing.value = false
  }
}

async function pollImportTask(taskId: number) {
  for (let index = 0; index < 360; index += 1) {
    await sleep(1000)
    importTask.value = await getOpenApiImportTask(taskId)
    if (importTask.value.status === 'success') {
      importResult.value = importTask.value.data.result || null
      await resourcePageRef.value?.load()
      return
    }
    if (importTask.value.status === 'failed') {
      importError.value = importTask.value.data.error || '导入失败'
      return
    }
  }
  importError.value = '导入仍在执行，请稍后刷新查看任务状态'
}

function sleep(ms: number) {
  return new Promise(resolve => window.setTimeout(resolve, ms))
}

function statusText(status: string) {
  const labels: Record<string, string> = {
    queued: '等待中',
    running: '导入中',
    success: '成功',
    failed: '失败',
    active: '启用',
    draft: '草稿',
    disabled: '停用',
    archived: '归档',
    accepted: '已采纳',
    rejected: '已驳回',
    pending: '待处理',
    cancelled: '已取消',
    canceled: '已取消',
    error: '异常'
  }
  return labels[status] || '未知状态'
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
  return error instanceof Error ? error.message : '导入失败'
}

async function openCaseDialog(item: ResourceItem) {
  caseError.value = ''
  selectedInterface.value = item
  selectedStrategyIds.value = []
  caseJsonText.value = ''
  caseVisible.value = true
  try {
    const [fields, strategyItems] = await Promise.all([
      listAllResourceItems('/api-testing/fields', { interface_id: item.id }),
      listAllResourceItems('/project-knowledge')
    ])
    strategies.value = strategyItems.filter(isCaseStrategy)
    selectedStrategyIds.value = strategies.value
      .filter(strategy => strategy.data.domain === 'API' || strategy.data.domain === 'COMMON')
      .slice(0, 3)
      .map(strategy => strategy.id)
    caseJsonText.value = JSON.stringify(buildNormalCaseExampleJson(fields), null, 2)
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
  if (!selectedInterface.value) {
    caseError.value = '请选择接口'
    return
  }
  let caseJson: Record<string, unknown>
  try {
    caseJson = JSON.parse(caseJsonText.value) as Record<string, unknown>
  } catch {
    caseError.value = '正常用例 JSON 不是合法 JSON'
    return
  }
  const draftJson = buildCaseDraftJson(selectedInterface.value, caseJson)
  const assertions = caseAssertions(draftJson)
  const cleanDraftJson = withoutCaseMeta(draftJson)

  caseSaving.value = true
  try {
    await createResource('/api-testing/case-drafts', {
      name: String(cleanDraftJson.name || `[正常] ${selectedInterface.value.name}`),
      project_id: selectedInterface.value.project_id,
      source_id: selectedInterface.value.id,
      status: 'draft',
      case_json: cleanDraftJson,
      data: cleanDraftJson,
      assertions,
      strategy_ids: selectedStrategyIds.value
    })
    caseVisible.value = false
  } catch (error) {
    caseError.value = getErrorMessage(error)
  } finally {
    caseSaving.value = false
  }
}

function buildNormalCaseExampleJson(fields: ResourceItem[]) {
  const result: Record<string, unknown> = {}
  for (const field of fields) {
    const data = field.data || {}
    const fieldName = String(data.name || field.name)
    result[fieldName] = exampleValue(data, fieldName)
  }
  return result
}

function buildCaseDraftJson(api: ResourceItem, values: Record<string, unknown>): Record<string, unknown> {
  const method = String(api.data.method || 'GET')
  const path = String(api.data.path || api.name)
  return {
    name: `[正常] ${method} ${path}`,
    case_type: 'API',
    category: 'normal',
    priority: 'P1',
    method,
    path,
    params: values
  }
}

function caseAssertions(caseJson: Record<string, unknown>) {
  const assertions = caseJson.assertions
  return Array.isArray(assertions)
    ? assertions.filter((item): item is Record<string, unknown> => isRecord(item))
    : [
        { type: 'status', expected: 200 },
        { type: 'response_time', operator: '<=', expected: 3000 }
      ]
}

function withoutCaseMeta(caseJson: Record<string, unknown>) {
  const { assertions, strategies, strategy, strategy_ids, ...rest } = caseJson
  void assertions
  void strategies
  void strategy
  void strategy_ids
  return rest
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function exampleValue(data: Record<string, unknown>, fieldName: string) {
  if (data.example != null && data.example !== '') {
    return data.example
  }
  if (data.default_value != null && data.default_value !== '') {
    return data.default_value
  }
  const type = String(data.field_type || data.type || 'string')
  if (type === 'integer') {
    return Math.floor(Math.random() * 9000) + 1000
  }
  if (type === 'number') {
    return Number((Math.random() * 1000).toFixed(2))
  }
  if (type === 'boolean') {
    return Math.random() > 0.5
  }
  if (type === 'array') {
    return [`${fieldName}_${Date.now().toString(36)}`]
  }
  if (type === 'object') {
    return {}
  }
  return `${fieldName}_${Math.random().toString(36).slice(2, 8)}`
}

function isCaseStrategy(item: ResourceItem) {
  const domain = item.data.domain
  const kind = item.data.kind
  return (domain === 'API' || domain === 'COMMON') && (kind === 'case_template' || kind === 'design_strategy')
}
</script>

<style scoped>
.api-filter-select,
.api-path-filter {
  flex: 0 0 180px;
  width: 180px;
  height: 34px;
  min-width: 128px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  color: #111827;
  padding: 0 10px;
}

.method-filter {
  flex-basis: 120px;
  width: 120px;
  min-width: 108px;
}

.api-path-filter {
  flex-basis: 220px;
  width: 220px;
}

@media (max-width: 720px) {
  .api-filter-select,
  .api-path-filter {
    width: 100%;
    min-width: 0;
  }
}
</style>
