<template>
  <section v-if="!activeModuleId" class="module-page">
    <div class="module-toolbar">
      <div class="module-filter-group">
        <select v-model.number="apiFilter.projectId" aria-label="选择 API 项目" @change="handleProjectChange">
          <option v-for="project in projects" :key="project.id" :value="project.id">
            {{ project.name }}
          </option>
        </select>
        <input
          v-model.trim="moduleKeyword"
          type="search"
          placeholder="搜索模块名称"
          aria-label="搜索模块名称"
          @keyup.enter="searchModules"
        />
        <button type="button" :disabled="moduleLoading" @click="searchModules">查询</button>
        <button type="button" :disabled="moduleLoading || !moduleKeyword" @click="resetModuleSearch">重置</button>
      </div>
      <div class="module-command-group">
        <button type="button" :disabled="!apiFilter.projectId" @click="openModuleDialog('create')"><Plus :size="16" />新增模块</button>
        <button type="button" @click="createInterfaceFromDirectory">新增 API</button>
        <button type="button" @click="openImportDialog">导入 OpenAPI</button>
        <button type="button" @click="openProjectGeneration">OpenAPI 生成用例</button>
      </div>
    </div>

    <div class="module-table-wrap">
      <table>
        <thead>
          <tr>
            <th>模块名称</th>
            <th class="count-column">API 数量</th>
            <th>方法分布</th>
            <th class="status-column">状态</th>
            <th class="time-column">更新时间</th>
            <th class="enter-column">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="moduleItem in modules"
            :key="moduleItem.key"
            class="module-row"
            tabindex="0"
            @click="enterModule(moduleItem)"
            @keydown.enter.self="enterModule(moduleItem)"
          >
            <td>
              <strong>{{ moduleItem.name }}</strong>
              <small v-if="moduleItem.key === UNGROUPED_MODULE_KEY">未填写所属模块的接口</small>
            </td>
            <td>{{ moduleItem.interface_count }}</td>
            <td class="method-summary">{{ formatMethodCounts(moduleItem.method_counts) }}</td>
            <td>
              <span :class="['module-status', moduleStatusClass(moduleItem)]">{{ moduleStatus(moduleItem) }}</span>
            </td>
            <td>{{ formatUpdateTime(moduleItem.updated_at) }}</td>
            <td>
              <div class="module-row-actions">
                <button type="button" class="enter-button" @click.stop="enterModule(moduleItem)">进入</button>
                <button type="button" class="module-icon-button" :aria-label="`编辑模块 ${moduleItem.name}`" title="编辑模块" :disabled="moduleItem.key === UNGROUPED_MODULE_KEY" @click.stop="openModuleDialog('edit', moduleItem)"><Pencil :size="16" /></button>
                <button type="button" class="module-icon-button danger" :aria-label="`删除模块 ${moduleItem.name}`" :title="moduleItem.interface_count ? '模块包含 API，不能删除' : '删除模块'" :disabled="moduleItem.key === UNGROUPED_MODULE_KEY || !!moduleItem.interface_count" @click.stop="openModuleDialog('delete', moduleItem)"><Trash2 :size="16" /></button>
              </div>
            </td>
          </tr>
          <tr v-if="!modules.length">
            <td colspan="6" class="module-empty">
              <template v-if="moduleLoading">模块加载中...</template>
              <template v-else-if="moduleKeyword">没有匹配的模块</template>
              <template v-else>当前项目暂无 API，请先导入 OpenAPI 或新增 API。</template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <CommonPagination
      :page="modulePage"
      :page-size="modulePageSize"
      :total="moduleTotal"
      :loading="moduleLoading"
      :message="moduleError"
      @change="handleModulePagination"
    />
  </section>

  <ResourcePage
    ref="resourcePageRef"
    :class="{ 'directory-create-host': !activeModuleId }"
    :title="activeModuleId ? `${activeModuleLabel} API` : 'API'"
    :description="`维护 ${activeModuleLabel} 模块下的 API 接口、字段和测试用例。`"
    api-path="/api-testing/interfaces"
    :actions="actions"
    :row-actions="rowActions"
    :fields="apiInterfaceFields"
    :columns="apiInterfaceColumns"
    :initial-params="apiSearchParams"
    :default-values="apiDefaultValues"
    :defer-load="!projectFilterReady || !activeModuleId"
    :form-blocked="moduleBusy || authLoading"
    @custom-action="handleCustomAction"
    @saved="handleInterfaceSaved"
  >
    <template #form-field-data.module_id="{ values }">
      <span>所属模块<b>*</b></span>
      <ApiModuleSelect :project-id="Number(values.project_id) || 0" :model-value="values['data.module_id']" @update:model-value="values['data.module_id'] = $event" @busy="moduleBusy = $event" @changed="handleModuleChanged" />
    </template>
    <template #form-field-data.auth_id="{ values }">
      <span>鉴权信息</span>
      <ApiAuthSelect :project-id="Number(values.project_id) || 0" :model-value="values['data.auth_id']" @update:model-value="values['data.auth_id'] = $event" @busy="authLoading = $event" />
    </template>
    <template #toolbar-top>
      <nav class="module-breadcrumb" aria-label="API 模块层级">
        <button type="button" aria-label="返回模块列表" @click="leaveModule">←</button>
        <button type="button" @click="leaveModule">API 管理</button>
        <span>/</span>
        <strong>{{ activeModuleLabel }}</strong>
      </nav>
    </template>
    <template #search-before-button>
      <select v-model.number="apiFilter.projectId" class="api-filter-select" aria-label="选择 API 项目" @change="handleProjectChange">
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
      <select v-model="apiFilter.status" class="api-filter-select status-filter" aria-label="按状态筛选 API">
        <option value="">全部状态</option>
        <option value="active">启用</option>
        <option value="disabled">停用</option>
        <option value="archived">归档</option>
      </select>
    </template>
    <template #search-actions>
      <button type="button" @click="resetApiFilters">重置筛选</button>
    </template>
  </ResourcePage>

  <ApiModuleDialog :project-id="apiFilter.projectId" :mode="moduleDialogMode" :module="editingModule" @close="moduleDialogMode = ''" @changed="handleDirectoryModuleChanged" />

  <ApiCaseDraftGenerateDialog
    :visible="openapiGenerationVisible"
    :initial-project-id="apiFilter.projectId"
    :initial-module-id="generationModuleId || undefined"
    :initial-module-name="generationModuleName || undefined"
    @close="closeGenerationDialog"
  />

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
              <option value="file">上传 JSON/YAML 文件</option>
              <option value="url">输入 URL 地址</option>
            </select>
          </label>

          <label v-if="importForm.sourceType === 'file'" class="field full">
            <span>OpenAPI JSON/YAML 文件<b>*</b></span>
            <input type="file" accept=".json,.yaml,.yml,application/json,application/yaml,text/yaml" @change="handleFileChange" />
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

