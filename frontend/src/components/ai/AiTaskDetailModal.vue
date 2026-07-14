<template>
  <div v-if="visible" class="modal-backdrop" @click.self="requestClose">
    <section class="modal-panel task-detail-panel" role="dialog" aria-modal="true">
      <header class="modal-header">
        <h3>生成任务详情</h3>
        <button class="modal-close" type="button" aria-label="关闭" @click="requestClose">×</button>
      </header>

      <div v-if="loading" class="detail-loading">加载中...</div>
      <div v-else-if="error" class="detail-error">{{ error }}</div>
      <div v-else-if="task" class="task-detail-content">
        <section class="detail-summary">
          <div>
            <span>任务名称</span>
            <strong>{{ task.name }}</strong>
          </div>
          <div>
            <span>状态</span>
            <strong :class="['status-text', statusClass(task.status)]">{{ formatStatus(task.status) }}</strong>
          </div>
          <div>
            <span>任务类型</span>
            <strong>{{ formatTaskType(taskData.task_type) }}</strong>
          </div>
          <div>
            <span>项目ID</span>
            <strong>{{ task.project_id || '-' }}</strong>
          </div>
          <div>
            <span>更新时间</span>
            <strong>{{ task.updated_at || '-' }}</strong>
          </div>
          <div>
            <span>执行时间</span>
            <strong>{{ taskDurationText }}</strong>
          </div>
          <div v-if="taskData.progress">
            <span>当前进度</span>
            <strong>{{ taskData.progress }}</strong>
          </div>
        </section>

        <section v-if="failureLogs.length" class="detail-section error-section">
          <h4>失败日志</h4>
          <ul>
            <li v-for="(log, index) in failureLogs" :key="`failure-${index}`">{{ log }}</li>
          </ul>
        </section>

        <section v-if="batchErrors.length" class="detail-section">
          <h4>批次失败</h4>
          <table class="detail-table">
            <thead>
              <tr>
                <th>批次</th>
                <th>错误信息</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, index) in batchErrors" :key="`batch-${index}`">
                <td>{{ item.batch ?? '-' }}</td>
                <td>{{ item.error ?? stringifyJson(item) }}</td>
              </tr>
            </tbody>
          </table>
        </section>

        <section v-if="warnings.length" class="detail-section warning-section">
          <h4>警告信息</h4>
          <ul>
            <li v-for="(warning, index) in warnings" :key="`warning-${index}`">{{ warning }}</li>
          </ul>
        </section>

        <section class="detail-section result-grid">
          <div>
            <span>{{ isWebFunctionElementTask ? '扫描页面' : '生成页面' }}</span>
            <strong>{{ isWebFunctionElementTask ? taskResult.page_count ?? '-' : taskResult.generated_pages ?? '-' }}</strong>
          </div>
          <div>
            <span>{{ isWebFunctionElementTask ? '成功页面' : '保存页面' }}</span>
            <strong>{{ isWebFunctionElementTask ? taskResult.success_pages ?? '-' : taskResult.saved_pages ?? '-' }}</strong>
          </div>
          <div>
            <span>{{ isWebFunctionElementTask ? '保存元素' : '更新页面' }}</span>
            <strong>{{ isWebFunctionElementTask ? taskResult.saved_elements ?? '-' : taskResult.updated_pages ?? '-' }}</strong>
          </div>
          <template v-if="isWebFunctionElementTask">
            <div>
              <span>新增元素</span>
              <strong>{{ taskResult.created_elements ?? '-' }}</strong>
            </div>
            <div>
              <span>更新元素</span>
              <strong>{{ taskResult.updated_elements ?? '-' }}</strong>
            </div>
            <div>
              <span>跳过元素</span>
              <strong>{{ taskResult.skipped_elements ?? '-' }}</strong>
            </div>
          </template>
          <div>
            <span>{{ isWebFunctionElementTask ? '失败页面' : '跳过页面' }}</span>
            <strong>{{ isWebFunctionElementTask ? failedPageCount : taskResult.skipped_pages ?? '-' }}</strong>
          </div>
          <div>
            <span>{{ isWebFunctionElementTask ? '扫描方式' : '成功批次' }}</span>
            <strong>{{ isWebFunctionElementTask ? formatScanScope(taskResult.scan_scope) : taskResult.success_batches ?? '-' }}</strong>
          </div>
          <div>
            <span>失败批次</span>
            <strong>{{ taskResult.failed_batches ?? taskData.failed_batches ?? '-' }}</strong>
          </div>
        </section>

        <section v-if="isWebFunctionElementTask" class="detail-section element-scan-section">
          <header class="section-title-row">
            <h4>扫描页面与元素</h4>
            <span>共 {{ scanPageItems.length }} 个页面，{{ totalScanElementCount }} 个元素</span>
          </header>
          <div v-if="scanPageItems.length" class="scan-layout">
            <aside class="scan-page-list" aria-label="扫描页面列表">
              <button
                v-for="page in scanPageItems"
                :key="page.key"
                type="button"
                :class="{ active: selectedScanPageKey === page.key }"
                @click="selectedScanPageKey = page.key"
              >
                <span>{{ page.page_name }}</span>
                <small>{{ page.target_url || '-' }}</small>
                <b>{{ page.element_count }} 个元素</b>
              </button>
            </aside>

            <section v-if="selectedScanPage" class="scan-detail">
              <div class="route-meta">
                <div>
                  <span>页面ID</span>
                  <strong>{{ selectedScanPage.page_id || '-' }}</strong>
                </div>
                <div>
                  <span>页面功能</span>
                  <strong>{{ selectedScanPage.page_name }}</strong>
                </div>
                <div>
                  <span>页面地址</span>
                  <strong>{{ selectedScanPage.target_url || '-' }}</strong>
                </div>
              </div>

              <div v-if="selectedScanPage.warnings.length" class="scan-warning">
                <strong>页面警告</strong>
                <ul>
                  <li v-for="(warning, index) in selectedScanPage.warnings" :key="`scan-warning-${index}`">{{ warning }}</li>
                </ul>
              </div>

              <figure v-if="selectedScanPage.screenshot_url" class="scan-screenshot">
                <figcaption>
                  <span>点击功能按钮后的页面截图</span>
                  <small>{{ selectedScanPage.screenshot_file || '已采集' }}</small>
                </figcaption>
                <img :src="selectedScanPage.screenshot_url" :alt="`${selectedScanPage.page_name} 功能截图`" />
              </figure>
              <p v-else-if="selectedScanPage.screenshot_error" class="empty-route-detail">
                功能截图采集失败：{{ selectedScanPage.screenshot_error }}
              </p>
              <p v-else class="empty-route-detail">暂无点击功能按钮后的页面截图。</p>

              <div class="scan-subsection">
                <header class="section-title-row">
                  <h5>功能操作步骤</h5>
                  <span>{{ selectedScanPage.operation_steps.length }} 个计划步骤，{{ selectedScanPage.executed_steps.length }} 个执行记录</span>
                </header>
                <table v-if="selectedScanPage.operation_steps.length" class="detail-table scan-table">
                  <thead>
                    <tr>
                      <th>步骤</th>
                      <th>元素名称</th>
                      <th>交互</th>
                      <th>输入值</th>
                      <th>实际定位</th>
                      <th>执行状态</th>
                      <th>目的</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="step in selectedScanPage.operation_steps" :key="step.key">
                      <td>{{ step.step_id }}</td>
                      <td>{{ step.element_name || '-' }}</td>
                      <td>{{ formatAction(step.action) }}</td>
                      <td>{{ step.value || '-' }}</td>
                      <td>{{ step.locator || '-' }}</td>
                      <td>
                        <span :class="['status-pill', stepStatusClass(step)]">{{ formatStepStatus(step) }}</span>
                      </td>
                      <td>{{ step.purpose || '-' }}</td>
                    </tr>
                  </tbody>
                </table>
                <p v-else class="empty-route-detail">暂无功能操作步骤。</p>
              </div>

              <div class="scan-subsection">
                <header class="section-title-row">
                  <h5>获取元素列表</h5>
                  <span>{{ selectedScanPage.elements.length }} 个元素</span>
                </header>
                <table v-if="selectedScanPage.elements.length" class="detail-table scan-table element-table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>元素名称</th>
                      <th>类型</th>
                      <th>交互</th>
                      <th>定位方式</th>
                      <th>定位值</th>
                      <th>默认值</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="element in selectedScanPage.elements" :key="element.key">
                      <td>{{ element.id || '-' }}</td>
                      <td>{{ element.name || '-' }}</td>
                      <td>{{ element.element_type || '-' }}</td>
                      <td>{{ formatAction(element.action) }}</td>
                      <td>{{ formatLocatorType(element.locator_type) }}</td>
                      <td>{{ element.locator || '-' }}</td>
                      <td>{{ element.default_value || '-' }}</td>
                    </tr>
                  </tbody>
                </table>
                <p v-else class="empty-route-detail">暂无解析到的元素。</p>
              </div>

              <details v-if="selectedScanPage.script_text" class="detail-json">
                <summary>查看解析脚本</summary>
                <pre>{{ selectedScanPage.script_text }}</pre>
              </details>
            </section>
          </div>
          <p v-else class="empty-route-detail">暂无扫描页面结果。</p>
        </section>

        <section v-if="!isWebFunctionElementTask" class="detail-section route-discovery-section">
          <header class="section-title-row">
            <h4>登录后获取路由</h4>
            <span>共 {{ routeItems.length }} 个路由，{{ routeFeatures.length }} 个识别功能</span>
          </header>
          <div v-if="routeTree.length" class="route-layout">
            <aside class="route-tree" aria-label="登录后路由目录">
              <details v-for="group in routeTree" :key="group.key" class="route-group" open>
                <summary>
                  <span>{{ group.label }}</span>
                  <b>{{ group.children.length }}</b>
                </summary>
                <button
                  v-for="route in group.children"
                  :key="route.key"
                  type="button"
                  :class="{ active: selectedRouteKey === route.key }"
                  @click="selectedRouteKey = route.key"
                >
                  <span>{{ route.label }}</span>
                  <small>{{ route.route || route.url }}</small>
                </button>
              </details>
            </aside>

            <section v-if="selectedRoute" class="route-detail">
              <div class="route-meta">
                <div>
                  <span>页面路由</span>
                  <strong>{{ selectedRoute.route || '-' }}</strong>
                </div>
                <div>
                  <span>页面地址</span>
                  <strong>{{ selectedRoute.url || '-' }}</strong>
                </div>
                <div>
                  <span>截图</span>
                  <strong>{{ selectedRoute.screenshot_url ? '已采集' : '未采集' }}</strong>
                </div>
              </div>

              <figure v-if="selectedRoute.screenshot_url" class="route-screenshot">
                <img :src="selectedRoute.screenshot_url" :alt="`${selectedRoute.label} 截图`" />
              </figure>
              <p v-else class="empty-route-detail">该路由暂无截图，可能来自路由表但未进入页面采集。</p>

              <div class="route-functions">
                <h5>AI 识别到的对应功能</h5>
                <table v-if="selectedRoute.features.length" class="detail-table">
                  <thead>
                    <tr>
                      <th>功能名称</th>
                      <th>功能类型</th>
                      <th>状态</th>
                      <th>说明</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="feature in selectedRoute.features" :key="feature.key">
                      <td>{{ feature.name }}</td>
                      <td>{{ formatFeatureType(feature.feature_type) }}</td>
                      <td>{{ formatStatus(feature.status) }}</td>
                      <td>{{ feature.description || '-' }}</td>
                    </tr>
                  </tbody>
                </table>
                <p v-else class="empty-route-detail">该路由暂未识别到页面功能。</p>
              </div>
            </section>
          </div>
          <p v-else class="empty-route-detail">暂无登录后路由信息，请重新执行生成任务并开启登录后页面发现。</p>
        </section>
      </div>
      <p v-else class="empty-detail">没有找到任务详情。</p>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import type { ResourceItem } from '../../api/http'
