<template>
  <div v-if="visible" class="modal-backdrop" @click.self="requestClose">
    <section class="modal-panel" role="dialog" aria-modal="true" aria-labelledby="openapi-generator-title">
      <header class="modal-header">
        <h3 id="openapi-generator-title">从 OpenAPI 生成用例</h3>
        <button class="modal-close" type="button" aria-label="关闭" @click="requestClose">×</button>
      </header>

      <div class="modal-body">
        <div :class="['filter-grid', { 'is-interface-scoped': hasFixedInterfaceScope }]">
          <label class="field project-field">
            <span>项目<b>*</b></span>
            <select v-model.number="projectId" :disabled="busy || Boolean(preview) || hasLockedScope" @change="handleProjectChange">
              <option :value="0">请选择项目</option>
              <option v-for="project in projects" :key="project.id" :value="project.id">{{ project.name }}</option>
            </select>
          </label>

          <div v-if="hasFixedInterfaceScope" class="field scope-field">
            <span>生成范围</span>
            <strong>{{ interfaces[0]?.name || '当前 API' }}</strong>
          </div>

          <label v-if="!hasFixedInterfaceScope" class="field method-field">
            <span>请求方法</span>
            <select v-model="methodFilter" :disabled="busy || Boolean(preview)" @change="searchInterfaces">
              <option value="">全部方法</option>
              <option v-for="method in httpMethods" :key="method" :value="method">{{ method }}</option>
            </select>
          </label>

          <label v-if="!hasFixedInterfaceScope" class="field">
            <span>接口名称/路径</span>
            <input
              v-model.trim="keyword"
              :disabled="busy || Boolean(preview)"
              type="search"
              placeholder="搜索接口名称"
              @keyup.enter="searchInterfaces"
            />
          </label>

          <label v-if="!hasFixedInterfaceScope" class="field">
            <span>接口路径</span>
            <input
              v-model.trim="pathFilter"
              :disabled="busy || Boolean(preview)"
              type="search"
              placeholder="例如 /users/{id}"
              @keyup.enter="searchInterfaces"
            />
          </label>

          <button v-if="!hasFixedInterfaceScope" class="query-button" type="button" :disabled="loadingInterfaces || busy || Boolean(preview)" @click="searchInterfaces">
            {{ loadingInterfaces ? '查询中...' : '查询' }}
          </button>
        </div>

        <div v-if="snapshot" class="snapshot-strip">
          <strong>OpenAPI {{ snapshot.data.openapi_version || '-' }}</strong>
          <span v-if="hasFixedInterfaceScope">接口：{{ interfaces[0]?.name || '当前 API' }}</span>
          <span v-if="props.initialModuleId">模块：{{ scopeModuleLabel }}</span>
          <span>{{ snapshot.data.operation_count || 0 }} 个操作</span>
          <code>{{ shortHash(snapshot.data.schema_hash) }}</code>
          <span>{{ snapshot.data.source || snapshot.data.source_type || '-' }}</span>
        </div>

        <div class="interface-table-wrap">
          <table>
            <thead>
              <tr>
                <th class="check-column">
                  <input
                    type="checkbox"
                    :checked="allCurrentPageChecked"
                    :disabled="Boolean(preview)"
                    aria-label="选择当前页接口"
                    @change="toggleCurrentPage"
                  />
                </th>
                <th class="method-column">方法</th>
                <th>接口路径</th>
                <th>接口名称</th>
                <th>模块</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="api in interfaces" :key="api.id">
                <td>
                  <input
                    type="checkbox"
                    :checked="selectedInterfaceIds.includes(api.id)"
                    :disabled="Boolean(preview)"
                    :aria-label="`选择接口 ${api.name}`"
                    @change="toggleInterface(api.id, $event)"
                  />
                </td>
                <td><strong class="method-text">{{ formatValue(api.data.method) }}</strong></td>
                <td class="path-cell">{{ formatValue(api.data.path) }}</td>
                <td>{{ api.name }}</td>
                <td>{{ formatValue(api.data.module) }}</td>
              </tr>
              <tr v-if="!interfaces.length">
                <td colspan="5" class="empty-cell">{{ loadingInterfaces ? '接口加载中...' : '暂无 API 接口' }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <footer class="table-footer">
          <span>已选择 {{ selectedInterfaceIds.length }} 个接口</span>
          <div class="pager">
            <button type="button" :disabled="currentPage <= 1 || loadingInterfaces || Boolean(preview)" @click="goToPage(currentPage - 1)">上一页</button>
            <span>第 {{ currentPage }} / {{ totalPages }} 页</span>
            <button type="button" :disabled="currentPage >= totalPages || loadingInterfaces || Boolean(preview)" @click="goToPage(currentPage + 1)">下一页</button>
          </div>
        </footer>

        <fieldset class="strategy-panel" :disabled="busy || Boolean(preview)">
          <legend>OpenAPI 生成策略</legend>
          <label v-for="option in generationStrategyOptions" :key="option.value" class="strategy-option">
            <input v-model="selectedGenerationStrategies" type="checkbox" :value="option.value" @change="invalidatePreview" />
            <span>
              <b>{{ option.label }}</b>
              <small>{{ option.hint }}</small>
            </span>
          </label>
        </fieldset>

        <section class="knowledge-panel">
          <div class="knowledge-header">
            <strong>附加知识库策略</strong>
            <button type="button" :disabled="loadingStrategies || busy || Boolean(preview)" @click="toggleAllStrategies">
              {{ allStrategiesChecked ? '取消全选' : '全选' }}
            </button>
          </div>
          <div v-if="strategies.length" class="knowledge-list">
            <label v-for="strategyItem in strategies" :key="strategyItem.id" class="knowledge-option">
              <input
                v-model="selectedStrategyIds"
                type="checkbox"
                :value="strategyItem.id"
                :disabled="busy || Boolean(preview)"
                @change="invalidatePreview"
              />
              <span>
                <b>{{ strategyItem.name }}</b>
                <small>{{ strategyMeta(strategyItem) }}</small>
              </span>
            </label>
          </div>
          <p v-else class="empty-strategy">{{ loadingStrategies ? '策略加载中...' : '暂无适用的 API 知识库策略' }}</p>
        </section>

        <section v-if="preview" class="preview-panel">
          <header class="preview-header">
            <div>
              <strong>预览 {{ preview.total }} 条</strong>
              <span>新增 {{ preview.summary.new }} · 更新 {{ preview.summary.update }} · 无变化 {{ preview.summary.unchanged }}</span>
            </div>
            <label>
              <input type="checkbox" :checked="allMutablePreviewChecked" @change="toggleAllPreview" />
              选择可生成项
            </label>
          </header>
          <p v-if="preview.truncated" class="preview-warning">已达到单次 {{ MAX_CASES }} 条上限，请缩小接口范围后继续。</p>
          <div class="preview-table-wrap">
            <table>
              <thead>
                <tr>
                  <th class="check-column"></th>
                  <th class="action-column">处理</th>
                  <th>场景</th>
                  <th>接口</th>
                  <th>字段</th>
                  <th>预期</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in preview.items" :key="item.fingerprint">
                  <td>
                    <input
                      type="checkbox"
                      :checked="selectedFingerprints.includes(item.fingerprint)"
                      :disabled="item.action === 'unchanged' || generating"
                      :aria-label="`选择用例 ${item.name}`"
                      @change="togglePreviewItem(item.fingerprint, $event)"
                    />
                  </td>
                  <td><span class="action-text" :class="`is-${item.action}`">{{ actionLabel(item.action) }}</span></td>
                  <td>{{ strategyLabel(item.strategy) }}</td>
                  <td class="path-cell"><b>{{ item.method }}</b> {{ item.path }}</td>
                  <td>{{ item.field || '-' }}</td>
                  <td>{{ assertionSummary(item.assertions) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <p v-if="resultMessage" class="result-message">{{ resultMessage }}</p>
        <p v-if="errorMessage" class="form-error">{{ errorMessage }}</p>
      </div>

      <footer class="modal-actions">
        <button type="button" :disabled="busy" @click="requestClose">关闭</button>
        <button v-if="preview" type="button" :disabled="busy" @click="clearPreview">返回配置</button>
        <button v-if="!preview" class="primary" type="button" :disabled="!canPreview" @click="previewCases">
          {{ previewLoading ? '预览生成中...' : '预览用例' }}
        </button>
        <button v-else class="primary" type="button" :disabled="!canGenerate" @click="generateDrafts">
          {{ generating ? '保存中...' : `生成选中草稿 (${selectedFingerprints.length})` }}
        </button>
      </footer>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { getResource, listProjectOptions, listResources, resolveDefaultProjectId } from '../../api/http'
import {
  generateOpenApiCases,
  getLatestOpenApiSchema,
  previewOpenApiCases
} from '../../services/openapi-schema.service'
import type {
  OpenApiCaseGenerationPayload,
  OpenApiCaseGenerationResult,
  OpenApiCasePreview,
  OpenApiGenerationAction,
  OpenApiGenerationStrategy,
  OpenApiSchemaSnapshot
} from '../../types/openapi-schema'
import type { ProjectOption, ResourceItem } from '../../types/resource'

const props = defineProps<{
  visible: boolean
  initialProjectId?: number
  initialInterfaceIds?: number[]
  initialModuleId?: number
  initialModuleName?: string
}>()

const emit = defineEmits<{
  close: []
  generated: [result: OpenApiCaseGenerationResult]
}>()

const PAGE_SIZE = 10
const MAX_CASES = 500
const httpMethods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']
const generationStrategyOptions: Array<{ value: OpenApiGenerationStrategy; label: string; hint: string }> = [
  { value: 'normal', label: '正常值', hint: '示例、默认值和约束内数据' },
  { value: 'required', label: '必填缺失', hint: '逐个移除必填参数' },
  { value: 'boundary', label: '边界值', hint: '数值、长度和数组边界' },
  { value: 'enum', label: '枚举值', hint: '合法枚举与非法枚举' },
  { value: 'format', label: '格式错误', hint: '日期、邮箱、UUID、URI 等' },
  { value: 'type', label: '类型错误', hint: '替换为不匹配的数据类型' },
  { value: 'auth', label: '未鉴权', hint: 'Schema 声明安全要求时生成' }
]

const projects = ref<ProjectOption[]>([])
const interfaces = ref<ResourceItem[]>([])
const strategies = ref<ResourceItem[]>([])
const snapshot = ref<OpenApiSchemaSnapshot | null>(null)
const preview = ref<OpenApiCasePreview | null>(null)
const projectId = ref(0)
const methodFilter = ref('')
const keyword = ref('')
const pathFilter = ref('')
const selectedInterfaceIds = ref<number[]>([])
const selectedStrategyIds = ref<number[]>([])
const selectedGenerationStrategies = ref<OpenApiGenerationStrategy[]>(generationStrategyOptions.map(item => item.value))
const selectedFingerprints = ref<string[]>([])
const currentPage = ref(1)
const total = ref(0)
const loadingProjects = ref(false)
const loadingInterfaces = ref(false)
const loadingStrategies = ref(false)
const loadingSnapshot = ref(false)
const previewLoading = ref(false)
const generating = ref(false)
const errorMessage = ref('')
const resultMessage = ref('')

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))
const busy = computed(() => (
  loadingProjects.value
  || loadingInterfaces.value
  || loadingStrategies.value
  || loadingSnapshot.value
  || previewLoading.value
  || generating.value
))
const allCurrentPageChecked = computed(() => (
  interfaces.value.length > 0 && interfaces.value.every(api => selectedInterfaceIds.value.includes(api.id))
))
const allStrategiesChecked = computed(() => (
  strategies.value.length > 0 && strategies.value.every(strategy => selectedStrategyIds.value.includes(strategy.id))
))
const mutablePreviewFingerprints = computed(() => (
  preview.value?.items.filter(item => item.action !== 'unchanged').map(item => item.fingerprint) || []
))
const allMutablePreviewChecked = computed(() => (
  mutablePreviewFingerprints.value.length > 0
  && mutablePreviewFingerprints.value.every(value => selectedFingerprints.value.includes(value))
))
const canPreview = computed(() => (
  !busy.value
  && Boolean(snapshot.value)
  && projectId.value > 0
  && selectedInterfaceIds.value.length > 0
  && selectedGenerationStrategies.value.length > 0
))
const canGenerate = computed(() => !busy.value && selectedFingerprints.value.length > 0)
const fixedInterfaceIds = computed(() => uniqueIds(props.initialInterfaceIds || []))
const hasFixedInterfaceScope = computed(() => fixedInterfaceIds.value.length > 0)
const hasLockedScope = computed(() => hasFixedInterfaceScope.value || Boolean(props.initialModuleId))
const scopeModuleLabel = computed(() => (
  String(props.initialModuleName || '当前模块')
))

watch(() => props.visible, async visible => {
  if (!visible) return
  resetDialog()
  await loadProjects()
  const requestedProject = Number(props.initialProjectId || 0)
  projectId.value = projects.value.some(item => item.id === requestedProject)
    ? requestedProject
    : resolveDefaultProjectId(projects.value)
  selectedInterfaceIds.value = [...fixedInterfaceIds.value]
  await Promise.all([loadInterfaces(), loadStrategies(), loadSnapshot()])
  if (props.initialModuleId && !selectedInterfaceIds.value.length) {
    await selectScopedModuleInterfaces()
  }
})

function resetDialog() {
  methodFilter.value = ''
  keyword.value = ''
  pathFilter.value = ''
  selectedInterfaceIds.value = []
  selectedStrategyIds.value = []
  selectedGenerationStrategies.value = generationStrategyOptions.map(item => item.value)
  selectedFingerprints.value = []
  currentPage.value = 1
  total.value = 0
  interfaces.value = []
  strategies.value = []
  snapshot.value = null
  preview.value = null
  errorMessage.value = ''
  resultMessage.value = ''
}

async function loadProjects() {
  if (projects.value.length) return
  loadingProjects.value = true
  try {
    projects.value = await listProjectOptions()
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    loadingProjects.value = false
  }
}

async function loadSnapshot() {
  snapshot.value = null
  if (!projectId.value) return
  loadingSnapshot.value = true
  try {
    snapshot.value = await getLatestOpenApiSchema(projectId.value)
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    loadingSnapshot.value = false
  }
}

async function loadInterfaces() {
  if (!projectId.value) {
    interfaces.value = []
    total.value = 0
    return
  }
  loadingInterfaces.value = true
  errorMessage.value = ''
  try {
    if (hasFixedInterfaceScope.value) {
      interfaces.value = await Promise.all(
        fixedInterfaceIds.value.map(interfaceId => getResource('/api-testing/interfaces', interfaceId))
      )
      total.value = interfaces.value.length
      currentPage.value = 1
      return
    }
    const result = await listResources('/api-testing/interfaces', {
      project_id: projectId.value,
      keyword: keyword.value,
      method: methodFilter.value,
      path: pathFilter.value,
      module_id: props.initialModuleId || undefined,
      page: currentPage.value,
      pageSize: PAGE_SIZE
    })
    interfaces.value = result.items
    total.value = result.total
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    loadingInterfaces.value = false
  }
}

async function loadStrategies() {
  strategies.value = []
  selectedStrategyIds.value = []
  if (!projectId.value) return
  loadingStrategies.value = true
  try {
    const items = await listAllResourceItems('/project-knowledge')
    strategies.value = items.filter(isApiStrategy).filter(strategy => (
      strategy.project_id == null || strategy.project_id === projectId.value
    ))
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    loadingStrategies.value = false
  }
}

async function listAllResourceItems(path: string, params: Record<string, unknown> = {}) {
  const firstPage = await listResources(path, { ...params, page: 1, pageSize: 200 })
  const items = [...firstPage.items]
  const totalPageCount = Math.ceil(firstPage.total / firstPage.pageSize)
  for (let page = 2; page <= totalPageCount; page += 1) {
    const nextPage = await listResources(path, { ...params, page, pageSize: 200 })
    items.push(...nextPage.items)
  }
  return items
}

async function selectScopedModuleInterfaces() {
  loadingInterfaces.value = true
  try {
    const items = await listAllResourceItems('/api-testing/interfaces', {
      project_id: projectId.value,
      module_id: props.initialModuleId
    })
    if (items.length > 500) {
      errorMessage.value = '当前模块超过 500 个接口，请手动分批选择后生成'
      return
    }
    selectedInterfaceIds.value = items.map(item => item.id)
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    loadingInterfaces.value = false
  }
}

async function handleProjectChange() {
  selectedInterfaceIds.value = []
  currentPage.value = 1
  invalidatePreview()
  await Promise.all([loadInterfaces(), loadStrategies(), loadSnapshot()])
}

async function searchInterfaces() {
  currentPage.value = 1
  await loadInterfaces()
}

async function goToPage(page: number) {
  currentPage.value = Math.min(Math.max(page, 1), totalPages.value)
  await loadInterfaces()
}

function toggleInterface(interfaceId: number, event: Event) {
  const checked = (event.target as HTMLInputElement).checked
  selectedInterfaceIds.value = checked
    ? uniqueIds([...selectedInterfaceIds.value, interfaceId])
    : selectedInterfaceIds.value.filter(id => id !== interfaceId)
  invalidatePreview()
}

function toggleCurrentPage(event: Event) {
  const checked = (event.target as HTMLInputElement).checked
  const currentIds = interfaces.value.map(api => api.id)
  selectedInterfaceIds.value = checked
    ? uniqueIds([...selectedInterfaceIds.value, ...currentIds])
    : selectedInterfaceIds.value.filter(id => !currentIds.includes(id))
  invalidatePreview()
}

function toggleAllStrategies() {
  selectedStrategyIds.value = allStrategiesChecked.value ? [] : strategies.value.map(strategy => strategy.id)
  invalidatePreview()
}

async function previewCases() {
  if (!canPreview.value) return
  previewLoading.value = true
  errorMessage.value = ''
  resultMessage.value = ''
  try {
    preview.value = await previewOpenApiCases(generationPayload())
    selectedFingerprints.value = preview.value.items
      .filter(item => item.action !== 'unchanged')
      .map(item => item.fingerprint)
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    previewLoading.value = false
  }
}

async function generateDrafts() {
  if (!canGenerate.value) return
  generating.value = true
  errorMessage.value = ''
  resultMessage.value = ''
  try {
    const result = await generateOpenApiCases({
      ...generationPayload(),
      selected_fingerprints: selectedFingerprints.value
    })
    resultMessage.value = `已新增 ${result.created_count} 条、更新 ${result.updated_count} 条，跳过 ${result.skipped_count} 条`
    const selected = new Set(selectedFingerprints.value)
    if (preview.value) {
      preview.value.items.forEach(item => {
        if (selected.has(item.fingerprint)) item.action = 'unchanged'
      })
      preview.value.summary = {
        new: preview.value.items.filter(item => item.action === 'new').length,
        update: preview.value.items.filter(item => item.action === 'update').length,
        unchanged: preview.value.items.filter(item => item.action === 'unchanged').length
      }
    }
    selectedFingerprints.value = []
    emit('generated', result)
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    generating.value = false
  }
}

function generationPayload(): OpenApiCaseGenerationPayload {
  return {
    project_id: projectId.value,
    snapshot_id: snapshot.value?.id,
    source_ids: selectedInterfaceIds.value,
    strategies: selectedGenerationStrategies.value,
    strategy_ids: selectedStrategyIds.value,
    max_cases: MAX_CASES
  }
}

function togglePreviewItem(fingerprint: string, event: Event) {
  const checked = (event.target as HTMLInputElement).checked
  selectedFingerprints.value = checked
    ? Array.from(new Set([...selectedFingerprints.value, fingerprint]))
    : selectedFingerprints.value.filter(item => item !== fingerprint)
}

function toggleAllPreview() {
  selectedFingerprints.value = allMutablePreviewChecked.value ? [] : [...mutablePreviewFingerprints.value]
}

function clearPreview() {
  preview.value = null
  selectedFingerprints.value = []
  resultMessage.value = ''
}

function invalidatePreview() {
  if (preview.value) clearPreview()
}

function requestClose() {
  if (!busy.value) emit('close')
}

function actionLabel(value: OpenApiGenerationAction) {
  return ({ new: '新增', update: '更新', unchanged: '无变化' } as Record<OpenApiGenerationAction, string>)[value]
}

function strategyLabel(value: string) {
  return generationStrategyOptions.find(item => item.value === value)?.label || (value === 'knowledge' ? '知识库' : value)
}

function assertionSummary(assertions: Array<Record<string, unknown>>) {
  return assertions.map(item => {
    const expected = item.expected == null ? '' : ` ${JSON.stringify(item.expected)}`
    return `${String(item.type || '断言')}${expected}`
  }).join('；') || '-'
}

function uniqueIds(values: number[]) {
  return Array.from(new Set(values.map(Number).filter(value => Number.isInteger(value) && value > 0)))
}

function shortHash(value: unknown) {
  return String(value || '-').slice(0, 12)
}

function formatValue(value: unknown) {
  return value == null || value === '' ? '-' : String(value)
}

function isApiStrategy(item: ResourceItem) {
  const domain = String(item.data.domain || 'COMMON').toUpperCase()
  const kind = String(item.data.kind || '')
  return ['COMMON', 'API'].includes(domain) && ['case_template', 'design_strategy'].includes(kind)
}

function strategyMeta(item: ResourceItem) {
  return [formatValue(item.data.category), item.data.priority ? `优先级 ${item.data.priority}` : ''].filter(Boolean).join(' / ')
}

function getErrorMessage(error: unknown) {
  const data = (error as { response?: { data?: { message?: string; detail?: unknown } } }).response?.data
  if (data?.message) return data.message
  if (typeof data?.detail === 'string') return data.detail
  return error instanceof Error ? error.message : '生成用例失败'
}
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: grid;
  place-items: center;
  padding: 28px;
  background: rgb(15 23 42 / 54%);
}