</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { Pencil, Plus, Trash2 } from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import {
  getOpenApiImportTask,
  importOpenApiFile,
  importOpenApiUrl,
  listProjectOptions,
  OpenApiImportTask,
  OpenApiImportResult,
  ProjectOption,
  resolveDefaultProjectId
} from '../../api/http'
import ResourcePage from '../../components/ResourcePage.vue'
import ApiCaseDraftGenerateDialog from '../../components/api-case-drafts/ApiCaseDraftGenerateDialog.vue'
import CommonPagination from '../../components/common/CommonPagination.vue'
import ApiModuleSelect from '../../components/api-case-drafts/ApiModuleSelect.vue'
import ApiModuleDialog from '../../components/api-case-drafts/ApiModuleDialog.vue'
import ApiAuthSelect from '../../components/api-case-drafts/ApiAuthSelect.vue'
import { apiInterfaceColumns, apiInterfaceFields } from '../../resourceSchemas'
import { getApiModule, listApiModules } from '../../services/api-interface.service'
import { pageTabKey, usePageTabsStore } from '../../store/page-tabs'
import type { ApiModuleChange, ApiModuleSummary } from '../../types/api-interface'
import type { PageAction } from '../../types/page-actions'
import { useLatestRequest } from '../../composables/useLatestRequest'

const moduleBusy = ref(false)
const authLoading = ref(false)
const moduleDialogMode = ref<'create' | 'edit' | 'delete' | ''>('')
const editingModule = ref<ApiModuleSummary | null>(null)

function openModuleDialog(mode: 'create' | 'edit' | 'delete', module: ApiModuleSummary | null = null) {
  editingModule.value = module
  moduleDialogMode.value = mode
}

function handleDirectoryModuleChanged(change: ApiModuleChange) {
  modulePage.value = 1
  if (!change.deleted) moduleKeyword.value = ''
  handleModuleChanged(change)
}

function handleModuleChanged(change: ApiModuleChange) {
  if (change.id === activeModuleId.value && !change.deleted) activeModuleName.value = change.name
  if (activeModuleId.value) void resourcePageRef.value?.load()
  else void loadModules()
}