import {
  arrayRecords,
  firstRouteSegment,
  formatAction,
  formatDurationMinutes,
  formatFeatureType,
  formatLocatorType,
  formatScanScope,
  formatStatus,
  formatStepStatus,
  formatTaskType,
  isRecord,
  normalizeRoute,
  normalizeScanPage,
  routeKey,
  statusClass,
  stepStatusClass,
  stringifyJson,
  toFiniteNumber,
  toRecord,
  toTimestampMs,
  upsertRouteItem
} from '../../utils/aiTaskDetail'
import type { RouteFeature, RouteGroup, RouteItem, ScanPageItem } from '../../utils/aiTaskDetail'

const props = defineProps<{
  visible: boolean
  loading: boolean
  error: string
  task: ResourceItem | null
}>()

const emit = defineEmits<{
  (event: 'close'): void
}>()

const visible = computed(() => props.visible)
const loading = computed(() => props.loading)
const error = computed(() => props.error)
const task = computed(() => props.task)
const selectedRouteKey = ref('')
const selectedScanPageKey = ref('')
const taskData = computed<Record<string, unknown>>(() => {
  return toRecord(task.value?.data)
})

const taskResult = computed<Record<string, unknown>>(() => {
  return toRecord(taskData.value.result)
})

const isWebFunctionElementTask = computed(() => String(taskData.value.task_type || taskResult.value.task_type || '') === 'web_function_element_generation')

