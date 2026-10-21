<template>
  <section class="page">
    <div v-if="$slots['toolbar-top']" class="toolbar-top">
      <slot name="toolbar-top"></slot>
    </div>

    <div class="toolbar">
      <button v-if="allowCreate" type="button" @click="openCreate">新增</button>
      <input v-model="keyword" placeholder="搜索名称/说明" @keyup.enter="search" />
      <slot name="search-before-button"></slot>
      <button type="button" :disabled="listLoading" @click="search">查询</button>
      <slot name="search-actions"></slot>
      <button type="button" :disabled="!selectedIds.length || deleting || listLoading" @click="removeSelected">{{ deleting ? '删除中...' : '批量删除' }}</button>
      <button
        v-for="(action, index) in actions"
        :key="actionKey(action, index)"
        type="button"
        :disabled="actionRunning"
        @click="runAction(action, actionKey(action, index))"
      >
        {{ runningActionKey === actionKey(action, index) ? `${action.label}中...` : action.label }}
      </button>
    </div>

    <p v-if="loadError" role="alert">{{ loadError }} <button type="button" :disabled="listLoading" @click="load">重试</button></p>
    <p v-if="deleteError" role="alert">{{ deleteError }}</p>
    <div class="table-wrap" :aria-busy="listLoading || deleting">
      <table>
        <thead>
          <tr>
            <th class="check-column"><input type="checkbox" :checked="allChecked" :disabled="deleting" @change="toggleAll" /></th>
            <th v-for="column in visibleColumns" :key="column.key" :style="{ width: column.width }">{{ column.label }}</th>
            <th class="action-column">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="item in items"
            :key="item.id"
            :class="{ 'clickable-row': detailMode === 'case-draft' }"
            @click="handleRowClick(item, $event)"
          >
            <td><input v-model="selectedIds" type="checkbox" :value="item.id" :disabled="deleting" @click.stop /></td>
            <td v-for="column in visibleColumns" :key="column.key" class="table-cell">{{ formatCellValue(item, column.key) }}</td>
            <td class="row-actions">
              <button
                v-for="(action, index) in rowActions"
                :key="actionKey(action, index, item)"
                type="button"
                :class="{ active: isRowActionActive(action, item) }"
                :disabled="isRowActionRunning(action, index, item) || isRowActionDisabled(action, item)"
                :title="rowActionTitle(action, item)"
                @click.stop="runRowAction(action, item, actionKey(action, index, item))"
              >
                {{ runningActionKey === actionKey(action, index, item) ? `${action.label}中...` : action.label }}
              </button>
              <button v-if="detailMode === 'test-case'" type="button" @click.stop="openDetail(item)">查看</button>
              <button v-if="allowEdit && detailMode !== 'case-draft'" type="button" @click.stop="openEdit(item)">编辑</button>
              <button class="danger" type="button" :disabled="deleting || listLoading" @click.stop="remove(item.id)">删除</button>
            </td>
          </tr>
          <tr v-if="listLoading"><td class="empty-cell" :colspan="visibleColumns.length + 2">正在加载...</td></tr>
          <tr v-if="!listLoading && !loadError && !items.length">
            <td class="empty-cell" :colspan="visibleColumns.length + 2">暂无数据</td>
          </tr>
        </tbody>
      </table>
    </div>

    <CommonPagination
      :page="currentPage"
      :page-size="pageSize"
      :total="total"
      :message="message"
      :loading="listLoading || deleting"
      @change="handlePaginationChange"
    />

    <div v-if="operationToastVisible" class="operation-toast" role="status" aria-live="polite">
      <strong>{{ operationToastTitle }}</strong>
      <span>{{ operationToastMessage }}</span>
    </div>

    <div v-if="dialogVisible" class="modal-backdrop" @click.self="closeDialog">
      <button
        v-if="caseDraftDialogMode"
        type="button"
        class="case-draft-side-nav case-draft-side-nav-left"
        :disabled="!canSwitchCaseDraft(-1)"
        aria-label="上一个用例"
        @click="switchCaseDraftDetail(-1)"
      >‹</button>
      <section class="modal-panel" :class="{ 'web-case-draft-panel': isWebCaseDraftPage }" role="dialog" aria-modal="true">
        <header v-if="caseDraftDialogMode" class="modal-header case-draft-detail-header">
          <div class="case-draft-nav">
            <h3>{{ editingItem?.name || '用例草稿详情' }}</h3>
            <p>{{ caseDraftPositionText }}</p>
          </div>
          <div class="case-draft-header-actions">
            <button type="button" :disabled="!caseDraftCanReview || actionRunning" @click="acceptCurrentCaseDraft">采纳</button>
            <button type="button" :disabled="!caseDraftCanReview || actionRunning" @click="rejectCurrentCaseDraft">驳回</button>
            <button type="button" class="danger" :disabled="actionRunning || deleting" @click="deleteCurrentCaseDraft">删除</button>
            <button class="modal-close" type="button" aria-label="关闭" @click="closeDialog">×</button>
          </div>
        </header>
        <header v-else class="modal-header">
          <h3>{{ dialogTitle }}</h3>
          <button class="modal-close" type="button" aria-label="关闭" @click="closeDialog">×</button>
        </header>

        <form class="modal-form" @submit.prevent="submitForm">
          <div class="form-grid">
            <div
              v-for="field in visibleFields"
              :key="field.key"
              class="field"
              :class="{ full: field.full || field.type === 'textarea' || field.type === 'json', 'json-field-hidden': shouldHideJsonField(field) }"
            >
              <slot :name="`form-field-${field.key}`" :field="field" :values="formValues" :item="editingItem">
              <span>{{ field.label }}<b v-if="field.required">*</b></span>
              <textarea v-if="field.type === 'textarea'" v-model.trim="formValues[field.key]" :rows="field.rows || 3" :placeholder="field.placeholder"></textarea>
              <template v-else-if="field.type === 'json'">
                <WebDraftStepEditor v-if="isWebCaseDraftJsonField(field)" v-model="jsonValues[field.key]" />
                <textarea
                  v-if="!shouldHideJsonInput(field)"
                  v-model="jsonValues[field.key]"
                  class="json-editor"
                  :rows="field.rows || 8"
                  spellcheck="false"
                  :aria-label="field.label"
                  :placeholder="field.placeholder || '请输入 JSON'"
                ></textarea>
                <DynamicValueTools v-if="isCaseValueJsonField(field)" v-model="jsonValues[field.key]" :label="field.label" :variables="dynamicVariableDefinitions" />
              </template>
              <ApiSelect v-else-if="field.type === 'select' && field.remoteOptions?.path === '/api-testing/interfaces/options'"
                :model-value="formValues[field.key]" :options="getApiFieldOptions(field)" :label="field.label" :required="field.required" :loading="remoteOptionsLoading > 0"
                :placeholder="field.placeholder" @update:model-value="formValues[field.key] = $event || ''" @change="handleSelectChange(field)" />
              <select v-else-if="field.type === 'select'" v-model="formValues[field.key]" @change="handleSelectChange(field)">
                <option value="">{{ field.placeholder || '请选择' }}</option>
                <option v-for="option in getFieldOptions(field)" :key="String(option.value)" :value="option.value">{{ option.label }}</option>
              </select>
              <select
                v-else-if="field.type === 'multiselect'"
                v-model="multiSelectValues[field.key]"
                multiple
                :size="Math.min(Math.max(getFieldOptions(field).length, 3), 8)"
                @change="handleSelectChange(field)"
              >
                <option v-for="option in getFieldOptions(field)" :key="String(option.value)" :value="String(option.value)">{{ option.label }}</option>
              </select>
              <span v-else-if="field.type === 'checkbox'" class="checkbox-field">
                <input v-model="checkboxValues[field.key]" type="checkbox" />
                <small>{{ checkboxValues[field.key] ? '是' : '否' }}</small>
              </span>
              <DynamicValueInput v-else-if="field.key === 'data.default_value' || field.key === 'data.example'" :model-value="formValues[field.key]" :label="field.label" @update:model-value="formValues[field.key] = $event" />
              <input v-else v-model.trim="formValues[field.key]" :type="field.type === 'number' ? 'number' : 'text'" :placeholder="field.placeholder" />
              </slot>
            </div>
          </div>
          <label v-if="showJsonEditor && !hideExtraJsonEditor" class="field">
            <span>扩展数据 JSON</span>
            <textarea v-model="extraDataJson" class="json-editor" rows="8" spellcheck="false"></textarea>
          </label>
          <p v-if="formError" class="form-error">{{ formError }}</p>
          <footer class="modal-actions">
            <button type="button" @click="closeDialog">取消</button>
            <button type="submit" :disabled="saving || formBlocked">{{ saving ? '保存中...' : '保存' }}</button>
          </footer>
        </form>
      </section>
      <button
        v-if="caseDraftDialogMode"
        type="button"
        class="case-draft-side-nav case-draft-side-nav-right"
        :disabled="!canSwitchCaseDraft(1)"
        aria-label="下一个用例"
        @click="switchCaseDraftDetail(1)"
      >›</button>
    </div>

    <div v-if="resultVisible" class="modal-backdrop" @click.self="closeResultDialog">
      <section class="modal-panel execution-result-modal" role="dialog" aria-modal="true">
        <header class="modal-header">
          <h3>{{ resultTitle }}</h3>
          <button class="modal-close" type="button" aria-label="关闭" @click="closeResultDialog">×</button>
        </header>
        <div class="case-detail-content"><pre class="result-json">{{ stringifyJson(actionResult) }}</pre></div>
      </section>
    </div>

    <div v-if="detailVisible" class="modal-backdrop" @click.self="closeDetailDialog">
      <section class="modal-panel execution-result-modal" :class="{ 'api-evidence-modal': isApiTestCasePage }" role="dialog" aria-modal="true">
        <header class="modal-header">
          <h3>查看详情</h3>
          <button class="modal-close" type="button" aria-label="关闭" @click="closeDetailDialog">×</button>
        </header>
        <div v-if="detailItem" class="case-detail-content">
          <section class="case-detail-summary">
            <div>
              <span>用例名称</span>
              <strong>{{ detailItem.name }}</strong>
            </div>
            <div>
              <span>状态</span>
              <strong>{{ formatStatus(detailItem.status) }}</strong>
            </div>
            <div v-if="formatValue(readValue(detailItem, 'data.project_name')) !== '-'">
              <span>项目</span>
              <strong>{{ formatValue(readValue(detailItem, 'data.project_name')) }}</strong>
            </div>
            <div>
              <span>{{ caseSourceLabel(detailItem) }}</span>
              <strong>{{ caseSourceDisplay(detailItem) }}</strong>
            </div>
          </section>
          <WebCaseDetailContent v-if="isWebTestCasePage" :item="detailItem" />
          <ApiCaseDetailContent v-else-if="isApiTestCasePage" :item="detailItem" />
          <template v-else>
            <details open class="result-detail">
              <summary>用例 JSON 参数</summary>
              <pre>{{ stringifyJson(getCaseRequest(detailItem)) }}</pre>
            </details>
            <details class="result-detail">
              <summary>断言 JSON</summary>
              <pre>{{ stringifyJson(getCaseAssertions(detailItem)) }}</pre>
            </details>
            <details class="result-detail">
              <summary>策略信息</summary>
              <pre>{{ stringifyJson(getCaseStrategies(detailItem)) }}</pre>
            </details>
          </template>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  clearRemoteOptionsCache,
  createResource,
  listRemoteOptionsCached,
  listResources,
  postAction,
  updateResource
} from '../api/http'
import { defaultColumns, defaultFields } from '../resourceSchemas'
import type { PageAction } from '../types/page-actions'
import type { ResourceItem, ResourcePayload } from '../types/resource'
import type { ResourceColumn, ResourceField, ResourceOption } from '../types/resource-schema'
import CommonPagination from './common/CommonPagination.vue'
import ApiSelect from './common/ApiSelect.vue'
import DynamicValueInput from './common/DynamicValueInput.vue'
import DynamicValueTools from './common/DynamicValueTools.vue'
import ApiCaseDetailContent from './resource/ApiCaseDetailContent.vue'
import WebCaseDetailContent from './resource/WebCaseDetailContent.vue'
import WebDraftStepEditor from './resource/WebDraftStepEditor.vue'
import { useOperationToast } from './resource/useOperationToast'
import { useLatestRequest } from '../composables/useLatestRequest'
import { useResourceDeletion } from '../composables/useResourceDeletion'

