<template>
  <section class="api-detail-page">
    <header class="detail-header">
      <nav class="detail-breadcrumb" aria-label="API 详情层级">
        <button type="button" aria-label="返回 API 列表" @click="goBack">←</button>
        <button type="button" @click="goBack">API 管理</button>
        <span>/</span>
        <span>{{ moduleName }}</span>
        <span>/</span>
        <strong>{{ interfaceItem?.name || 'API 详情' }}</strong>
      </nav>
      <div v-if="interfaceItem" class="api-identity">
        <span :class="['method-badge', methodClass]">{{ apiMethod }}</span>
        <code>{{ apiPath }}</code>
        <span :class="['status-text', interfaceItem.status === 'active' ? 'active' : 'inactive']">
          {{ statusText(interfaceItem.status) }}
        </span>
      </div>
    </header>

    <p v-if="detailLoading" class="page-state">正在加载 API 详情...</p>
    <div v-else-if="pageError" class="page-state error-state">
      <strong>API 详情加载失败</strong>
      <span>{{ pageError }}</span>
      <button type="button" @click="loadDetail">重试</button>
    </div>

    <div v-else-if="interfaceItem" ref="detailGrid" class="detail-grid" :class="{ 'auto-height': activeDetailTab !== 'parameters' || parameterHeightPreset === 'auto' }" :style="{ '--detail-height': `${availableDetailHeight}px` }">
      <header class="detail-tab-header">
        <nav class="case-kind-tabs" role="tablist" aria-label="API 详情选项卡">
          <button
            v-for="tab in detailTabs"
            :id="`api-detail-tab-${interfaceId}-${tab.value}`"
            :key="tab.value"
            type="button"
            role="tab"
            :class="{ active: activeDetailTab === tab.value }"
            :aria-selected="activeDetailTab === tab.value"
            :aria-controls="`api-detail-panel-${interfaceId}-${tab.value}`"
            :tabindex="activeDetailTab === tab.value ? 0 : -1"
            @click="activeDetailTab = tab.value"
            @keydown="handleDetailTabKey($event, tab.value)"
          >
            {{ tab.label }} <span>{{ tab.count }}</span>
          </button>
        </nav>
        <div class="case-header-actions">
          <button v-if="activeDetailTab === 'parameters'" type="button" @click="openCreateField">新增参数</button>
          <button v-if="activeDetailTab === 'cases'" type="button" @click="openCreateCase">新增用例</button>
          <button v-if="activeDetailTab !== 'parameters'" type="button" @click="caseGenerationVisible = true">生成用例草稿</button>
          <button type="button" @click="smartGenerationVisible = true">AI 生成用例</button>
        </div>
      </header>

      <section v-show="activeDetailTab === 'parameters'" :id="`api-detail-panel-${interfaceId}-parameters`" class="detail-panel parameter-panel" role="tabpanel" :aria-labelledby="`api-detail-tab-${interfaceId}-parameters`" tabindex="0">

        <nav class="location-tabs" aria-label="参数位置">
          <button
            v-for="tabItem in locationTabs"
            :key="tabItem.value"
            type="button"
            :class="{ active: fieldLocationFilter === tabItem.value }"
            @click="fieldLocationFilter = tabItem.value"
          >
            {{ tabItem.label }} <span>{{ tabItem.count }}</span>
          </button>
        </nav>

        <div class="parameter-height-controls">
          <label for="parameter-height-preset">列表高度</label>
          <select id="parameter-height-preset" v-model="parameterHeightPreset" aria-label="请求参数列表高度">
            <option value="auto">自适应窗口</option>
            <option value="compact">紧凑 · 320 px</option>
            <option value="standard">标准 · 480 px</option>
            <option value="large">展开 · 720 px</option>
            <option value="custom">自定义</option>
          </select>
          <label v-if="parameterHeightPreset === 'custom'" class="custom-height-input">
            <input v-model.number="parameterCustomHeight" type="number" min="240" max="1600" step="20" aria-label="自定义请求参数列表高度" @change="normalizeCustomHeight" />
            <span>px</span>
          </label>
          <button type="button" class="height-reset" aria-label="重置请求参数列表高度" title="重置列表高度" @click="resetParameterHeight">↺</button>
        </div>

        <p v-if="fieldMessage" class="panel-message" role="status">{{ fieldMessage }}</p>
        <p v-if="fieldError" class="panel-message error-text">{{ fieldError }}</p>

        <div class="panel-table-wrap parameter-table-wrap" :style="parameterHeightPreset === 'auto' ? undefined : { height: `${parameterTableHeight}px` }" tabindex="0" aria-label="请求参数列表">
          <table class="parameter-table">
            <colgroup>
              <col class="parameter-name-column" />
              <col class="parameter-location-column" />
              <col class="parameter-type-column" />
              <col class="parameter-required-column" />
              <col />
            </colgroup>
            <thead>
              <tr>
                <th>参数</th>
                <th>位置</th>
                <th>类型</th>
                <th>必填</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="field in filteredFields" :key="field.id">
                <td>
                  <strong>{{ field.name }}</strong>
                  <small>{{ fieldExample(field) }}</small>
                </td>
                <td>{{ locationLabel(fieldLocation(field)) }}</td>
                <td>{{ fieldType(field) }}</td>
                <td>{{ field.data.required ? '是' : '否' }}</td>
                <td>
                  <div class="compact-actions">
                    <button type="button" @click="openEditField(field)">编辑</button>
                    <button type="button" class="danger" @click="removeField(field)">删除</button>
                  </div>
                </td>
              </tr>
              <tr v-if="fieldLoading || !filteredFields.length">
                <td colspan="5" class="empty-cell">
                  {{ fieldLoading ? '参数加载中...' : fieldLocationFilter ? '当前位置暂无参数' : '暂无请求参数' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section v-show="activeDetailTab !== 'parameters'" :id="`api-detail-panel-${interfaceId}-${activeDetailTab === 'drafts' ? 'drafts' : 'cases'}`" class="detail-panel case-panel" role="tabpanel" :aria-labelledby="`api-detail-tab-${interfaceId}-${activeDetailTab === 'drafts' ? 'drafts' : 'cases'}`" tabindex="0">
        <template v-if="activeDetailTab === 'drafts'">
          <div class="case-toolbar">
            <input
              v-model.trim="draftKeyword"
              type="search"
              placeholder="搜索草稿名称"
              aria-label="搜索用例草稿"
              :disabled="draftActionRunning"
              @keyup.enter="searchDrafts"
            />
            <select v-model="draftStatus" :disabled="draftActionRunning" aria-label="按状态筛选用例草稿" @change="searchDrafts">
              <option value="">全部状态</option>
              <option value="draft">待审核</option>
              <option value="accepted">已采纳</option>
              <option value="rejected">已驳回</option>
            </select>
            <button type="button" :disabled="draftLoading || draftActionRunning" @click="searchDrafts">查询</button>
            <button type="button" :disabled="draftLoading || draftActionRunning || !hasDraftFilters" @click="resetDraftFilters">重置</button>
            <button type="button" class="icon-button" :disabled="draftLoading || draftActionRunning" aria-label="刷新用例草稿" title="刷新用例草稿" @click="loadDrafts">↻</button>
            <button type="button" :disabled="draftLoading || draftActionRunning || !selectedPendingDraftIds.length" @click="acceptSelectedDrafts">
              {{ draftActionRunning ? '处理中...' : `采纳选中（${selectedPendingDraftIds.length}）` }}
            </button>
            <button type="button" class="danger case-delete-action" title="删除选中的用例草稿" :disabled="draftLoading || draftActionRunning || !selectedDraftIds.length" @click="removeSelectedDrafts">
              <Trash2 :size="15" />{{ draftDeleting ? '删除中...' : `删除选中（${selectedDraftIds.length}）` }}
            </button>
          </div>

          <p v-if="draftMessage" class="panel-message" role="status">{{ draftMessage }}</p>
          <p v-if="draftError" class="panel-message error-text">{{ draftError }}</p>

          <div class="panel-table-wrap case-table-wrap">
            <table class="case-table draft-table">
              <colgroup>
                <col class="selection-column" />
                <col class="case-name-column" />
                <col class="priority-column" />
                <col class="status-column" />
                <col class="updated-column" />
                <col />
              </colgroup>
              <thead>
                <tr>
                  <th class="check-column">
                    <input type="checkbox" :checked="allDraftsSelected" :disabled="draftLoading || draftActionRunning" aria-label="选择当前页全部草稿" @change="toggleAllDrafts" />
                  </th>
                  <th>草稿名称</th>
                  <th>优先级</th>
                  <th>状态</th>
                  <th>更新时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="draft in drafts" :key="draft.id">
                  <td>
                    <input
                      v-model="selectedDraftIds"
                      type="checkbox"
                      :value="draft.id"
                      :disabled="draftLoading || draftActionRunning"
                      :aria-label="`选择 ${draft.name}`"
                    />
                  </td>
                  <td>
                    <strong>{{ draft.name }}</strong>
                    <small :title="draft.description || caseCategory(draft)">{{ draft.description || caseCategory(draft) }}</small>
                  </td>
                  <td>{{ casePriority(draft) }}</td>
                  <td>{{ statusText(draft.status) }}</td>
                  <td>{{ formatTime(draft.updated_at) }}</td>
                  <td>
                    <div class="compact-actions">
                      <button type="button" @click="selectedDraft = draft">详情</button>
                      <button type="button" :disabled="draftActionRunning || draft.status !== 'draft'" @click="acceptDrafts([draft.id])">采纳</button>
                      <button type="button" :disabled="draftActionRunning || draft.status !== 'draft'" @click="rejectDraft(draft)">驳回</button>
                      <button type="button" class="danger" :disabled="draftLoading || draftActionRunning" @click="removeDrafts([draft])">删除</button>
                    </div>
                  </td>
                </tr>
                <tr v-if="draftLoading || !drafts.length">
                  <td colspan="6" class="empty-cell">{{ draftLoading ? '草稿加载中...' : '暂无用例草稿' }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <CommonPagination
            :page="draftPage"
            :page-size="draftPageSize"
            :total="draftTotal"
            :loading="draftLoading || draftActionRunning"
            @change="handleDraftPagination"
          />
        </template>

        <template v-else>
          <div class="case-toolbar">
            <input
              v-model.trim="caseKeyword"
              type="search"
              placeholder="搜索用例名称"
              aria-label="搜索正式用例"
              @keyup.enter="searchCases"
            />
            <select v-model="caseStatus" aria-label="按状态筛选正式用例" @change="searchCases">
              <option value="">全部状态</option>
              <option value="active">启用</option>
              <option value="disabled">停用</option>
            </select>
            <button type="button" :disabled="caseLoading || caseDeleting" @click="searchCases">查询</button>
            <button type="button" :disabled="caseLoading || caseDeleting || !hasCaseFilters" @click="resetCaseFilters">重置</button>
            <button type="button" class="icon-button" :disabled="caseLoading || caseDeleting" aria-label="刷新正式用例" title="刷新正式用例" @click="loadCases">↻</button>
            <button type="button" :disabled="caseRunning || caseDeleting || caseLoading || !selectedCaseIds.length" @click="runSelectedCases">
              {{ caseRunning ? '执行中...' : `执行选中（${selectedCaseIds.length}）` }}
            </button>
            <button type="button" class="danger case-delete-action" title="删除选中的正式用例" :disabled="caseRunning || caseDeleting || caseLoading || !selectedCaseIds.length" @click="removeSelectedCases">
              <Trash2 :size="15" />{{ caseDeleting ? '删除中...' : `删除选中（${selectedCaseIds.length}）` }}
            </button>
          </div>

          <p v-if="caseMessage" class="panel-message" role="status">{{ caseMessage }}</p>
          <p v-if="caseError" class="panel-message error-text">{{ caseError }}</p>

          <div class="panel-table-wrap case-table-wrap">
            <table class="case-table formal-case-table">
              <colgroup>
                <col class="selection-column" />
                <col class="case-name-column" />
                <col class="priority-column" />
                <col class="status-column" />
                <col class="execution-column" />
                <col class="http-status-column" />
                <col class="response-code-column" />
                <col class="updated-column" />
                <col />
              </colgroup>
              <thead>
                <tr>
                  <th class="check-column">
                    <input type="checkbox" :checked="allCasesSelected" :disabled="caseLoading || caseDeleting" aria-label="选择当前页全部用例" @change="toggleAllCases" />
                  </th>
                  <th>用例名称</th>
                  <th>优先级</th>
                  <th>状态</th>
                  <th>最近执行</th>
                  <th>HTTP 状态</th>
                  <th>返回 code</th>
                  <th>更新时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="caseItem in cases" :key="caseItem.id">
                  <td><input v-model="selectedCaseIds" type="checkbox" :value="caseItem.id" :disabled="caseLoading || caseDeleting" :aria-label="`选择 ${caseItem.name}`" /></td>
                  <td>
                    <strong>{{ caseItem.name }}</strong>
                    <small :title="caseItem.description || caseCategory(caseItem)">{{ caseItem.description || caseCategory(caseItem) }}</small>
                  </td>
                  <td>{{ casePriority(caseItem) }}</td>
                  <td>{{ statusText(caseItem.status) }}</td>
                  <td><span class="case-execution-result" :class="`is-${caseItem.latest_execution?.status || 'idle'}`" :title="caseItem.latest_execution ? `执行时间：${formatTime(caseItem.latest_execution.executed_at)} · 记录 #${caseItem.latest_execution.record_id}` : ''">{{ caseExecutionLabel(caseItem) }}</span></td>
                  <td class="case-http-status">{{ caseItem.latest_execution?.http_status ?? '-' }}</td>
                  <td class="case-response-code" :title="caseResponseCode(caseItem)">{{ caseResponseCode(caseItem) }}</td>
                  <td>{{ formatTime(caseItem.updated_at) }}</td>
                  <td>
                    <div class="compact-actions">
                      <button type="button" @click="openCaseDetail(caseItem)">详情</button>
                      <button type="button" :disabled="caseDeleting" @click="openEditCase(caseItem)">编辑</button>
                      <button type="button" :disabled="caseDeleting" @click="openCopyCase(caseItem)">复制</button>
                      <button type="button" :disabled="caseRunning || caseDeleting || caseLoading" @click="runCases([caseItem.id])">执行</button>
                      <button type="button" class="danger case-delete-icon" :disabled="caseRunning || caseDeleting || caseLoading" :aria-label="`删除正式用例 ${caseItem.name}`" title="删除正式用例" @click="removeCases([caseItem])"><Trash2 :size="15" /></button>
                    </div>
                  </td>
                </tr>
                <tr v-if="caseLoading || !cases.length">
                  <td colspan="9" class="empty-cell">{{ caseLoading ? '用例加载中...' : '暂无正式用例' }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <CommonPagination
            :page="casePage"
            :page-size="casePageSize"
            :total="caseTotal"
            :loading="caseLoading || caseDeleting"
            @change="handleCasePagination"
          />
        </template>
      </section>
    </div>

    <div v-if="fieldDialogVisible" class="modal-backdrop" @click.self="closeFieldDialog">
      <section class="modal-panel field-dialog" role="dialog" aria-modal="true">
        <header class="modal-header">
          <h3>{{ editingField ? '编辑参数' : '新增参数' }}</h3>
          <button class="modal-close" type="button" aria-label="关闭" @click="closeFieldDialog">×</button>
        </header>
        <form class="modal-form" @submit.prevent="submitField">
          <div class="form-grid">
            <label class="field">
              <span>参数名称<b>*</b></span>
              <input v-model.trim="fieldForm.name" placeholder="例如：userId" />
            </label>
            <label class="field">
              <span>参数位置<b>*</b></span>
              <select v-model="fieldForm.location">
                <option v-for="item in fieldLocationOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
              </select>
            </label>
            <label class="field">
              <span>字段类型</span>
              <select v-model="fieldForm.fieldType">
                <option v-for="type in fieldTypeOptions" :key="type" :value="type">{{ type }}</option>
              </select>
            </label>
            <label class="field checkbox-form-field">
              <span>是否必填</span>
              <span><input v-model="fieldForm.required" type="checkbox" /> {{ fieldForm.required ? '是' : '否' }}</span>
            </label>
            <label class="field">
              <span>示例值</span>
              <DynamicValueInput v-model="fieldForm.example" label="参数示例值" />
            </label>
            <label class="field">
              <span>默认值</span>
              <DynamicValueInput v-model="fieldForm.defaultValue" label="参数默认值" />
            </label>
            <label class="field">
              <span>状态</span>
              <select v-model="fieldForm.status">
                <option value="active">启用</option>
                <option value="disabled">停用</option>
              </select>
            </label>
            <label class="field full">
              <span>校验/生成规则</span>
              <textarea v-model.trim="fieldForm.rule" rows="3"></textarea>
            </label>
            <label class="field full">
              <span>说明</span>
              <textarea v-model.trim="fieldForm.description" rows="3"></textarea>
            </label>
          </div>
          <p v-if="fieldFormError" class="form-error">{{ fieldFormError }}</p>
          <footer class="modal-actions">
            <button type="button" @click="closeFieldDialog">取消</button>
            <button type="submit" :disabled="fieldSaving">{{ fieldSaving ? '保存中...' : '保存' }}</button>
          </footer>
        </form>
      </section>
    </div>

    <ResultDetailDialog v-if="selectedCase" :title="selectedCase.name" @close="selectedCase = null">
      <ApiCaseDetailContent :item="selectedCase" />
      <template #footer>
          <button type="button" class="danger case-delete-action" :disabled="caseRunning || caseDeleting || caseLoading" @click="removeCases([selectedCase])"><Trash2 :size="15" />{{ caseDeleting ? '删除中...' : '删除用例' }}</button>
          <button type="button" @click="selectedCase = null">关闭</button>
      </template>
    </ResultDetailDialog>

    <ResultDetailDialog v-if="selectedDraft" :title="`草稿详情：${selectedDraft.name}`" @close="selectedDraft = null">
      <ApiCaseDetailContent :item="selectedDraft" :show-execution="false" />
    </ResultDetailDialog>

    <ApiCaseFormDialog
      v-if="interfaceItem"
      :visible="caseFormVisible"
      :interface-item="interfaceItem"
      :fields="fields"
      :item="editingCase"
      :copying="copyingCase"
      @close="caseFormVisible = false"
      @saved="handleCaseSaved"
    />

    <ApiCaseDraftGenerateDialog
      :visible="caseGenerationVisible"
      :initial-project-id="projectId"
      :initial-interface-ids="[interfaceId]"
      @close="caseGenerationVisible = false"
      @generated="handleCasesGenerated"
    />
    <BusinessGenerationDrawer v-if="interfaceItem" :visible="smartGenerationVisible" domain="API" :source-id="interfaceId" :source-name="interfaceItem.name" @close="smartGenerationVisible = false" @saved="loadDetail" />
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Trash2 } from 'lucide-vue-next'

import ApiCaseDraftGenerateDialog from '../../components/api-case-drafts/ApiCaseDraftGenerateDialog.vue'
import BusinessGenerationDrawer from '../../components/generation/BusinessGenerationDrawer.vue'
import ApiCaseFormDialog from '../../components/api-case-drafts/ApiCaseFormDialog.vue'
import DynamicValueInput from '../../components/common/DynamicValueInput.vue'
import CommonPagination from '../../components/common/CommonPagination.vue'
import ApiCaseDetailContent from '../../components/resource/ApiCaseDetailContent.vue'
import ResultDetailDialog from '../../components/common/ResultDetailDialog.vue'
import { ExecutionMode } from '../../constants/enums'
import { runApiCases } from '../../services/api-case.service'
import { pageTabKey, usePageTabsStore } from '../../store/page-tabs'
import {
  batchDeleteResources,
  createResource,
  deleteResource,
  getResource,
  listResources,
  postAction,
  updateResource
} from '../../services/resource.service'
import type { ResourceItem, ResourcePayload } from '../../types/resource'
import type { OpenApiCaseGenerationResult } from '../../types/openapi-schema'

type FieldLocation = '' | 'path' | 'query' | 'header' | 'body' | 'cookie'
type DetailTab = 'parameters' | 'drafts' | 'cases'
type ParameterHeightPreset = 'auto' | 'compact' | 'standard' | 'large' | 'custom'

const PARAMETER_HEIGHT_STORAGE_KEY = 'autotest.api.parameter-table-height'
const storedParameterHeight = readParameterHeight()
const parameterHeightPreset = ref<ParameterHeightPreset>(storedParameterHeight.preset)
const parameterCustomHeight = ref(storedParameterHeight.customHeight)
const detailGrid = ref<HTMLElement | null>(null)
const availableDetailHeight = ref(600)
let layoutObserver: ResizeObserver | undefined
const parameterTableHeight = computed(() => (
  parameterHeightPreset.value === 'custom'
    ? clampParameterHeight(parameterCustomHeight.value)
    : { auto: 480, compact: 320, standard: 480, large: 720 }[parameterHeightPreset.value]
))

const route = useRoute()
const router = useRouter()
const pageTabsStore = usePageTabsStore()
const interfaceItem = ref<ResourceItem | null>(null)
const smartGenerationVisible = ref(false)
const fields = ref<ResourceItem[]>([])
const drafts = ref<ResourceItem[]>([])
const cases = ref<ResourceItem[]>([])
const detailLoading = ref(false)
const fieldLoading = ref(false)
const draftLoading = ref(false)
const caseLoading = ref(false)
const pageError = ref('')
const fieldError = ref('')
const fieldMessage = ref('')
const draftError = ref('')
const draftMessage = ref('')
const caseError = ref('')
const caseMessage = ref('')
const fieldLocationFilter = ref<FieldLocation>('')
const activeDetailTab = ref<DetailTab>('cases')
const draftKeyword = ref('')
const draftStatus = ref('draft')
const draftPage = ref(1)
const draftPageSize = ref(10)
const draftTotal = ref(0)
const selectedDraftIds = ref<number[]>([])
const selectedDraft = ref<ResourceItem | null>(null)
const draftActionRunning = ref(false)
const draftDeleting = ref(false)
let draftLoadSequence = 0
const caseKeyword = ref('')
const caseStatus = ref('')
const casePage = ref(1)
const casePageSize = ref(10)
const caseTotal = ref(0)
const selectedCaseIds = ref<number[]>([])
const selectedCase = ref<ResourceItem | null>(null)
const caseRunning = ref(false)
const caseDeleting = ref(false)
let caseLoadSequence = 0
const caseGenerationVisible = ref(false)
const caseFormVisible = ref(false)
const editingCase = ref<ResourceItem | null>(null)
const copyingCase = ref(false)
const fieldDialogVisible = ref(false)
const editingField = ref<ResourceItem | null>(null)
const fieldSaving = ref(false)
const fieldFormError = ref('')

const fieldLocationOptions: Array<{ value: Exclude<FieldLocation, ''>; label: string }> = [
  { value: 'path', label: 'Path' },
  { value: 'query', label: 'Query' },
  { value: 'header', label: 'Header' },
  { value: 'body', label: 'Body' },
  { value: 'cookie', label: 'Cookie' }
]
const fieldTypeOptions = ['string', 'integer', 'number', 'boolean', 'object', 'array']
const fieldForm = reactive({
  name: '',
  location: 'query' as Exclude<FieldLocation, ''>,
  fieldType: 'string',
  required: false,
  example: '',
  defaultValue: '',
  rule: '',
  status: 'active',
  description: ''
})

const interfaceId = computed(() => positiveInteger(route.params.interfaceId))
const projectId = computed(() => positiveInteger(interfaceItem.value?.project_id) || positiveInteger(route.query.project_id))
const moduleId = computed(() => positiveInteger(interfaceItem.value?.data.module_id) || positiveInteger(route.query.module_id))
const moduleName = computed(() => String(interfaceItem.value?.data.module || '未分组'))
const apiMethod = computed(() => String(interfaceItem.value?.data.method || '-').toUpperCase())
const apiPath = computed(() => String(interfaceItem.value?.data.path || '-'))
const methodClass = computed(() => `method-${apiMethod.value.toLowerCase()}`)
const filteredFields = computed(() => fields.value.filter(item => (
  !fieldLocationFilter.value || fieldLocation(item) === fieldLocationFilter.value
)))
const locationTabs = computed(() => [
  { value: '' as FieldLocation, label: '全部', count: fields.value.length },
  ...fieldLocationOptions.map(item => ({
    ...item,
    count: fields.value.filter(field => fieldLocation(field) === item.value).length
  }))
])
const allCasesSelected = computed(() => (
  cases.value.length > 0 && cases.value.every(item => selectedCaseIds.value.includes(item.id))
))
const selectedPendingDraftIds = computed(() => drafts.value
  .filter(item => item.status === 'draft' && selectedDraftIds.value.includes(item.id)).map(item => item.id))
const allDraftsSelected = computed(() => (
  drafts.value.length > 0 && drafts.value.every(item => selectedDraftIds.value.includes(item.id))
))
const hasDraftFilters = computed(() => Boolean(draftKeyword.value || draftStatus.value !== 'draft'))
const hasCaseFilters = computed(() => Boolean(caseKeyword.value || caseStatus.value))
const detailTabs = computed<Array<{ value: DetailTab; label: string; count: number }>>(() => [
  { value: 'parameters', label: '请求参数', count: fields.value.length },
  { value: 'drafts', label: '用例草稿', count: draftTotal.value },
  { value: 'cases', label: '正式用例', count: caseTotal.value }
])

function handleDetailTabKey(event: KeyboardEvent, current: DetailTab) {
  const keys = ['ArrowLeft', 'ArrowRight', 'Home', 'End']
  if (!keys.includes(event.key)) return
  event.preventDefault()
  const tabs = detailTabs.value
  const index = tabs.findIndex(tab => tab.value === current)
  const next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1
    : (index + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length
  activeDetailTab.value = tabs[next].value
  const tablist = (event.currentTarget as HTMLElement).closest('[role="tablist"]')
  tablist?.querySelectorAll<HTMLButtonElement>('[role="tab"]')[next]?.focus()
}

onMounted(() => {
  window.addEventListener('resize', updateDetailHeight)
  void loadDetail()
})
watch(detailGrid, element => {
  layoutObserver?.disconnect()
  if (!element) return
  layoutObserver = new ResizeObserver(updateDetailHeight)
  const content = element.closest('.content')
  for (const target of [element.previousElementSibling, content?.querySelector('.content-topbar')]) {
    if (target) layoutObserver.observe(target)
  }
  updateDetailHeight()
}, { flush: 'post' })
onBeforeUnmount(() => {
  window.removeEventListener('resize', updateDetailHeight)
  layoutObserver?.disconnect()
})

function updateDetailHeight() {
  const element = detailGrid.value
  if (!element) return
  const content = element.closest('.content')
  const bottomPadding = content ? parseFloat(getComputedStyle(content).paddingBottom) || 0 : 28
  availableDetailHeight.value = Math.max(420, Math.floor(window.innerHeight - element.getBoundingClientRect().top - window.scrollY - bottomPadding))
}
watch(interfaceId, () => {
  activeDetailTab.value = 'cases'
  void loadDetail()
})
watch([parameterHeightPreset, parameterCustomHeight], () => {
  try {
    localStorage.setItem(PARAMETER_HEIGHT_STORAGE_KEY, JSON.stringify({
      preset: parameterHeightPreset.value, customHeight: clampParameterHeight(parameterCustomHeight.value)
    }))
  } catch { /* Keep the height usable when browser storage is unavailable. */ }
})

function clampParameterHeight(value: unknown) {
  const height = Number(value)
  return Number.isFinite(height) && height > 0 ? Math.min(1600, Math.max(240, Math.round(height))) : 480
}

function readParameterHeight(): { preset: ParameterHeightPreset; customHeight: number } {
  try {
    const saved = JSON.parse(localStorage.getItem(PARAMETER_HEIGHT_STORAGE_KEY) || '{}')
    if (saved && ['auto', 'compact', 'standard', 'large', 'custom'].includes(saved.preset)) {
      return { preset: saved.preset, customHeight: clampParameterHeight(saved.customHeight) }
    }
  } catch { /* Invalid preferences fall back to the standard height. */ }
  return { preset: 'auto', customHeight: 480 }
}

function normalizeCustomHeight() { parameterCustomHeight.value = clampParameterHeight(parameterCustomHeight.value) }
function resetParameterHeight() { parameterHeightPreset.value = 'auto'; parameterCustomHeight.value = 480 }

async function loadDetail() {
  pageTabsStore.setTitle(pageTabKey(route), 'API 详情')
  if (!interfaceId.value) {
    pageError.value = 'API ID 不合法'
    return
  }
  detailLoading.value = true
  pageError.value = ''
  try {
    interfaceItem.value = await getResource('/api-testing/interfaces', interfaceId.value)
    pageTabsStore.setTitle(pageTabKey(route), 'API 详情')
    await Promise.all([loadFields(), loadDrafts(), loadCases()])
  } catch (error) {
    interfaceItem.value = null
    pageError.value = errorMessage(error, 'API 详情加载失败')
  } finally {
    detailLoading.value = false
  }
}

async function loadFields() {
  fieldLoading.value = true
  fieldError.value = ''
  try {
    const firstPage = await listResources('/api-testing/fields', {
      project_id: projectId.value || undefined,
      interface_id: interfaceId.value,
      page: 1,
      pageSize: 200
    })
    const result = [...firstPage.items]
    const totalPages = Math.ceil(firstPage.total / firstPage.pageSize)
    for (let page = 2; page <= totalPages; page += 1) {
      const nextPage = await listResources('/api-testing/fields', {
        project_id: projectId.value || undefined,
        interface_id: interfaceId.value,
        page,
        pageSize: 200
      })
      result.push(...nextPage.items)
    }
    fields.value = result
  } catch (error) {
    fields.value = []
    fieldError.value = errorMessage(error, '请求参数加载失败')
  } finally {
    fieldLoading.value = false
  }
}

async function loadDrafts() {
  const sequence = ++draftLoadSequence
  const origin = interfaceId.value
  draftLoading.value = true
  draftError.value = ''
  try {
    const result = await listResources('/api-testing/case-drafts', {
      project_id: projectId.value || undefined,
      source_id: interfaceId.value,
      keyword: draftKeyword.value || undefined,
      status: draftStatus.value || undefined,
      page: draftPage.value,
      pageSize: draftPageSize.value
    })
    if (sequence !== draftLoadSequence || origin !== interfaceId.value) return
    const lastPage = Math.max(1, Math.ceil(result.total / result.pageSize))
    if (result.page > lastPage) { draftPage.value = lastPage; await loadDrafts(); return }
    drafts.value = result.items
    draftTotal.value = result.total
    draftPage.value = result.page
    draftPageSize.value = result.pageSize
    selectedDraftIds.value = []
  } catch (error) {
    if (sequence !== draftLoadSequence || origin !== interfaceId.value) return
    drafts.value = []
    draftTotal.value = 0
    draftError.value = errorMessage(error, '用例草稿加载失败')
  } finally {
    if (sequence === draftLoadSequence) draftLoading.value = false
  }
}

async function searchDrafts() {
  if (draftActionRunning.value) return
  draftPage.value = 1
  await loadDrafts()
}

async function resetDraftFilters() {
  if (draftActionRunning.value) return
  draftKeyword.value = ''
  draftStatus.value = 'draft'
  draftPage.value = 1
  await loadDrafts()
}

async function handleDraftPagination(page: number, pageSize: number) {
  if (draftActionRunning.value) return
  draftPage.value = page
  draftPageSize.value = pageSize
  await loadDrafts()
}

function toggleAllDrafts(event: Event) {
  selectedDraftIds.value = (event.target as HTMLInputElement).checked
    ? drafts.value.map(item => item.id)
    : []
}

async function acceptSelectedDrafts() {
  await acceptDrafts([...selectedPendingDraftIds.value])
}

async function acceptDrafts(ids: number[]) {
  if (!ids.length || draftActionRunning.value || draftLoading.value) return
  draftActionRunning.value = true
  draftError.value = ''
  draftMessage.value = ''
  try {
    const result = await postAction<{ accepted_count: number; skipped_count: number }>('/api-testing/case-drafts/accept', { ids })
    draftMessage.value = `已采纳 ${result.accepted_count} 条草稿${result.skipped_count ? `，跳过 ${result.skipped_count} 条` : ''}`
    await Promise.all([loadDrafts(), loadCases()])
  } catch (error) {
    draftError.value = errorMessage(error, '草稿采纳失败')
  } finally {
    draftActionRunning.value = false
  }
}

async function rejectDraft(item: ResourceItem) {
  if (draftActionRunning.value || draftLoading.value || item.status !== 'draft') return
  if (!window.confirm(`确认驳回草稿“${item.name}”吗？`)) return
  draftActionRunning.value = true
  draftError.value = ''
  draftMessage.value = ''
  try {
    await postAction(`/api-testing/case-drafts/${item.id}/reject`, { review_comment: '手动驳回' })
    draftMessage.value = `草稿“${item.name}”已驳回`
    await loadDrafts()
  } catch (error) {
    draftError.value = errorMessage(error, '草稿驳回失败')
  } finally {
    draftActionRunning.value = false
  }
}

async function removeSelectedDrafts() {
  await removeDrafts(drafts.value.filter(item => selectedDraftIds.value.includes(item.id)))
}

async function removeDrafts(items: ResourceItem[]) {
  if (!items.length || draftActionRunning.value || draftLoading.value) return
  const ids = [...new Set(items.map(item => item.id))]
  const target = ids.length === 1 ? `草稿“${items[0].name}”` : `选中的 ${ids.length} 条草稿`
  if (!window.confirm(`确认删除${target}吗？删除后无法恢复，已采纳的正式用例不受影响。`)) return
  const origin = interfaceId.value
  draftActionRunning.value = true
  draftDeleting.value = true
  draftError.value = ''
  draftMessage.value = ''
  try {
    let count = 1
    if (ids.length === 1) await deleteResource('/api-testing/case-drafts', ids[0])
    else count = (await batchDeleteResources('/api-testing/case-drafts', ids)).deleted_count
    if (origin !== interfaceId.value) return
    if (selectedDraft.value && ids.includes(selectedDraft.value.id)) selectedDraft.value = null
    selectedDraftIds.value = []
    draftMessage.value = `已删除 ${count} 条草稿`
    await loadDrafts()
  } catch (error) {
    if (origin === interfaceId.value) draftError.value = errorMessage(error, '草稿删除失败')
  } finally {
    draftDeleting.value = false
    draftActionRunning.value = false
  }
}

async function loadCases() {
  const sequence = ++caseLoadSequence
  caseLoading.value = true
  caseError.value = ''
  try {
    const result = await listResources('/api-testing/cases', {
      project_id: projectId.value || undefined,
      source_id: interfaceId.value,
      keyword: caseKeyword.value || undefined,
      status: caseStatus.value || undefined,
      page: casePage.value,
      pageSize: casePageSize.value,
      include_latest_execution: true
    })
    if (sequence !== caseLoadSequence) return
    const lastPage = Math.max(1, Math.ceil(result.total / result.pageSize))
    if (result.page > lastPage) { casePage.value = lastPage; await loadCases(); return }
    cases.value = result.items
    caseTotal.value = result.total
    casePage.value = result.page
    casePageSize.value = result.pageSize
    selectedCaseIds.value = []
  } catch (error) {
    if (sequence !== caseLoadSequence) return
    cases.value = []
    caseTotal.value = 0
    caseError.value = errorMessage(error, '正式用例加载失败')
  } finally {
    if (sequence === caseLoadSequence) caseLoading.value = false
  }
}

async function searchCases() {
  casePage.value = 1
  await loadCases()
}

async function resetCaseFilters() {
  caseKeyword.value = ''
  caseStatus.value = ''
  casePage.value = 1
  await loadCases()
}

async function handleCasePagination(page: number, pageSize: number) {
  casePage.value = page
  casePageSize.value = pageSize
  await loadCases()
}

function toggleAllCases(event: Event) {
  selectedCaseIds.value = (event.target as HTMLInputElement).checked ? cases.value.map(item => item.id) : []
}

async function runSelectedCases() {
  await runCases([...selectedCaseIds.value])
}

async function runCases(caseIds: number[]) {
  if (!caseIds.length || caseRunning.value || caseDeleting.value || caseLoading.value) return
  caseRunning.value = true
  caseError.value = ''
  caseMessage.value = ''
  try {
    await runApiCases({
      project_id: projectId.value,
      case_ids: caseIds,
      mode: ExecutionMode.LOCAL_HEADLESS
    })
    caseMessage.value = `已提交 ${caseIds.length} 条正式用例执行`
    await loadCases()
  } catch (error) {
    caseError.value = errorMessage(error, '用例执行失败')
  } finally {
    caseRunning.value = false
  }
}

async function removeSelectedCases() {
  await removeCases(cases.value.filter(item => selectedCaseIds.value.includes(item.id)))
}

async function removeCases(items: ResourceItem[]) {
  if (!items.length || caseDeleting.value || caseRunning.value || caseLoading.value) return
  const ids = [...new Set(items.map(item => item.id))]
  const target = ids.length === 1 ? `正式用例“${items[0].name}”` : `选中的 ${ids.length} 条正式用例`
  if (!window.confirm(`确认删除${target}吗？删除后无法从页面恢复，历史执行记录保留。引用这些用例的流程或鉴权配置需重新选择用例。`)) return
  const origin = interfaceId.value
  caseDeleting.value = true
  caseError.value = ''; caseMessage.value = ''
  try {
    let count = 1
    if (ids.length === 1) await deleteResource('/api-testing/cases', ids[0])
    else count = (await batchDeleteResources('/api-testing/cases', ids)).deleted_count
    if (origin !== interfaceId.value) return
    if (selectedCase.value && ids.includes(selectedCase.value.id)) selectedCase.value = null
    if (editingCase.value && ids.includes(editingCase.value.id)) { editingCase.value = null; caseFormVisible.value = false }
    selectedCaseIds.value = []
    caseMessage.value = `已删除 ${count} 条正式用例`
    await loadCases()
  } catch (error) {
    if (origin === interfaceId.value) caseError.value = errorMessage(error, '正式用例删除失败')
  } finally {
    caseDeleting.value = false
  }
}

function caseExecutionLabel(item: ResourceItem) {
  const labels: Record<string, string> = {success: '成功', failed: '失败', exception: '异常', queued: '排队中', running: '执行中', cancelled: '已取消', skipped: '已跳过'}
  const status = item.latest_execution?.status
  return status ? labels[status] || '异常' : '未执行'
}

function caseResponseCode(item: ResourceItem) {
  const value = item.latest_execution?.response_code
  return value == null ? '-' : typeof value === 'object' ? JSON.stringify(value) : String(value)
}

function openCaseDetail(item: ResourceItem) {
  selectedCase.value = item
}

function openCreateCase() {
  editingCase.value = null
  copyingCase.value = false
  caseFormVisible.value = true
}

function openEditCase(item: ResourceItem) {
  editingCase.value = item
  copyingCase.value = false
  caseFormVisible.value = true
}

function openCopyCase(item: ResourceItem) {
  editingCase.value = item
  copyingCase.value = true
  caseFormVisible.value = true
}

async function handleCaseSaved(item: ResourceItem) {
  caseFormVisible.value = false
  activeDetailTab.value = 'cases'
  caseKeyword.value = ''
  caseStatus.value = ''
  casePage.value = 1
  caseMessage.value = `用例“${item.name}”已保存`
  await loadCases()
}

async function handleCasesGenerated(result: OpenApiCaseGenerationResult) {
  caseGenerationVisible.value = false
  activeDetailTab.value = 'drafts'
  draftKeyword.value = ''
  draftStatus.value = ''
  draftPage.value = 1
  draftMessage.value = `已新增 ${result.created_count} 条、更新 ${result.updated_count} 条，跳过 ${result.skipped_count} 条已有草稿`
  await loadDrafts()
}

function openCreateField() {
  editingField.value = null
  resetFieldForm()
  fieldDialogVisible.value = true
}

function openEditField(item: ResourceItem) {
  editingField.value = item
  fieldForm.name = item.name
  fieldForm.location = normalizeFieldLocation(item.data.location)
  fieldForm.fieldType = String(item.data.field_type || item.data.type || 'string')
  fieldForm.required = Boolean(item.data.required)
  fieldForm.example = editableValue(item.data.example)
  fieldForm.defaultValue = editableValue(item.data.default_value)
  fieldForm.rule = editableValue(item.data.rule)
  fieldForm.status = item.status || 'active'
  fieldForm.description = String(item.description || '')
  fieldFormError.value = ''
  fieldDialogVisible.value = true
}

function closeFieldDialog() {
  if (fieldSaving.value) return
  fieldDialogVisible.value = false
  fieldFormError.value = ''
}

async function submitField() {
  if (!fieldForm.name) {
    fieldFormError.value = '请填写参数名称'
    return
  }
  fieldSaving.value = true
  fieldFormError.value = ''
  try {
    const existingData = editingField.value?.data || {}
    const payload: ResourcePayload = {
      name: fieldForm.name,
      project_id: projectId.value,
      description: fieldForm.description || null,
      status: fieldForm.status,
      data: {
        ...existingData,
        name: fieldForm.name,
        interface_id: interfaceId.value,
        location: fieldForm.location,
        field_type: fieldForm.fieldType,
        type: fieldForm.fieldType,
        required: fieldForm.required,
        example: fieldForm.example || null,
        default_value: fieldForm.defaultValue || null,
        rule: fieldForm.rule || null
      }
    }
    if (editingField.value) {
      await updateResource('/api-testing/fields', editingField.value.id, payload)
      fieldMessage.value = '参数已更新'
    } else {
      await createResource('/api-testing/fields', payload)
      fieldMessage.value = '参数已新增'
    }
    fieldDialogVisible.value = false
    await loadFields()
  } catch (error) {
    fieldFormError.value = errorMessage(error, '参数保存失败')
  } finally {
    fieldSaving.value = false
  }
}

async function removeField(item: ResourceItem) {
  fieldError.value = ''
  try {
    await deleteResource('/api-testing/fields', item.id)
    fieldMessage.value = `参数“${item.name}”已删除`
    await loadFields()
  } catch (error) {
    fieldError.value = errorMessage(error, '参数删除失败')
  }
}

function resetFieldForm() {
  fieldForm.name = ''
  fieldForm.location = 'query'
  fieldForm.fieldType = 'string'
  fieldForm.required = false
  fieldForm.example = ''
  fieldForm.defaultValue = ''
  fieldForm.rule = ''
  fieldForm.status = 'active'
  fieldForm.description = ''
  fieldFormError.value = ''
}

function goBack() {
  const query: Record<string, string> = {}
  if (projectId.value) query.project_id = String(projectId.value)
  if (moduleId.value) query.module_id = String(moduleId.value)
  void router.replace({ path: '/api/interfaces', query })
}

function fieldLocation(item: ResourceItem): Exclude<FieldLocation, ''> {
  return normalizeFieldLocation(item.data.location)
}

function normalizeFieldLocation(value: unknown): Exclude<FieldLocation, ''> {
  const normalized = String(value || 'body').toLowerCase()
  return fieldLocationOptions.some(item => item.value === normalized)
    ? normalized as Exclude<FieldLocation, ''>
    : 'body'
}

function fieldType(item: ResourceItem) {
  return String(item.data.field_type || item.data.type || 'string')
}

function fieldExample(item: ResourceItem) {
  const value = item.data.example ?? item.data.default_value
  return value == null || value === '' ? '无示例值' : `示例：${displayValue(value)}`
}

function locationLabel(value: string) {
  return fieldLocationOptions.find(item => item.value === value)?.label || value
}

function casePriority(item: ResourceItem) {
  return String(item.data.priority || 'P2')
}

function caseCategory(item: ResourceItem) {
  return String(item.data.category || item.data.case_type || 'API')
}

function statusText(value: unknown) {
  const labels: Record<string, string> = {
    active: '启用',
    disabled: '停用',
    archived: '归档',
    draft: '待审核',
    accepted: '已采纳',
    rejected: '已驳回'
  }
  return labels[String(value || '')] || String(value || '-')
}

function formatTime(value: unknown) {
  const text = String(value || '')
  return text ? text.replace('T', ' ').slice(0, 16) : '-'
}

function positiveInteger(value: unknown) {
  const raw = Array.isArray(value) ? value[0] : value
  const result = Number(raw || 0)
  return Number.isInteger(result) && result > 0 ? result : 0
}

function editableValue(value: unknown) {
  if (value == null) return ''
  return typeof value === 'object' ? JSON.stringify(value) : String(value)
}

function displayValue(value: unknown) {
  return typeof value === 'object' ? JSON.stringify(value) : String(value)
}

function errorMessage(error: unknown, fallback: string) {
  return error instanceof Error && error.message ? error.message : fallback
}
</script>

<style scoped>
.api-detail-page {
  display: grid;
  gap: 18px;
}

.detail-header,
.panel-header,
.case-toolbar,
.detail-breadcrumb,
.api-identity,
.compact-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.detail-header {
  align-items: stretch;
  flex-direction: column;
  border-bottom: 1px solid #dfe5ee;
  padding-bottom: 18px;
}

.panel-header p {
  margin: 5px 0 0;
  color: #68758a;
  font-size: 13px;
}

.detail-breadcrumb {
  flex-wrap: wrap;
  color: #68758a;
  font-size: 13px;
}

.detail-breadcrumb button {
  border: 0;
  background: transparent;
  color: #0f6073;
  padding: 0;
}

.detail-breadcrumb button:first-child {
  width: 28px;
  height: 28px;
  border: 1px solid #d6dee9;
  border-radius: 6px;
  background: #ffffff;
  font-size: 18px;
}

.detail-breadcrumb strong {
  max-width: 280px;
  overflow: hidden;
  color: #253247;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.api-identity {
  width: 100%;
  flex-wrap: wrap;
  justify-content: flex-start;
  min-width: 0;
}

.api-identity code {
  max-width: 100%;
  color: #24324a;
  font-size: 13px;
  overflow-wrap: anywhere;
  white-space: normal;
}

.method-badge {
  min-width: 58px;
  border-radius: 4px;
  padding: 5px 8px;
  color: #ffffff;
  font-size: 12px;
  font-weight: 700;
  text-align: center;
}

.method-get { background: #147d64; }
.method-post { background: #1d65b7; }
.method-put,
.method-patch { background: #9a6700; }
.method-delete { background: #b42318; }

.status-text {
  font-weight: 600;
  white-space: nowrap;
}

.status-text.active { color: #166534; }
.status-text.inactive { color: #9a3412; }

.detail-grid {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.detail-grid.auto-height { height: var(--detail-height); }
.detail-panel { display: flex; flex: 1 1 0; flex-direction: column; min-height: 0; }
.detail-panel > :not(.panel-table-wrap) { flex-shrink: 0; }
.auto-height .parameter-table-wrap { flex: 1 1 0; min-height: 0; }
.case-table-wrap { flex: 1 1 auto; min-height: 0; overflow: auto; }
.case-table th { position: sticky; top: 0; z-index: 1; box-shadow: 0 1px #e5eaf2; }

.detail-panel {
  min-width: 0;
  background: #ffffff;
  padding: 0 16px 16px;
}

.detail-tab-header {
  display: flex;
  flex-shrink: 0;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 16px 0;
  border-bottom: 1px solid #e3e8f1;
  background: #ffffff;
}

.detail-tab-header .case-kind-tabs { border-bottom: 0; }

.panel-header {
  justify-content: space-between;
  flex-wrap: wrap;
}

.panel-header > button {
  flex: 0 0 auto;
  white-space: nowrap;
}

.panel-header h3 {
  margin: 0;
  color: #253247;
  font-size: 16px;
}

.panel-header h3 span {
  color: #68758a;
  font-size: 13px;
}

.case-panel-heading {
  min-width: 0;
  flex: 1 1 auto;
}

.case-header-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.case-header-actions button { white-space: nowrap; }

.parameter-height-controls {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin: 0 0 12px;
  color: #68758a;
  font-size: 12px;
}

.parameter-height-controls select {
  width: 140px;
  min-width: 0;
  height: 32px;
  padding: 0 8px;
}

.custom-height-input { display: flex; align-items: center; gap: 5px; }
.custom-height-input input { width: 76px; min-width: 0; height: 32px; padding: 0 6px; }
.height-reset { width: 32px; height: 32px; padding: 0; font-size: 18px; margin-left: auto; }

.case-kind-tabs {
  display: flex;
  overflow-x: auto;
  border-bottom: 1px solid #e3e8f1;
}

.case-kind-tabs button {
  flex: 0 0 auto;
  border: 0;
  border-bottom: 2px solid transparent;
  border-radius: 0;
  background: transparent;
  color: #62708a;
  padding: 8px 12px;
}

.case-kind-tabs button.active {
  border-bottom-color: #0f6b7a;
  color: #0f5f6d;
  font-weight: 700;
}

.case-kind-tabs button span {
  color: #8692a6;
  font-size: 11px;
}

.location-tabs {
  display: flex;
  flex-wrap: wrap;
  margin: 16px 0 12px;
  border-bottom: 1px solid #e3e8f1;
}

.location-tabs button {
  flex: 0 0 auto;
  border: 0;
  border-bottom: 2px solid transparent;
  border-radius: 0;
  background: transparent;
  color: #62708a;
  padding: 8px 10px;
}

.location-tabs button.active {
  border-bottom-color: #0f6b7a;
  color: #0f5f6d;
  font-weight: 700;
}

.location-tabs button span {
  color: #8692a6;
  font-size: 11px;
}

.case-toolbar {
  flex-wrap: wrap;
  margin: 16px 0 12px;
}

.case-toolbar input {
  flex: 1 1 190px;
  min-width: 150px;
}

.case-toolbar select {
  width: 118px;
}

.case-toolbar .icon-button { flex: 0 0 36px; width: 36px; height: 36px; padding: 0; }

.panel-table-wrap {
  width: 100%;
  overflow-x: auto;
  container-type: inline-size;
  border: 1px solid #e5eaf2;
  border-radius: 6px;
}

.panel-table-wrap table {
  min-width: 100%;
}

.parameter-table {
  min-width: 480px !important;
  table-layout: fixed;
}

.parameter-table-wrap { overflow: auto; scrollbar-gutter: stable; }
.parameter-table th { position: sticky; top: 0; z-index: 1; box-shadow: 0 1px #e5eaf2; }
.parameter-name-column { width: clamp(180px, 36cqi, 260px); }
.parameter-location-column { width: 60px; }
.parameter-type-column { width: 68px; }
.parameter-required-column { width: 48px; }
.parameter-table td:first-child strong { overflow-wrap: anywhere; }
.parameter-table td:first-child small { max-width: 100%; }

.case-table {
  min-width: 760px !important;
  table-layout: fixed;
}

.selection-column { width: 38px; }
/* Reserve space for metadata and actions before allowing the name to grow. */
.case-name-column { width: clamp(220px, calc(100cqi - 538px), 360px); }
.priority-column { width: 64px; }
.status-column { width: 64px; }
.updated-column { width: 136px; }
.formal-case-table { min-width: 1068px !important; }
.formal-case-table .case-name-column { width: clamp(180px, calc(100cqi - 828px), 340px); }
.execution-column { width: 92px; }
.http-status-column { width: 88px; }
.response-code-column { width: 88px; }
.case-http-status, .case-response-code { overflow-wrap: anywhere; font-family: Consolas, monospace; }
.case-execution-result { display: inline-block; padding: 3px 6px; border-radius: 4px; background: #f1f4f8; color: #68758a; white-space: nowrap; font-size: 12px; }
.case-execution-result.is-success { background: #e6f5ec; color: #166534; }
.case-execution-result.is-failed { background: #fcecec; color: #b42318; }
.case-execution-result.is-exception { background: #fff3d7; color: #865900; }
.case-delete-action { display: inline-flex; align-items: center; justify-content: center; gap: 5px; font-size: 13px; white-space: nowrap; }
.compact-actions .case-delete-icon { display: inline-grid; place-items: center; width: 30px; height: 30px; padding: 0; }

.case-table td:nth-child(2) strong {
  overflow-wrap: anywhere;
  white-space: normal;
  line-height: 1.5;
}

.case-table td:nth-child(2) small {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.panel-table-wrap th,
.panel-table-wrap td {
  padding: 11px 10px;
}

.panel-table-wrap td strong,
.panel-table-wrap td small {
  display: block;
}

.panel-table-wrap td small {
  max-width: 280px;
  overflow: hidden;
  margin-top: 4px;
  color: #748096;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.compact-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
}

.compact-actions button {
  flex: 0 0 auto;
  padding: 5px 8px;
}

.panel-message {
  margin: 0 0 10px;
  color: #166534;
  font-size: 13px;
}

.error-text,
.error-state {
  color: #b42318;
}

.page-state {
  display: grid;
  justify-items: start;
  gap: 8px;
  min-height: 180px;
  align-content: center;
  color: #68758a;
}

.field-dialog {
  width: min(720px, calc(100vw - 32px));
}

.checkbox-form-field > span:last-child {
  display: flex;
  align-items: center;
  min-height: 38px;
  gap: 8px;
}

.checkbox-form-field input {
  width: 16px;
  height: 16px;
}

.modal-backdrop { z-index: 60; }

@media (max-width: 720px) {
  .detail-header,
  .panel-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .api-identity {
    width: 100%;
    justify-content: flex-start;
    flex-wrap: wrap;
  }

  .api-identity code {
    max-width: 100%;
    overflow-wrap: anywhere;
    white-space: normal;
  }

  .detail-panel {
    padding: 0 12px 12px;
  }

  .detail-tab-header { padding: 10px 12px; }

  .case-panel-heading,
  .case-kind-tabs {
    width: 100%;
  }

  .case-toolbar {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .case-toolbar > input,
  .case-toolbar > select {
    grid-column: 1 / -1;
    width: 100%;
    min-width: 0;
  }

  .case-toolbar > button { min-width: 0; }
  .case-toolbar > button:last-child { grid-column: 2; }
  .case-toolbar .icon-button { justify-self: start; }
  .parameter-panel > .panel-header { flex-direction: row; align-items: center; }
}
</style>