const scanPageItems = computed<ScanPageItem[]>(() => {
  return arrayRecords(taskResult.value.pages).map((page, index) => normalizeScanPage(page, index))
})

const selectedScanPage = computed<ScanPageItem | null>(() => {
  if (!scanPageItems.value.length) {
    return null
  }
  const selected = scanPageItems.value.find(page => page.key === selectedScanPageKey.value)
  return selected || scanPageItems.value[0]
})

const totalScanElementCount = computed(() => scanPageItems.value.reduce((total, page) => total + page.element_count, 0))

const failedPageCount = computed(() => arrayRecords(taskResult.value.failed_pages).length)

const discoveryData = computed<Record<string, unknown>>(() => {
  return toRecord(taskResult.value.discovery ?? taskData.value.discovery)
})

const routeFeatures = computed<RouteFeature[]>(() => {
  const pages = arrayRecords(taskResult.value.pages)
  return pages.map((page, index) => {
    const data = toRecord(page.data)
    const route = normalizeRoute(data.route ?? page.route)
    const url = String(data.url ?? page.url ?? '')
    return {
      key: String(page.id ?? `${route || url || 'feature'}-${index}`),
      name: String(page.name ?? data.name ?? '-'),
      route,
      url,
      feature_type: String(data.feature_type ?? page.feature_type ?? ''),
      status: String(page.status ?? ''),
      description: String(page.description ?? '')
    }
  })
})

