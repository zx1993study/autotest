<template>
  <section class="page page-management-page">
    <div class="toolbar page-management-toolbar">
      <select
        v-model.number="selectedProjectId"
        class="project-filter"
        aria-label="选择 Web 项目"
        :disabled="projectsLoading || !projects.length"
        @change="handleProjectChange"
      >
        <option v-if="projectsLoading" :value="selectedProjectId" disabled>正在加载默认项目...</option>
        <option v-else-if="!projects.length" :value="0" disabled>暂无可用项目</option>
        <option v-for="project in projects" :key="project.id" :value="project.id">
          {{ project.is_default ? `${project.name}（默认）` : project.name }}
        </option>
      </select>
      <input
        v-model.trim="keyword"
        type="search"
        placeholder="搜索页面名称、路由或地址"
        aria-label="搜索页面"
        @keyup.enter="searchPages"
      />
      <select
        v-model="statusFilter"
        class="status-filter"
        aria-label="按状态筛选页面"
        @change="searchPages"
      >
        <option value="">全部状态</option>
        <option value="active">启用</option>
        <option value="disabled">停用</option>
        <option value="archived">归档</option>
      </select>
      <button type="button" :disabled="loading" @click="searchPages">查询</button>
      <button type="button" :disabled="loading || (!keyword && !statusFilter)" @click="resetFilters">重置</button>
      <button class="create-page-button" type="button" :disabled="!selectedProjectId" @click="openCreateDialog">新增页面</button>
    </div>

    <p v-if="message" class="operation-message" role="status">{{ message }}</p>
    <p v-if="errorMessage" class="operation-message error-text" role="alert">{{ errorMessage }}</p>

    <div class="table-wrap page-table-wrap">
      <table class="page-directory-table">
        <thead>
          <tr>
            <th>页面名称</th>
            <th>页面路由</th>
            <th>页面地址</th>
            <th class="number-column">功能</th>
            <th class="number-column">API</th>
            <th class="execution-column">执行结果</th>
            <th class="status-column">状态</th>
            <th class="action-column">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="pageItem in pages"
            :key="pageItem.id"
            class="clickable-row"
            tabindex="0"
            @click="openDetail(pageItem)"
            @keydown.enter="openDetail(pageItem)"
          >
            <td class="page-name-cell">
              <strong>{{ pageItem.name }}</strong>
              <small v-if="pageItem.description">{{ pageItem.description }}</small>
            </td>
            <td class="route-cell"><code :title="textValue(pageItem.data.route)">{{ textValue(pageItem.data.route) }}</code></td>
            <td class="address-cell">
              <span :title="textValue(pageItem.data.url)">{{ textValue(pageItem.data.url) }}</span>
              <small v-if="addressVariantCount(pageItem) > 1">
                另有 {{ addressVariantCount(pageItem) - 1 }} 个访问地址
              </small>
            </td>
            <td class="number-cell"><span class="metric-value feature-metric">{{ pageItem.feature_count }}</span></td>
            <td class="number-cell"><span class="metric-value api-metric">{{ pageItem.interface_count }}</span></td>
            <td><WebExecutionResultCell :summary="executionResults[pageItem.id]" :loading="executionLoading" :error="executionError" aggregate @open="selectedRecordId = $event" @retry="refreshExecution" /></td>
            <td><span :class="['status-badge', pageItem.status]">{{ statusText(pageItem.status) }}</span></td>
            <td class="actions-cell">
              <div class="row-actions">
                <button
                  type="button"
                  title="复制页面地址"
                  :disabled="!pageItem.data.url"
                  @click.stop="copyAddress(pageItem)"
                >复制</button>
                <button
                  type="button"
                  title="在新窗口打开页面"
                  :disabled="!isExternalUrl(pageItem.data.url)"
                  @click.stop="openAddress(pageItem)"
                >打开</button>
                <button type="button" class="detail-action" @click.stop="openDetail(pageItem)">页面功能</button>
                <button type="button" @click.stop="openEditDialog(pageItem)">编辑</button>
              </div>
            </td>
          </tr>
          <tr v-if="!pages.length">
            <td colspan="8" class="empty-cell">
              {{ loading ? '页面加载中...' : keyword || statusFilter ? '没有匹配的页面' : '当前项目暂无页面' }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <CommonPagination
      :page="currentPage"
      :page-size="pageSize"
      :total="total"
      :loading="loading"
      @change="handlePagination"
    />
    <ExecutionRecordDetailDialog v-if="selectedRecordId !== null" :record-id="selectedRecordId" @close="selectedRecordId = null" />
  </section>

  <div v-if="dialogVisible" class="modal-backdrop" @click.self="closeDialog">
    <section class="modal-panel page-dialog" role="dialog" aria-modal="true">
      <header class="modal-header">
        <div>
          <h3>{{ editingPage ? '编辑页面' : '新增页面' }}</h3>
        </div>
        <button class="modal-close" type="button" aria-label="关闭" @click="closeDialog">×</button>
      </header>
      <form class="modal-form" @submit.prevent="submitPage">
        <div class="form-grid">
          <label class="field full">
            <span>页面名称<b>*</b></span>
            <input v-model.trim="pageForm.name" maxlength="128" required />
          </label>
          <label class="field full">
            <span>页面路由</span>
            <input v-model.trim="pageForm.route" placeholder="例如：/warehouse/warehouse" />
          </label>
          <label class="field full">
            <span>页面地址</span>
            <input v-model.trim="pageForm.url" placeholder="例如：https://example.test/warehouse/warehouse" />
          </label>
          <label class="field">
            <span>状态</span>
            <select v-model="pageForm.status">
              <option value="active">启用</option>
              <option value="disabled">停用</option>
              <option value="archived">归档</option>
            </select>
          </label>
          <label class="field full">
            <span>描述</span>
            <textarea v-model.trim="pageForm.description" rows="3" />
          </label>
        </div>
        <p v-if="formError" class="form-error">{{ formError }}</p>
        <footer class="modal-actions">
          <button type="button" :disabled="saving" @click="closeDialog">取消</button>
          <button type="submit" :disabled="saving">{{ saving ? '保存中...' : '保存' }}</button>
        </footer>
      </form>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import CommonPagination from '../../components/common/CommonPagination.vue'
import { listProjectOptions, resolveDefaultProjectId } from '../../services/project.service'
import {
  createWebPageGroup,
  listWebPageGroups,
  updateWebPageGroup
} from '../../services/web-page.service'
import { pageTabKey, usePageTabsStore } from '../../store/page-tabs'
import type { ProjectOption } from '../../types/resource'
import type { WebPageGroup } from '../../types/web-page'
import { useLatestRequest } from '../../composables/useLatestRequest'
import { useWebExecutionSummaries } from '../../composables/useWebExecutionSummaries'
import WebExecutionResultCell from '../../components/web-testing/WebExecutionResultCell.vue'
import ExecutionRecordDetailDialog from '../../components/reports/ExecutionRecordDetailDialog.vue'

const route = useRoute()
const router = useRouter()
const pageTabsStore = usePageTabsStore()
const projects = ref<ProjectOption[]>([])
const selectedProjectId = ref(0)
const projectsLoading = ref(true)
const keyword = ref('')
const statusFilter = ref('')
const pages = ref<WebPageGroup[]>([])
const { results: executionResults, loading: executionLoading, error: executionError, refresh: refreshExecution, selectedRecordId } = useWebExecutionSummaries({ projectId: () => selectedProjectId.value, ids: () => pages.value.map(item => item.id), scope: 'page' })
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const { loading, error: errorMessage, run: loadRequest, cancel: cancelLoad } = useLatestRequest('页面加载失败')
const message = ref('')
const dialogVisible = ref(false)
const editingPage = ref<WebPageGroup | null>(null)
const saving = ref(false)
const formError = ref('')
const pageForm = reactive({ name: '', route: '', url: '', status: 'active', description: '' })

onMounted(initialize)

async function initialize() {
  pageTabsStore.setTitle(pageTabKey(route), '页面管理')
  const queryProjectId = positiveInteger(route.query.project_id)
  selectedProjectId.value = queryProjectId
  const initialPagesPromise = queryProjectId ? loadPages() : Promise.resolve()
  try {
    projects.value = await listProjectOptions()
    const resolvedProjectId = projects.value.some(item => item.id === queryProjectId)
      ? queryProjectId
      : resolveDefaultProjectId(projects.value)
    const projectChanged = selectedProjectId.value !== resolvedProjectId
    selectedProjectId.value = resolvedProjectId
    projectsLoading.value = false
    await initialPagesPromise
    if (projectChanged) {
      await syncRouteProject()
      await loadPages()
    }
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    projectsLoading.value = false
  }
}

async function loadPages() {
  if (!selectedProjectId.value) {
    cancelLoad()
    pages.value = []
    total.value = 0
    return
  }
  await loadRequest(signal => listWebPageGroups({
      project_id: selectedProjectId.value,
      keyword: keyword.value || undefined,
      status: statusFilter.value || undefined,
      page: currentPage.value,
      pageSize: pageSize.value
    }, signal), result => {
    pages.value = result.items
    total.value = result.total
    currentPage.value = result.page
    pageSize.value = result.pageSize
  })
}

async function handleProjectChange() {
  cancelLoad()
  pages.value = []
  total.value = 0
  keyword.value = ''
  statusFilter.value = ''
  currentPage.value = 1
  await syncRouteProject()
  await loadPages()
}

async function syncRouteProject() {
  if (!selectedProjectId.value || positiveInteger(route.query.project_id) === selectedProjectId.value) return
  await router.replace({ path: route.path, query: { project_id: String(selectedProjectId.value) } })
}

async function searchPages() {
  currentPage.value = 1
  await loadPages()
}

async function resetFilters() {
  keyword.value = ''
  statusFilter.value = ''
  currentPage.value = 1
  await loadPages()
}

async function handlePagination(page: number, size: number) {
  currentPage.value = page
  pageSize.value = size
  await loadPages()
}

async function openDetail(pageItem: WebPageGroup) {
  await router.push({
    path: `/web/pages/${pageItem.id}`,
    query: { project_id: String(pageItem.project_id || selectedProjectId.value) }
  })
}

function openCreateDialog() {
  editingPage.value = null
  Object.assign(pageForm, { name: '', route: '', url: '', status: 'active', description: '' })
  formError.value = ''
  dialogVisible.value = true
}

function openEditDialog(pageItem: WebPageGroup) {
  editingPage.value = pageItem
  Object.assign(pageForm, {
    name: pageItem.name,
    route: textValue(pageItem.data.route, ''),
    url: textValue(pageItem.data.url, ''),
    status: pageItem.status,
    description: pageItem.description || ''
  })
  formError.value = ''
  dialogVisible.value = true
}

function closeDialog() {
  if (!saving.value) dialogVisible.value = false
}

async function submitPage() {
  formError.value = ''
  if (!pageForm.name || (!pageForm.route && !pageForm.url)) {
    formError.value = '请填写页面名称，以及页面路由或页面地址'
    return
  }
  saving.value = true
  try {
    const payload = {
      name: pageForm.name,
      project_id: selectedProjectId.value,
      route: pageForm.route,
      url: pageForm.url,
      status: pageForm.status,
      description: pageForm.description || undefined
    }
    if (editingPage.value) await updateWebPageGroup(editingPage.value.id, payload)
    else await createWebPageGroup(payload)
    message.value = editingPage.value ? '页面已更新' : '页面已创建'
    dialogVisible.value = false
    await loadPages()
  } catch (error) {
    formError.value = getErrorMessage(error)
  } finally {
    saving.value = false
  }
}

async function copyAddress(pageItem: WebPageGroup) {
  const value = textValue(pageItem.data.url, '')
  if (!value) return
  try {
    await navigator.clipboard.writeText(value)
    message.value = '页面地址已复制'
  } catch {
    errorMessage.value = '复制失败，请手动复制页面地址'
  }
}

function openAddress(pageItem: WebPageGroup) {
  const value = textValue(pageItem.data.url, '')
  if (isExternalUrl(value)) window.open(value, '_blank', 'noopener,noreferrer')
}

function addressVariantCount(pageItem: WebPageGroup) {
  return Array.isArray(pageItem.data.url_variants) ? pageItem.data.url_variants.length : 0
}

function isExternalUrl(value: unknown) {
  return /^https?:\/\//i.test(String(value || ''))
}

function textValue(value: unknown, fallback = '-') {
  const text = String(value ?? '').trim()
  return text || fallback
}

function statusText(status: string) {
  return { active: '启用', disabled: '停用', archived: '归档' }[status] || status || '-'
}

function positiveInteger(value: unknown) {
  const raw = Array.isArray(value) ? value[0] : value
  const number = Number(raw || 0)
  return Number.isInteger(number) && number > 0 ? number : 0
}

function getErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : '页面操作失败'
}
</script>