function handleInterfaceSaved() {
  if (activeModuleId.value) void resourcePageRef.value?.load()
  else void loadModules()
}

const actions: PageAction[] = [
  {
    label: '导入 OpenAPI',
    path: '',
    type: 'custom',
    name: 'openapi-import'
  },
  {
    label: 'OpenAPI 生成用例',
    path: '',
    type: 'custom',
    name: 'openapi-case-generation'
  }
]

const rowActions: PageAction[] = [
  {
    label: '详情',
    path: '/api/interfaces/{id}',
    type: 'route',
    payload: {
      project_id: '$project_id',
      module_id: '$data.module_id'
    }
  }
]

const route = useRoute()
const router = useRouter()
const pageTabsStore = usePageTabsStore()
const UNGROUPED_MODULE_KEY = '__ungrouped__'
const MODULE_PAGE_SIZE = 20
const resourcePageRef = ref<{ load: () => Promise<void>; openCreate: () => Promise<void> } | null>(null)
const importVisible = ref(false)
const importing = ref(false)
const importError = ref('')
const importTask = ref<OpenApiImportTask | null>(null)
const importResult = ref<OpenApiImportResult | null>(null)
const projects = ref<ProjectOption[]>([])
const projectFilterReady = ref(false)
const importForm = ref({
  projectId: '',
  sourceType: 'file' as 'file' | 'url',
  overwrite: true,
  file: null as File | null,
  url: ''
})
const openapiGenerationVisible = ref(false)
const modules = ref<ApiModuleSummary[]>([])
const moduleKeyword = ref('')
const modulePage = ref(1)
const modulePageSize = ref(MODULE_PAGE_SIZE)
const moduleTotal = ref(0)
const { loading: moduleLoading, error: moduleError, run: loadModuleRequest, cancel: cancelModuleLoad } = useLatestRequest('模块加载失败')
const activeModuleId = ref(0)
const activeModuleName = ref('')
const generationModuleId = ref(0)
const generationModuleName = ref('')
const httpMethods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']
const apiFilter = ref({
  projectId: 0,
  method: '',
  path: '',
  status: ''
})

const activeModuleLabel = computed(() => (
  activeModuleName.value || 'API 模块'
))
const apiDefaultValues = computed<Record<string, unknown>>(() => ({
  project_id: apiFilter.value.projectId || null,
  data: {
    module_id: activeModuleId.value || null
  }
}))

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
  if (activeModuleId.value) {
    params.module_id = activeModuleId.value
  }
  if (apiFilter.value.status) {
    params.status = apiFilter.value.status
  }
  return params
})

onMounted(async () => {
  try {
    projects.value = await listProjectOptions()
    const requestedProjectId = numberQueryValue(route.query.project_id)
    apiFilter.value.projectId = projects.value.some(item => item.id === requestedProjectId)
      ? requestedProjectId
      : resolveDefaultProjectId(projects.value)
  } finally {
    projectFilterReady.value = true
  }
  await replaceInvalidRouteState()
  const requestedModuleId = numberQueryValue(route.query.module_id)
  if (requestedModuleId) await loadActiveModule(requestedModuleId)
  else await loadModules()
})

watch(
  () => [route.query.project_id, route.query.module_id],
  async () => {
    const nextProjectId = numberQueryValue(route.query.project_id)
    const nextModuleId = numberQueryValue(route.query.module_id)
    pageTabsStore.setTitle(pageTabKey(route), nextModuleId ? 'API 列表' : 'API 管理')
    if (!projectFilterReady.value) return
    const validProjectId = projects.value.some(item => item.id === nextProjectId)
      ? nextProjectId
      : resolveDefaultProjectId(projects.value)
    if (validProjectId === apiFilter.value.projectId && nextModuleId === activeModuleId.value) return
    apiFilter.value.projectId = validProjectId
    resetInterfaceFilterValues()
    if (nextModuleId) await loadActiveModule(nextModuleId)
    else {
      clearActiveModule()
      await loadModules()
    }
  },
  { immediate: true }
)

async function handleCustomAction(action: PageAction) {
  if (action.name === 'openapi-case-generation') {
    if (!apiFilter.value.projectId) {
      apiFilter.value.projectId = resolveDefaultProjectId(projects.value)
    }
    generationModuleId.value = activeModuleId.value
    generationModuleName.value = activeModuleLabel.value
    openapiGenerationVisible.value = true
    return
  }
  await openImportDialog()
}