function discoveryRoutes() {
  return arrayRecords(discoveryData.value.routes)
}

function discoveryPages() {
  return arrayRecords(discoveryData.value.pages)
}

const routeItems = computed<RouteItem[]>(() => {
  const byKey = new Map<string, RouteItem>()
  for (const route of discoveryRoutes()) {
    upsertRouteItem(byKey, route)
  }
  for (const page of discoveryPages()) {
    upsertRouteItem(byKey, page)
  }
  for (const feature of routeFeatures.value) {
    const key = routeKey(feature.route, feature.url)
    if (!byKey.has(key)) {
      byKey.set(key, {
        key,
        label: feature.route || feature.url || feature.name,
        route: feature.route,
        url: feature.url,
        screenshot_url: '',
        screenshot_file: '',
        features: []
      })
    }
    byKey.get(key)?.features.push(feature)
  }
  return Array.from(byKey.values()).sort((left, right) => left.route.localeCompare(right.route))
})

const routeTree = computed<RouteGroup[]>(() => {
  const groups = new Map<string, RouteGroup>()
  for (const route of routeItems.value) {
    const groupKey = firstRouteSegment(route.route || route.url)
    if (!groups.has(groupKey)) {
      groups.set(groupKey, { key: groupKey, label: groupKey === '/' ? '根路由' : groupKey, children: [] })
    }
    groups.get(groupKey)?.children.push(route)
  }
  return Array.from(groups.values()).sort((left, right) => left.label.localeCompare(right.label))
})

const selectedRoute = computed<RouteItem | null>(() => {
  if (!routeItems.value.length) {
    return null
  }
  const selected = routeItems.value.find(route => route.key === selectedRouteKey.value)
  return selected || routeItems.value[0]
})

const taskDurationText = computed(() => {
  const savedDuration = toFiniteNumber(taskData.value.duration_minutes)
  if (savedDuration != null) {
    return formatDurationMinutes(savedDuration)
  }

  const startedAt = toTimestampMs(taskData.value.started_at)
  const finishedAt =
    toTimestampMs(taskData.value.finished_at) ||
    toTimestampMs(taskResult.value.finished_at) ||
    (String(task.value?.status || '') === 'running' ? Date.now() : toTimestampMs(task.value?.updated_at))
  if (!startedAt || !finishedAt || finishedAt < startedAt) {
    return '-'
  }
  return formatDurationMinutes((finishedAt - startedAt) / 60000)
})

const batchErrors = computed<Record<string, unknown>[]>(() => {
  const errors = taskResult.value.batch_errors ?? taskData.value.batch_errors
  return Array.isArray(errors) ? errors.filter(isRecord) : []
})

const warnings = computed<string[]>(() => {
  const rawWarnings = taskResult.value.warnings ?? taskData.value.warnings
  return Array.isArray(rawWarnings) ? rawWarnings.map(item => String(item)) : []
})