type FormValue = string | number | null

const props = withDefaults(defineProps<{
  title: string
  description: string
  apiPath: string
  actions?: PageAction[]
  rowActions?: PageAction[]
  fields?: ResourceField[]
  columns?: ResourceColumn[]
  showJsonEditor?: boolean
  initialParams?: Record<string, unknown>
  searchParams?: Record<string, unknown>
  defaultValues?: Record<string, unknown>
  allowCreate?: boolean
  allowEdit?: boolean
  deferLoad?: boolean
  formBlocked?: boolean
  detailMode?: 'none' | 'test-case' | 'case-draft'
}>(), {
  actions: () => [],
  rowActions: () => [],
  fields: () => defaultFields,
  columns: () => defaultColumns,
  showJsonEditor: false,
  initialParams: () => ({}),
  searchParams: () => ({}),
  defaultValues: () => ({}),
  allowCreate: true,
  allowEdit: true,
  deferLoad: false,
  formBlocked: false,
  detailMode: 'none'
})

const emit = defineEmits<{ customAction: [action: PageAction, item?: ResourceItem, payload?: Record<string, unknown>]; saved: [item: ResourceItem] }>()
const router = useRouter()
const keyword = ref('')
const items = ref<ResourceItem[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const selectedIds = ref<number[]>([])
const message = ref('')
const actionRunning = ref(false)
const runningActionKey = ref('')
const dialogVisible = ref(false)
const caseDraftDialogMode = ref(false)
const editingItem = ref<ResourceItem | null>(null)
const saving = ref(false)
const formError = ref('')
const formValues = ref<Record<string, FormValue>>({})
const multiSelectValues = ref<Record<string, string[]>>({})
const checkboxValues = ref<Record<string, boolean>>({})
const jsonValues = ref<Record<string, string>>({})
const remoteOptions = ref<Record<string, ResourceOption[]>>({})
const remoteOptionsLoading = ref(0)
const extraDataJson = ref('{}')
const resultVisible = ref(false)
const resultTitle = ref('执行结果')
const actionResult = ref<unknown>(null)
const detailVisible = ref(false)
const detailItem = ref<ResourceItem | null>(null)
const {
  operationToastVisible,
  operationToastTitle,
  operationToastMessage,
  showOperationToast
} = useOperationToast()
const { loading: listLoading, error: loadError, run: loadRequest, cancel: cancelLoad } = useLatestRequest()
const { deleting, deleteError, removeResources } = useResourceDeletion({
  path: () => props.apiPath,
  scope: () => JSON.stringify([props.apiPath, props.initialParams, props.searchParams]),
  reload: async count => {
    const lastPage = Math.max(1, Math.ceil(Math.max(0, total.value - count) / pageSize.value))
    currentPage.value = Math.min(currentPage.value, lastPage)
    await load()
  },
  success: count => showOperationToast('删除成功', `已删除 ${count} 条`)
})

const formFields = computed(() => props.fields)
const visibleFields = computed(() => props.fields.filter(field => !field.hidden && fieldVisible(field)))
const visibleColumns = computed(() => props.columns)
const allChecked = computed(() => items.value.length > 0 && selectedIds.value.length === items.value.length)
const dialogTitle = computed(() => `${editingItem.value ? '编辑' : '新增'}${props.title}`)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))
const caseDraftCurrentIndex = computed(() => editingItem.value ? items.value.findIndex(item => item.id === editingItem.value?.id) : -1)
const caseDraftPositionText = computed(() => caseDraftCurrentIndex.value >= 0 ? `当前页第 ${caseDraftCurrentIndex.value + 1} / ${items.value.length} 条` : '当前页')
const caseDraftCanReview = computed(() => String(editingItem.value?.status || '') === 'draft')
const hideExtraJsonEditor = computed(() => props.apiPath.includes('/web-testing/') || props.apiPath.includes('case-drafts'))
const isWebCaseDraftPage = computed(() => props.apiPath.includes('/web-testing/case-drafts'))
const isApiTestCasePage = computed(() => props.apiPath.includes('/api-testing/cases'))
const isWebTestCasePage = computed(() => props.apiPath.includes('/web-testing/cases'))
const dynamicVariableDefinitions = computed<Record<string, unknown>>(() => {
  try {
    const variables = JSON.parse(jsonValues.value['data.variables'] || '{}')
    return isRecord(variables) ? variables : {}
  } catch { return {} }
})