<style scoped>
.page-management-page {
  min-width: 0;
}

.project-filter {
  width: 180px;
}

.status-filter {
  width: 144px;
}

.page-management-toolbar {
  margin-top: 0;
  margin-bottom: 22px;
}

.page-management-toolbar input {
  min-width: 240px;
}

.create-page-button {
  margin-left: auto;
}

.page-directory-table {
  min-width: 1280px;
  table-layout: fixed;
}

.page-directory-table th {
  white-space: nowrap;
}

.page-directory-table th,
.page-directory-table td {
  padding: 16px 14px;
}

.page-directory-table th:nth-child(1) {
  width: 230px;
}

.page-directory-table th:nth-child(2) {
  width: 190px;
}

.page-directory-table th:nth-child(3) {
  width: auto;
}

.route-cell code {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.page-name-cell strong,
.page-name-cell small,
.address-cell > span,
.address-cell > small {
  display: block;
}

.page-name-cell strong {
  color: #18243a;
  line-height: 1.4;
}

.page-name-cell small {
  display: -webkit-box;
  max-width: 100%;
  margin-top: 6px;
  overflow: hidden;
  color: #718096;
  line-height: 1.5;
  white-space: normal;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.page-directory-table code {
  color: #253653;
  font-size: 12px;
}

.number-column,
.number-cell {
  width: 72px;
  text-align: center;
}

.status-column {
  width: 82px;
}

.execution-column { width: 176px; }

.action-column {
  width: 268px;
}

.address-cell {
  min-width: 0;
}

.address-cell > span {
  overflow: hidden;
  color: #334155;
  line-height: 1.5;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.address-cell > small {
  margin-top: 6px;
  color: #718096;
  line-height: 1.4;
}

.metric-value {
  display: inline-flex;
  min-width: 30px;
  height: 28px;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.feature-metric {
  background: #eef7f2;
  color: #176b45;
}

.api-metric {
  background: #eef4ff;
  color: #285ea8;
}

.page-directory-table .row-actions {
  align-items: center;
  gap: 6px;
}

.page-directory-table .row-actions button {
  min-width: 48px;
  height: 32px;
  padding: 0 10px;
  color: #334155;
}

.page-directory-table .row-actions .detail-action {
  border-color: #b9cdf5;
  background: #f3f7ff;
  color: #245aa5;
}

.status-badge {
  display: inline-flex;
  min-width: 50px;
  height: 28px;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  background: #f1f5f9;
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
}

.status-badge.active {
  background: #edf8f2;
  color: #0b7a4b;
}

.status-badge.disabled,
.status-badge.archived {
  background: #fff1f0;
  color: #b42318;
}

.error-text {
  color: #b42318;
}

.operation-message {
  margin: -10px 0 14px;
  color: #146c43;
  font-size: 13px;
}

.page-dialog {
  width: min(620px, calc(100vw - 32px));
}

.modal-header p {
  margin: 5px 0 0;
  color: #6b778c;
  font-size: 13px;
}

@media (max-width: 1600px) {
  .page-management-toolbar {
    flex-wrap: nowrap;
    gap: 8px;
  }

  .project-filter {
    width: 166px;
  }

  .page-management-toolbar input {
    min-width: 200px;
  }

  .page-management-toolbar button {
    padding-right: 10px;
    padding-left: 10px;
  }

  .page-directory-table {
    min-width: 1040px;
  }

  .page-directory-table th:nth-child(1) {
    width: 180px;
  }

  .page-directory-table th:nth-child(2) {
    width: 140px;
  }

  .number-column,
  .number-cell {
    width: 54px;
  }

  .status-column {
    width: 66px;
  }

  .action-column {
    width: 168px;
  }

  .page-directory-table .row-actions {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 5px;
  }

  .page-directory-table .row-actions button {
    min-width: 0;
    padding-right: 7px;
    padding-left: 7px;
  }
}

@media (max-width: 720px) {
  .page-management-toolbar {
    flex-wrap: wrap;
  }

  .page-management-toolbar > select,
  .page-management-toolbar > input,
  .page-management-toolbar > button {
    width: 100%;
  }

  .create-page-button {
    margin-left: 0;
  }
}
</style>