async function openImportDialog() {
  importError.value = ''
  importTask.value = null
  importResult.value = null
  if (!projects.value.length) {
    projects.value = await listProjectOptions()
  }
  importForm.value = {
    projectId: String(apiFilter.value.projectId || resolveDefaultProjectId(projects.value) || ''),
    sourceType: 'file',
    overwrite: true,
    file: null,
    url: ''
  }
  importVisible.value = true
}

async function resetApiFilters() {
  resetInterfaceFilterValues()
  await resourcePageRef.value?.load()
}

async function loadModules() {
  if (!apiFilter.value.projectId) {
    cancelModuleLoad()
    modules.value = []
    moduleTotal.value = 0
    return
  }
  await loadModuleRequest(signal => listApiModules({
      project_id: apiFilter.value.projectId,
      keyword: moduleKeyword.value || undefined,
      page: modulePage.value,
      pageSize: modulePageSize.value
    }, signal), result => {
    modules.value = result.items
    moduleTotal.value = result.total
    modulePage.value = result.page
    modulePageSize.value = result.pageSize
  })
}

async function searchModules() {
  modulePage.value = 1
  await loadModules()
}

async function resetModuleSearch() {
  moduleKeyword.value = ''
  modulePage.value = 1
  await loadModules()
}

async function handleModulePagination(page: number, pageSize: number) {
  modulePage.value = page
  modulePageSize.value = pageSize
  await loadModules()
}

async function handleProjectChange() {
  cancelModuleLoad()
  modules.value = []
  moduleTotal.value = 0
  clearActiveModule()
  moduleKeyword.value = ''
  modulePage.value = 1
  resetInterfaceFilterValues()
  await router.push({
    path: route.path,
    query: { project_id: String(apiFilter.value.projectId) }
  })
  await loadModules()
}

async function enterModule(moduleItem: ApiModuleSummary) {
  activeModuleId.value = moduleItem.id
  activeModuleName.value = moduleItem.name
  resetInterfaceFilterValues()
  await router.push({
    path: route.path,
    query: {
      project_id: String(apiFilter.value.projectId),
      module_id: String(moduleItem.id)
    }
  })
  pageTabsStore.setTitle(pageTabKey(route), 'API 列表')
}

async function leaveModule() {
  clearActiveModule()
  modulePage.value = 1
  resetInterfaceFilterValues()
  await router.push({
    path: route.path,
    query: { project_id: String(apiFilter.value.projectId) }
  })
  pageTabsStore.setTitle(pageTabKey(route), 'API 管理')
  await loadModules()
}

async function createInterfaceFromDirectory() {
  if (!apiFilter.value.projectId) {
    moduleError.value = '请选择项目'
    return
  }
  await resourcePageRef.value?.openCreate()
}

function openProjectGeneration() {
  generationModuleId.value = 0
  generationModuleName.value = ''
  openapiGenerationVisible.value = true
}

function closeGenerationDialog() {
  openapiGenerationVisible.value = false
  generationModuleId.value = 0
  generationModuleName.value = ''
}

async function loadActiveModule(moduleId: number) {
  try {
    const module = await getApiModule(apiFilter.value.projectId, moduleId)
    activeModuleId.value = module.id
    activeModuleName.value = module.name
    pageTabsStore.setTitle(pageTabKey(route), 'API 列表')
  } catch (error) {
    clearActiveModule()
    moduleError.value = getErrorMessage(error)
    await router.replace({
      path: route.path,
      query: { project_id: String(apiFilter.value.projectId) }
    })
    await loadModules()
  }
}

function clearActiveModule() {
  activeModuleId.value = 0
  activeModuleName.value = ''
}

function resetInterfaceFilterValues() {
  apiFilter.value.method = ''
  apiFilter.value.path = ''
  apiFilter.value.status = ''
}

async function replaceInvalidRouteState() {
  const projectId = apiFilter.value.projectId
  const currentProjectId = numberQueryValue(route.query.project_id)
  if (!projectId || currentProjectId === projectId) return
  const query: Record<string, string> = { project_id: String(projectId) }
  if (activeModuleId.value) query.module_id = String(activeModuleId.value)
  await router.replace({ path: route.path, query })
}

function numberQueryValue(value: unknown) {
  const text = Array.isArray(value) ? value[0] : value
  const number = Number(text || 0)
  return Number.isInteger(number) && number > 0 ? number : 0
}

function formatMethodCounts(counts: Record<string, number>) {
  return Object.entries(counts).map(([method, count]) => `${method} ${count}`).join(' / ') || '-'
}