async function load() {
  if (props.deferLoad) { cancelLoad(); return }
  await loadRequest(signal => listResources(props.apiPath, {
    keyword: keyword.value,
    page: currentPage.value,
    pageSize: pageSize.value,
    ...props.initialParams,
    ...props.searchParams
  }, signal), data => {
    items.value = data.items
    total.value = data.total
    pageSize.value = Number(data.pageSize) || pageSize.value
    currentPage.value = Number(data.page) || currentPage.value
    selectedIds.value = []
  })
}

async function search() { currentPage.value = 1; await load() }
async function goToPage(page: number) { currentPage.value = Math.min(Math.max(Math.trunc(page), 1), totalPages.value); await load() }
async function handlePaginationChange(nextPage: number, nextPageSize: number) { currentPage.value = nextPage; pageSize.value = nextPageSize; await load() }
async function openCreate() { caseDraftDialogMode.value = false; editingItem.value = null; initFormValues(); extraDataJson.value = '{}'; formError.value = ''; dialogVisible.value = true; await loadRemoteOptionsSafely() }
async function openEdit(item: ResourceItem) { caseDraftDialogMode.value = false; editingItem.value = item; initFormValues(item); extraDataJson.value = stringifyJson(item.data || {}); formError.value = ''; dialogVisible.value = true; await loadRemoteOptionsSafely() }
async function handleRowClick(item: ResourceItem, event: MouseEvent) { if (props.detailMode !== 'case-draft') return; if ((event.target as HTMLElement | null)?.closest('button, input, select, textarea, a, label')) return; await openCaseDraftDetail(item) }
async function openCaseDraftDetail(item: ResourceItem) { caseDraftDialogMode.value = true; editingItem.value = item; initFormValues(item); extraDataJson.value = stringifyJson(item.data || {}); formError.value = ''; dialogVisible.value = true; await loadRemoteOptionsSafely() }
function canSwitchCaseDraft(offset: number) { const nextIndex = caseDraftCurrentIndex.value + offset; return nextIndex >= 0 && nextIndex < items.value.length ? true : offset < 0 ? currentPage.value > 1 : currentPage.value < totalPages.value }
async function switchCaseDraftDetail(offset: number) { if (!canSwitchCaseDraft(offset)) return; const nextItem = items.value[caseDraftCurrentIndex.value + offset]; if (nextItem) { await openCaseDraftDetail(nextItem); return } await goToPage(currentPage.value + (offset < 0 ? -1 : 1)); const fallback = offset < 0 ? items.value[items.value.length - 1] : items.value[0]; if (fallback) await openCaseDraftDetail(fallback) }
async function acceptCurrentCaseDraft() { if (editingItem.value) await runCurrentCaseDraftAction('采纳', `${props.apiPath}/${editingItem.value.id}/accept`, {}) }
async function rejectCurrentCaseDraft() { if (editingItem.value) await runCurrentCaseDraftAction('驳回', `${props.apiPath}/${editingItem.value.id}/reject`, { review_comment: String(formValues.value.review_comment || '手动驳回') }) }
async function runCurrentCaseDraftAction(label: string, path: string, payload: Record<string, unknown>) {
  if (!editingItem.value || !caseDraftCanReview.value) return
  actionRunning.value = true
  try {
    await postAction(path, { id: editingItem.value.id, ...payload })
    showOperationToast(`${label}成功`, `用例草稿已${label}`)
    await load()
    const refreshed = items.value.find(item => item.id === editingItem.value?.id)
    refreshed ? await openCaseDraftDetail(refreshed) : closeDialog()
  } catch (error) {
    formError.value = getErrorMessage(error)
  } finally {
    actionRunning.value = false
    runningActionKey.value = ''
  }
}
async function deleteCurrentCaseDraft() {
  if (!editingItem.value) return
  const currentIndex = caseDraftCurrentIndex.value
  await removeResources([editingItem.value.id], false, async () => {
    const nextItem = items.value[Math.min(currentIndex, items.value.length - 1)]
    nextItem ? await openCaseDraftDetail(nextItem) : closeDialog()
  })
}
function closeDialog() { if (saving.value) return; dialogVisible.value = false; caseDraftDialogMode.value = false; formError.value = '' }
async function submitForm() {
  if (saving.value || props.formBlocked) return
  formError.value = ''
  let payload: ResourcePayload
  try { payload = buildPayload() } catch (error) { formError.value = error instanceof Error ? error.message : '表单数据无效'; return }
  saving.value = true
  try {
    if (editingItem.value) { const savedItem = await updateResource(props.apiPath, editingItem.value.id, payload); items.value = items.value.map(item => item.id === savedItem.id ? savedItem : item); editingItem.value = savedItem; emit('saved', savedItem); showOperationToast('编辑成功', '数据已更新') }
    else { const savedItem = await createResource(props.apiPath, payload); await load(); emit('saved', savedItem); showOperationToast('添加成功', '数据已添加') }
    if (!caseDraftDialogMode.value) dialogVisible.value = false
  } catch (error) { formError.value = getErrorMessage(error) } finally { saving.value = false }
}
async function remove(id: number) { await removeResources([id], false) }
async function removeSelected() { await removeResources([...selectedIds.value]) }
async function runAction(action: PageAction, key = actionKey(action, 0)) { if (action.type === 'custom') { const payload = buildActionPayload(action); if (action.selectedKey) payload[action.selectedKey] = selectedIds.value; emit('customAction', action, undefined, payload); return } if (action.type === 'route') { await router.push({ path: action.path, query: buildQueryParams(buildActionPayload(action)) }); return } const payload = buildActionPayload(action); if (action.selectedKey) payload[action.selectedKey] = selectedIds.value; await runRequestAction(action, payload, undefined, key) }
async function runRowAction(action: PageAction, item: ResourceItem, key = actionKey(action, 0, item)) { if (isRowActionDisabled(action, item)) return; if (action.type === 'custom') { emit('customAction', action, item, { id: item.id, ...buildActionPayload(action, item) }); return } if (action.type === 'route') { await router.push({ path: resolveActionPath(action.path, item), query: buildQueryParams(buildActionPayload(action, item)) }); return } await runRequestAction(action, { id: item.id, ...buildActionPayload(action, item) }, item, key) }
async function runRequestAction(action: PageAction, payload: Record<string, unknown>, item?: ResourceItem, key = actionKey(action, 0, item)) {
  actionRunning.value = true
  runningActionKey.value = key
  try {
    let result: unknown = await postAction(resolveActionPath(action.path, item), payload)
    if (action.awaitAgentTasks) {
      const { resolveAgentAction } = await import('../services/agent.service')
      result = await resolveAgentAction(result)
    }
    if (action.feedback === 'toast') {
      showOperationToast(action.successTitle || '执行成功', action.successMessage || actionSuccessMessage(action, result))
    } else {
      actionResult.value = result
      resultTitle.value = `${action.label}结果`
      resultVisible.value = true
    }
    if (action.path.includes('/projects/') && action.path.includes('/set-default')) {
      clearRemoteOptionsCache('/projects/options')
    }
    if (action.reload !== false) await load()
  } catch (error) {
    message.value = getErrorMessage(error)
  } finally {
    actionRunning.value = false
    runningActionKey.value = ''
  }
}
function closeResultDialog() { resultVisible.value = false }
function openDetail(item: ResourceItem) { detailItem.value = item; detailVisible.value = true }
function closeDetailDialog() { detailVisible.value = false }
function toggleAll(event: Event) { selectedIds.value = (event.target as HTMLInputElement).checked ? items.value.map(item => item.id) : [] }
function initFormValues(item?: ResourceItem) { formValues.value = {}; checkboxValues.value = {}; multiSelectValues.value = {}; jsonValues.value = {}; for (const field of formFields.value) { const value = item ? readValue(item, field.key) : readValue(props.defaultValues, field.key) ?? defaultValueFor(field); if (field.type === 'json') jsonValues.value[field.key] = stringifyJson(value); else if (field.type === 'checkbox') checkboxValues.value[field.key] = Boolean(value); else if (field.type === 'multiselect') multiSelectValues.value[field.key] = Array.isArray(value) ? value.map(String) : []; else formValues.value[field.key] = normalizeBindableValue(value) } }
async function loadRemoteOptionsSafely() { remoteOptionsLoading.value += 1; try { await loadRemoteOptions() } catch (error) { formError.value = `下拉选项加载失败：${getErrorMessage(error)}` } finally { remoteOptionsLoading.value -= 1 } }
async function loadRemoteOptions() { const nextOptions: Record<string, ResourceOption[]> = { ...remoteOptions.value }; for (const field of formFields.value) { const config = field.remoteOptions; if (!config || !remoteOptionDependenciesReady(config)) continue; const rows = await listRemoteOptionsCached(config.path, remoteOptionParams(config)); nextOptions[field.key] = rows.map(row => ({ value: readValue(row, config.valueKey) as string | number, label: config.labelKeys.map(key => formatValue(readValue(row, key))).filter(value => value !== '-').join(' '), isDefault: isDefaultOption(row) })); applyRemoteDefaultValues(nextOptions) } remoteOptions.value = nextOptions; applyRemoteDefaultValues(nextOptions) }
function applyRemoteDefaultValues(options: Record<string, ResourceOption[]>) { if (editingItem.value) return; for (const field of formFields.value) { if (!isProjectSelectField(field)) continue; const currentValue = formValues.value[field.key]; if (currentValue != null && currentValue !== '') continue; const defaultOption = options[field.key]?.find(option => option.isDefault) || options[field.key]?.[0]; if (defaultOption) formValues.value[field.key] = normalizeBindableValue(defaultOption.value) } }
function isProjectSelectField(field: ResourceField) { return field.key === 'project_id' && field.remoteOptions?.path === '/projects/options' }
function isDefaultOption(row: Record<string, unknown>) { return readValue(row, 'is_default') === true || readValue(row, 'data.is_default') === true }
function remoteOptionDependenciesReady(config: NonNullable<ResourceField['remoteOptions']>) { if (!config.dependsOn) return true; return Object.values(config.dependsOn).every(key => { const value = readCurrentFormValue(key); return value != null && value !== '' }) }
async function handleSelectChange(field: ResourceField) { if (field.remoteOptions) await loadRemoteOptionsSafely() }
function remoteOptionParams(config: NonNullable<ResourceField['remoteOptions']>) { const params: Record<string, string | number | boolean> = { ...(config.params || {}) }; if (config.dependsOn) { for (const [paramKey, fieldKey] of Object.entries(config.dependsOn)) { const value = readCurrentFormValue(fieldKey); if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') params[paramKey] = value } } return params }
function readCurrentFormValue(fieldKey: string): unknown { return fieldKey in formValues.value ? formValues.value[fieldKey] : readValue({ data: buildCurrentDataValues() }, fieldKey) }
function buildCurrentDataValues() { const data: Record<string, unknown> = {}; for (const [key, value] of Object.entries(formValues.value)) if (key.startsWith('data.')) assignNested(data, key.slice(5), value); return data }
function getFieldOptions(field: ResourceField) { return remoteOptions.value[field.key] || field.options || [] }
function getApiFieldOptions(field: ResourceField) { return getFieldOptions(field).map(option => ({ id: Number(option.value), name: option.label })) }
function buildPayload(): ResourcePayload { const payload: ResourcePayload = { name: '', project_id: null, description: null, status: 'active', data: props.showJsonEditor ? parseJsonObject(extraDataJson.value, '扩展数据 JSON') : { ...(editingItem.value?.data || {}) } }; for (const field of visibleFields.value) { const value = normalizeFieldValue(field); if (field.required && isEmptyValue(value)) throw new Error(`请填写${field.label}`); assignPayloadValue(payload, field.key, value) } if (!payload.name || typeof payload.name !== 'string') throw new Error('请填写名称'); return payload }
function normalizeFieldValue(field: ResourceField): unknown { if (field.type === 'json') return parseJson(jsonValues.value[field.key] || '', field.label); if (field.type === 'number') return parseNumber(formValues.value[field.key], field.label); if (field.type === 'checkbox') return Boolean(checkboxValues.value[field.key]); if (field.type === 'multiselect') return multiSelectValues.value[field.key] || []; const value = formValues.value[field.key]; return value === '' ? null : value }
function assignPayloadValue(payload: ResourcePayload, key: string, value: unknown) { if (key.startsWith('data.')) { assignNested(payload.data || {}, key.slice(5), value); return } if (key === 'project_id') { payload.project_id = value == null ? null : Number(value); return } payload[key] = value }
function readValue(item: Record<string, unknown>, key: string): unknown { return key.split('.').reduce<unknown>((current, part) => current && typeof current === 'object' && part in current ? (current as Record<string, unknown>)[part] : undefined, item) }
function assignNested(target: Record<string, unknown>, path: string, value: unknown) { const parts = path.split('.'); let current = target; for (const part of parts.slice(0, -1)) { if (!isRecord(current[part])) current[part] = {}; current = current[part] as Record<string, unknown> } current[parts[parts.length - 1]] = value }
function defaultValueFor(field: ResourceField): unknown { if (field.type === 'checkbox') return false; if (field.type === 'json') return field.defaultValue ?? {}; if (field.type === 'multiselect') return field.defaultValue ?? []; return field.defaultValue ?? '' }
function normalizeBindableValue(value: unknown): FormValue { if (value == null) return ''; if (typeof value === 'string' || typeof value === 'number') return value; if (typeof value === 'boolean') return value ? 'true' : 'false'; return JSON.stringify(value) }
function parseNumber(value: unknown, label: string) { if (value === '' || value == null) return null; const parsed = Number(value); if (!Number.isFinite(parsed)) throw new Error(`${label}必须是数字`); return parsed }
function parseJson(value: string, label: string): unknown { if (!value.trim()) return {}; try { return JSON.parse(value) as unknown } catch { throw new Error(`${label}不是合法 JSON`) } }
function parseJsonObject(value: string, label: string) { const parsed = parseJson(value, label); if (!isRecord(parsed)) throw new Error(`${label}必须是 JSON 对象`); return parsed }
function stringifyJson(value: unknown) { return JSON.stringify(value ?? {}, null, 2) }
function isWebCaseDraftJsonField(field: ResourceField) { return props.apiPath.includes('/web-testing/case-drafts') && field.key === 'case_json' }
function isCaseValueJsonField(field: ResourceField) { return /\/(cases|case-drafts)$/.test(props.apiPath) && ['steps', 'data.params', 'data.body', 'data.headers'].includes(field.key) }
function shouldHideJsonInput(field: ResourceField) { return field.type === 'json' && props.apiPath.includes('/web-testing/') && !isWebTestCasePage.value && field.key !== 'data.variables' }
function shouldHideJsonField(field: ResourceField) { return shouldHideJsonInput(field) && !isWebCaseDraftJsonField(field) }
function getCaseRequest(item: ResourceItem): unknown {
  const data = isRecord(item.data) ? item.data : {}
  if (!isRecord(data.request)) return data
  const { request, ...rest } = data
  return { ...request, ...rest }
}
function getCaseAssertions(item: ResourceItem) {
  if (Array.isArray(item.assertions)) return item.assertions
  const data = isRecord(item.data) ? item.data : {}
  return data.assertions ?? []
}
function getCaseStrategies(item: ResourceItem) {
  if (Array.isArray(item.strategies) && item.strategies.length) return item.strategies
  if (Array.isArray(item.strategy_ids)) return item.strategy_ids.map(id => ({ id }))
  const data = isRecord(item.data) ? item.data : {}
  return data.strategies ?? data.strategy_ids ?? []
}
function caseSourceLabel(item: ResourceItem) { return readValue(item, 'data.api_path') ? 'API 路径' : '来源' }
function caseSourceDisplay(item: ResourceItem) {
  const apiPath = readValue(item, 'data.api_path')
  if (apiPath) return [readValue(item, 'data.api_method'), apiPath].filter(value => value != null && value !== '').join(' ')
  return formatValue(item.source_id)
}
function formatValue(value: unknown): string { if (value == null || value === '') return '-'; if (typeof value === 'boolean') return value ? '是' : '否'; if (typeof value === 'object') return JSON.stringify(value); return String(value) }
function formatCellValue(item: ResourceItem, key: string) { const value = readValue(item, key); if (key === 'status' || key.endsWith('.status')) return formatStatus(value); return localOptionLabel(key, value) || formatValue(value) }
function localOptionLabel(key: string, value: unknown) { const field = formFields.value.find(item => item.key === key); if (!field?.options || value == null || value === '') return ''; return field.options.find(item => String(item.value) === String(value))?.label || '' }
function formatStatus(value: unknown) { const labels: Record<string, string> = { success: '成功', failed: '失败', queued: '排队中', running: '执行中', blocked: '阻塞', interrupted: '中断', active: '启用', draft: props.apiPath.includes('case-drafts') ? '待审核' : '草稿', disabled: '停用', accepted: '已采纳', rejected: '已驳回', pending: '待处理', done: '已完成', cancelled: '已取消', canceled: '已取消', error: '异常', passed: '通过', skipped: '已跳过' }; return labels[String(value || '')] || formatValue(value) }
function actionSuccessMessage(action: PageAction, result: unknown) {
  if (isRecord(result)) {
    const successCount = Number(result.success_count)
    const failedCount = Number(result.failed_count)
    const queuedCount = Number(result.queued_count)
    const hasExecutionCounts = [successCount, failedCount, queuedCount].some(Number.isFinite)
    if (hasExecutionCounts) {
      return `执行已完成：成功 ${Number.isFinite(successCount) ? successCount : 0} 条，失败 ${Number.isFinite(failedCount) ? failedCount : 0} 条，排队 ${Number.isFinite(queuedCount) ? queuedCount : 0} 条`
    }
  }
  return `${action.label}已完成`
}
function fieldVisible(field: ResourceField) { if (!field.visibleWhen) return true; if ('all' in field.visibleWhen) return field.visibleWhen.all.every(condition => matchVisibleCondition(condition.key, condition.value)); return matchVisibleCondition(field.visibleWhen.key, field.visibleWhen.value) }
function matchVisibleCondition(key: string, expectedValue: unknown | unknown[]) { const currentValue = readCurrentFormValue(key); return Array.isArray(expectedValue) ? expectedValue.includes(currentValue) : currentValue === expectedValue }
function isRowActionDisabled(action: PageAction, item: ResourceItem) { if (action.disabledWhen && matchActionValue(readValue(item, action.disabledWhen.key), action.disabledWhen.value)) return true; if (action.enabledWhen) return readValue(item, action.enabledWhen.key) !== action.enabledWhen.value; return false }
function isRowActionRunning(action: PageAction, index: number, item: ResourceItem) { return runningActionKey.value === actionKey(action, index, item) }
function isRowActionActive(action: PageAction, item: ResourceItem) { return Boolean(action.activeWhen && matchActionValue(readValue(item, action.activeWhen.key), action.activeWhen.value)) }
function matchActionValue(currentValue: unknown, expectedValue: unknown | unknown[]) { return Array.isArray(expectedValue) ? expectedValue.includes(currentValue) : currentValue === expectedValue }
function rowActionTitle(action: PageAction, item: ResourceItem) { return isRowActionDisabled(action, item) ? '当前状态不可操作' : action.label }
function resolveActionPath(path: string, item?: ResourceItem) { return item ? path.replace(/\{([^}]+)\}/g, (_, key: string) => String(readValue(item, key) ?? '')) : path }
function buildActionPayload(action: PageAction, item?: ResourceItem) { const payload: Record<string, unknown> = { ...(action.payload || {}) }; for (const [key, value] of Object.entries(payload)) payload[key] = resolveTemplateValue(value, item); return payload }
function actionKey(action: PageAction, index: number, item?: ResourceItem) { return [item?.id ?? 'toolbar', index, action.label, action.path].join(':') }
function resolveTemplateValue(value: unknown, item?: ResourceItem): unknown {
  if (item && typeof value === 'string' && value.startsWith('$')) return readValue(item, value.slice(1)) ?? ''
  if (Array.isArray(value)) return value.map(itemValue => resolveTemplateValue(itemValue, item))
  if (isRecord(value)) return Object.fromEntries(Object.entries(value).map(([key, itemValue]) => [key, resolveTemplateValue(itemValue, item)]))
  return value
}
function buildQueryParams(payload: Record<string, unknown>) { return Object.fromEntries(Object.entries(payload).map(([key, value]) => [key, Array.isArray(value) ? value.join(',') : String(value ?? '')])) }
function isEmptyValue(value: unknown) { return value == null || value === '' || (Array.isArray(value) && !value.length) }
function isRecord(value: unknown): value is Record<string, unknown> { return Boolean(value) && typeof value === 'object' && !Array.isArray(value) }
function getErrorMessage(error: unknown) { const data = (error as { response?: { data?: { message?: string; detail?: unknown } } }).response?.data; if (data?.message) return data.message; if (typeof data?.detail === 'string') return data.detail; return error instanceof Error ? error.message : '操作失败' }

watch(
  [() => props.initialParams, () => props.searchParams, () => props.deferLoad, () => props.apiPath],
  async () => {
    cancelLoad()
    items.value = []; total.value = 0; selectedIds.value = []
    currentPage.value = 1
    if (!props.deferLoad) await load()
  },
  { deep: true, immediate: true }
)
defineExpose({ load, openCreate })
</script>

<style scoped>
.modal-backdrop { z-index: 60; }
.api-evidence-modal { width: min(1600px, 100%); }
</style>