.modal-panel {
  width: min(1120px, 100%);
  max-height: calc(100vh - 56px);
  overflow: auto;
  border: 1px solid #dbe3ef;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 24px 60px rgb(15 23 42 / 22%);
}

.modal-header,
.modal-actions,
.preview-header,
.knowledge-header,
.table-footer,
.snapshot-strip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.modal-header {
  border-bottom: 1px solid #e5e7eb;
  padding: 18px 20px;
}

.modal-header h3 {
  margin: 0;
  color: #111827;
  font-size: 18px;
}

.modal-close {
  border: 0;
  background: transparent;
  color: #64748b;
  font-size: 24px;
  line-height: 1;
  cursor: pointer;
}

.modal-body {
  display: grid;
  gap: 14px;
  padding: 18px 20px;
}

.filter-grid {
  display: grid;
  grid-template-columns: minmax(160px, 220px) 124px minmax(180px, 1fr) minmax(180px, 1fr) auto;
  align-items: end;
  gap: 12px;
}

.filter-grid.is-interface-scoped {
  grid-template-columns: minmax(160px, 220px) minmax(240px, 1fr);
}

.scope-field strong {
  display: flex;
  align-items: center;
  min-height: 38px;
  overflow: hidden;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #f8fafc;
  color: #111827;
  padding: 0 10px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.field {
  display: grid;
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
.field input,
.query-button {
  height: 38px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  color: #111827;
  font: inherit;
  padding: 0 10px;
}

.query-button,
.knowledge-header button,
.pager button,
.modal-actions button {
  cursor: pointer;
}

.snapshot-strip {
  justify-content: flex-start;
  min-height: 38px;
  border-left: 3px solid #0f766e;
  background: #f0fdfa;
  color: #334155;
  font-size: 13px;
  padding: 8px 12px;
}

.snapshot-strip code {
  color: #0f766e;
}

.interface-table-wrap,
.preview-table-wrap {
  overflow: auto;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
}

.interface-table-wrap table,
.preview-table-wrap table {
  width: 100%;
  min-width: 820px;
  border-collapse: collapse;
}

.interface-table-wrap th,
.interface-table-wrap td,
.preview-table-wrap th,
.preview-table-wrap td {
  border-bottom: 1px solid #edf1f7;
  color: #374151;
  font-size: 13px;
  padding: 10px 12px;
  text-align: left;
  vertical-align: top;
}

.interface-table-wrap th,
.preview-table-wrap th {
  background: #f8fafc;
  color: #111827;
  font-weight: 700;
}

.interface-table-wrap tr:last-child td,
.preview-table-wrap tr:last-child td {
  border-bottom: 0;
}

.check-column {
  width: 44px;
}

.method-column,
.action-column {
  width: 80px;
}

.method-text {
  color: #075985;
}

.path-cell {
  max-width: 360px;
  word-break: break-all;
}

.empty-cell {
  color: #6b7280;
  text-align: center;
}

.table-footer {
  color: #64748b;
  font-size: 13px;
}

.pager {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pager button,
.knowledge-header button,
.modal-actions button {
  min-height: 34px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  color: #374151;
  padding: 0 12px;
}

.strategy-panel {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 8px;
  min-width: 0;
  margin: 0;
  border: 1px solid #dbe3ef;
  border-radius: 6px;
  padding: 10px 12px 12px;
}

.strategy-panel legend {
  padding: 0 5px;
  color: #334155;
  font-size: 13px;
  font-weight: 700;
}

.strategy-option,
.knowledge-option {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  min-width: 0;
  color: #334155;
  font-size: 13px;
}

.strategy-option input,
.knowledge-option input {
  width: 16px;
  height: 16px;
  flex: 0 0 auto;
  margin-top: 3px;
}

.strategy-option > span,
.knowledge-option > span {
  min-width: 0;
  flex: 1 1 auto;
}

.strategy-option b,
.strategy-option small,
.knowledge-option b,
.knowledge-option small {
  display: block;
}

.strategy-option small,
.knowledge-option small,
.empty-strategy,
.preview-header span {
  margin-top: 3px;
  color: #64748b;
  font-size: 12px;
}

.knowledge-panel,
.preview-panel {
  display: grid;
  gap: 10px;
  border-top: 1px solid #e5e7eb;
  padding-top: 14px;
}

.knowledge-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 16px;
}

.empty-strategy,
.preview-warning,
.result-message,
.form-error {
  margin: 0;
  font-size: 13px;
}

.preview-header > div,
.preview-header strong,
.preview-header span {
  display: block;
}

.preview-table-wrap {
  max-height: 320px;
}

.action-text {
  font-weight: 700;
}

.action-text.is-new {
  color: #166534;
}

.action-text.is-update {
  color: #b45309;
}

.action-text.is-unchanged {
  color: #64748b;
}

.preview-warning {
  color: #b45309;
}

.result-message {
  color: #166534;
}

.form-error {
  color: #dc2626;
}

.modal-actions {
  justify-content: flex-end;
  border-top: 1px solid #e5e7eb;
  padding: 14px 20px;
}

.modal-actions button.primary {
  border-color: #2563eb;
  background: #2563eb;
  color: #fff;
}

button:disabled,
input:disabled,
select:disabled,
fieldset:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

@media (max-width: 860px) {
  .modal-backdrop {
    padding: 14px;
  }

  .filter-grid,
  .strategy-panel,
  .knowledge-list {
    grid-template-columns: 1fr;
  }

  .table-footer,
  .preview-header,
  .snapshot-strip {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