const failureLogs = computed<string[]>(() => {
  const logs: string[] = []
  const error = taskResult.value.error ?? taskData.value.error
  if (error != null && error !== '') {
    logs.push(String(error))
  }
  for (const item of batchErrors.value) {
    if (item.error != null && item.error !== '') {
      logs.push(`第 ${item.batch ?? '-'} 批：${item.error}`)
    }
  }
  return Array.from(new Set(logs))
})

watch(
  () => [props.visible, props.loading, props.task?.id],
  async () => {
    if (!props.visible || props.loading || !props.task) {
      return
    }
    await nextTick()
    selectedRouteKey.value = routeItems.value[0]?.key || ''
    selectedScanPageKey.value = scanPageItems.value[0]?.key || ''
  },
  { immediate: true }
)

function requestClose() {
  if (props.loading) {
    return
  }
  emit('close')
}

</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: grid;
  place-items: center;
  padding: 32px;
  background: rgb(15 23 42 / 54%);
}

.modal-panel {
  width: min(1180px, 100%);
  max-height: calc(100vh - 64px);
  overflow: auto;
  border: 1px solid #dbe3ef;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 24px 60px rgb(15 23 42 / 22%);
}

.modal-header {
  position: sticky;
  top: 0;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 22px;
  border-bottom: 1px solid #e6edf5;
  background: #fff;
}

.modal-header h3 {
  margin: 0;
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

.task-detail-content,
.detail-loading,
.detail-error,
.empty-detail {
  padding: 20px 22px 24px;
}

.detail-error {
  color: #dc2626;
}

.detail-summary,
.result-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.detail-summary div,
.result-grid div {
  display: grid;
  gap: 6px;
  padding: 12px;
  border: 1px solid #e6edf5;
  border-radius: 8px;
  background: #f8fafc;
}

.detail-summary span,
.result-grid span {
  color: #64748b;
  font-size: 12px;
}

.detail-summary strong,
.result-grid strong {
  color: #0f172a;
  font-size: 14px;
  word-break: break-word;
}

.status-text.success {
  color: #16a34a;
}

.status-text.warning {
  color: #d97706;
}

.status-text.danger {
  color: #dc2626;
}

.status-text.info {
  color: #2563eb;
}

.detail-section {
  margin-top: 16px;
  padding: 14px;
  border: 1px solid #e6edf5;
  border-radius: 8px;
  background: #fff;
}

.detail-section h4 {
  margin: 0 0 10px;
  font-size: 15px;
}

.section-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.section-title-row h4 {
  margin: 0;
}

.section-title-row span {
  color: #64748b;
  font-size: 12px;
}

.detail-section ul {
  display: grid;
  gap: 8px;
  margin: 0;
  padding-left: 18px;
}

.error-section {
  border-color: #fecaca;
  background: #fef2f2;
  color: #991b1b;
}

.warning-section {
  border-color: #fed7aa;
  background: #fff7ed;
  color: #9a3412;
}

.route-discovery-section {
  background: #f8fafc;
}

.element-scan-section {
  background: #f8fafc;
}

.scan-layout {
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  gap: 14px;
  align-items: start;
}

.scan-page-list {
  display: grid;
  gap: 8px;
  max-height: 620px;
  overflow: auto;
  padding: 8px;
  border: 1px solid #e6edf5;
  border-radius: 8px;
  background: #fff;
}

.scan-page-list button {
  display: grid;
  gap: 5px;
  padding: 10px;
  border: 1px solid transparent;
  border-radius: 6px;
  background: transparent;
  color: #334155;
  text-align: left;
  cursor: pointer;
}

.scan-page-list button:hover,
.scan-page-list button.active {
  border-color: #bfdbfe;
  background: #eff6ff;
  color: #1d4ed8;
}

.scan-page-list span {
  font-size: 13px;
  font-weight: 700;
}

.scan-page-list small {
  overflow: hidden;
  color: #64748b;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 11px;
}

.scan-page-list b {
  color: #2563eb;
  font-size: 12px;
}

.scan-detail {
  display: grid;
  gap: 12px;
  min-width: 0;
}

.scan-warning {
  padding: 12px;
  border: 1px solid #fed7aa;
  border-radius: 8px;
  background: #fff7ed;
  color: #9a3412;
  font-size: 13px;
}

.scan-warning ul {
  margin: 8px 0 0;
  padding-left: 18px;
}

.scan-subsection {
  padding: 12px;
  border: 1px solid #e6edf5;
  border-radius: 8px;
  background: #fff;
}

.scan-subsection h5 {
  margin: 0;
  color: #0f172a;
  font-size: 14px;
}

.scan-screenshot {
  margin: 0;
  overflow: hidden;
  border: 1px solid #e6edf5;
  border-radius: 8px;
  background: #fff;
}

.scan-screenshot figcaption {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 12px;
  border-bottom: 1px solid #e6edf5;
  color: #0f172a;
  font-size: 13px;
  font-weight: 700;
}

.scan-screenshot figcaption small {
  overflow: hidden;
  color: #64748b;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 11px;
  font-weight: 500;
}

.scan-screenshot img {
  display: block;
  width: 100%;
  max-height: 420px;
  object-fit: contain;
  background: #f1f5f9;
}

.scan-table th,
.scan-table td {
  font-size: 12px;
}

.scan-table td {
  overflow-wrap: anywhere;
}

.element-table th:nth-child(6),
.element-table td:nth-child(6) {
  max-width: 320px;
}

.route-layout {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 14px;
  align-items: start;
}

.route-tree {
  max-height: 620px;
  overflow: auto;
  padding: 8px;
  border: 1px solid #e6edf5;
  border-radius: 8px;
  background: #fff;
}

.route-group {
  border-bottom: 1px solid #eef2f7;
}

.route-group:last-child {
  border-bottom: 0;
}

.route-group summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 8px;
  color: #0f172a;
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
}