function moduleStatus(item: ApiModuleSummary) {
  const states = []
  if (item.disabled_count) states.push(`停用 ${item.disabled_count}`)
  if (item.deprecated_count) states.push(`废弃 ${item.deprecated_count}`)
  return states.join(' / ') || '正常'
}

function moduleStatusClass(item: ApiModuleSummary) {
  return item.disabled_count || item.deprecated_count ? 'has-warning' : 'is-normal'
}

function formatUpdateTime(value: string) {
  if (!value) return '-'
  return value.replace('T', ' ').slice(0, 16)
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
    importError.value = '请上传 OpenAPI JSON/YAML 文件'
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
      if (importResult.value?.project_id === apiFilter.value.projectId) {
        await Promise.all([resourcePageRef.value?.load(), loadModules()])
      }
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

</script>

<style scoped>
.directory-create-host {
  display: contents;
}

.directory-create-host > :deep(:not(.modal-backdrop):not(.operation-toast)) {
  display: none;
}

.module-page {
  display: grid;
  gap: 16px;
}

.module-toolbar,
.module-filter-group,
.module-command-group,
.module-breadcrumb {
  display: flex;
  align-items: center;
  gap: 10px;
}

.module-toolbar {
  justify-content: space-between;
  flex-wrap: wrap;
  border-bottom: 1px solid #e3e8f1;
  padding-bottom: 14px;
}

.module-filter-group,
.module-command-group {
  flex-wrap: wrap;
}

.module-filter-group {
  flex: 1 1 510px;
}

.module-command-group {
  flex: 0 1 auto;
  justify-content: flex-end;
}

.module-toolbar select,
.module-toolbar input {
  width: 190px;
  height: 34px;
  border: 1px solid #d1d9e6;
  border-radius: 6px;
  background: #fff;
  color: #182230;
  padding: 0 10px;
}

.module-table-wrap {
  overflow: auto;
  border: 1px solid #dfe5ee;
  border-radius: 6px;
}

.module-table-wrap table {
  width: 100%;
  min-width: 820px;
  border-collapse: collapse;
}

.module-table-wrap th,
.module-table-wrap td {
  border-bottom: 1px solid #e8edf4;
  color: #334155;
  font-size: 13px;
  padding: 12px 14px;
  text-align: left;
}

.module-table-wrap th {
  background: #f7f9fc;
  color: #253247;
  font-weight: 700;
}

.module-table-wrap tbody tr:last-child td {
  border-bottom: 0;
}

.module-row {
  cursor: pointer;
}

.module-row:hover,
.module-row:focus-visible {
  background: #f3f8fb;
  outline: none;
}

.module-row td:first-child strong,
.module-row td:first-child small {
  display: block;
}

.module-row td:first-child strong {
  color: #172033;
  font-size: 14px;
}

.module-row td:first-child small {
  margin-top: 3px;
  color: #718096;
}

.count-column {
  width: 100px;
}

.status-column {
  width: 150px;
}

.time-column {
  width: 160px;
}

.enter-column {
  width: 150px;
}

.module-command-group > button,
.module-row-actions { display: flex; align-items: center; gap: 6px; }
.module-icon-button { display: grid; place-items: center; width: 30px; height: 30px; padding: 0; }

.method-summary {
  color: #285d72;
  font-variant-numeric: tabular-nums;
}

.module-status {
  font-weight: 600;
}

.module-status.is-normal {
  color: #166534;
}

.module-status.has-warning {
  color: #a16207;
}

.enter-button {
  min-width: 48px;
}

.module-empty {
  height: 140px;
  color: #718096;
  text-align: center !important;
}

.module-breadcrumb {
  color: #68758a;
  font-size: 13px;
}

.module-breadcrumb button {
  border: 0;
  background: transparent;
  color: #0f6073;
  padding: 0;
}

.module-breadcrumb button:first-child {
  width: 28px;
  height: 28px;
  border: 1px solid #d6dee9;
  border-radius: 6px;
  background: #fff;
  font-size: 18px;
}

.module-breadcrumb strong {
  color: #253247;
}

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

.status-filter {
  flex-basis: 120px;
  width: 120px;
  min-width: 108px;
}

.api-path-filter {
  flex-basis: 220px;
  width: 220px;
}

@media (max-width: 720px) {
  .module-toolbar select,
  .module-toolbar input {
    width: 100%;
  }

  .module-filter-group,
  .module-command-group {
    width: 100%;
    flex-basis: 100%;
    justify-content: flex-start;
  }

  .api-filter-select,
  .api-path-filter {
    width: 100%;
    min-width: 0;
  }
}
</style>