.route-group summary b {
  min-width: 26px;
  padding: 2px 6px;
  border-radius: 999px;
  background: #e8f1ff;
  color: #2563eb;
  text-align: center;
  font-size: 11px;
}

.route-group button {
  display: grid;
  width: 100%;
  gap: 4px;
  padding: 9px 10px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #334155;
  text-align: left;
  cursor: pointer;
}

.route-group button:hover,
.route-group button.active {
  background: #eff6ff;
  color: #1d4ed8;
}

.route-group button span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  font-weight: 600;
}

.route-group button small {
  overflow: hidden;
  color: #64748b;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 11px;
}

.route-detail {
  display: grid;
  gap: 12px;
  min-width: 0;
}

.route-meta {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.route-meta div {
  display: grid;
  gap: 6px;
  padding: 10px;
  border: 1px solid #e6edf5;
  border-radius: 8px;
  background: #fff;
}

.route-meta span {
  color: #64748b;
  font-size: 12px;
}

.route-meta strong {
  overflow-wrap: anywhere;
  color: #0f172a;
  font-size: 13px;
}

.route-screenshot {
  margin: 0;
  overflow: hidden;
  border: 1px solid #e6edf5;
  border-radius: 8px;
  background: #fff;
}

.route-screenshot img {
  display: block;
  width: 100%;
  max-height: 520px;
  object-fit: contain;
  background: #f1f5f9;
}

.route-functions {
  padding: 12px;
  border: 1px solid #e6edf5;
  border-radius: 8px;
  background: #fff;
}

.route-functions h5 {
  margin: 0 0 10px;
  color: #0f172a;
  font-size: 14px;
}

.empty-route-detail {
  margin: 0;
  padding: 14px;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  background: #fff;
  color: #64748b;
  font-size: 13px;
}

.detail-table {
  width: 100%;
  border-collapse: collapse;
}

.detail-table th,
.detail-table td {
  padding: 10px;
  border-bottom: 1px solid #e6edf5;
  text-align: left;
  vertical-align: top;
}

.detail-table th:first-child,
.detail-table td:first-child {
  width: 90px;
}

.detail-json {
  margin-top: 16px;
  border: 1px solid #e6edf5;
  border-radius: 8px;
  background: #fff;
}

.detail-json summary {
  padding: 12px 14px;
  cursor: pointer;
  font-weight: 600;
}

.detail-json pre {
  max-height: 360px;
  margin: 0;
  overflow: auto;
  padding: 14px;
  border-top: 1px solid #e6edf5;
  background: #0f172a;
  color: #e2e8f0;
  font-size: 12px;
  line-height: 1.6;
}

@media (max-width: 900px) {
  .modal-backdrop {
    padding: 16px;
  }

  .detail-summary,
  .result-grid,
  .scan-layout,
  .route-layout,
  .route-meta {
    grid-template-columns: 1fr;
  }

  .route-tree {
    max-height: 320px;
  }
}
</style>

