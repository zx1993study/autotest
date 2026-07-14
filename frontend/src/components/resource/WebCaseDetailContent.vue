<template>
  <template v-if="item">
    <section class="web-case-runtime-panel">
      <dl class="execution-meta">
        <div>
          <dt>来源 ID</dt>
          <dd>{{ formatValue(item.source_id) }}</dd>
        </div>
        <div>
          <dt>执行记录</dt>
          <dd>{{ latestExecutionRecord ? `#${latestExecutionRecord.id}` : '-' }}</dd>
        </div>
        <div>
          <dt>执行状态</dt>
          <dd><span class="status-pill" :class="runtimeStatusClass">{{ runtimeStatusText }}</span></dd>
        </div>
        <div>
          <dt>耗时</dt>
          <dd>{{ formatDuration(latestExecutionData.duration_ms) }}</dd>
        </div>
      </dl>
      <details class="result-detail">
        <summary>异常信息</summary>
        <pre>{{ runtimeErrorText }}</pre>
      </details>
    </section>

    <section class="case-step-panel">
      <div class="case-step-header">
        <strong>操作步骤</strong>
        <span>共 {{ steps.length }} 步</span>
      </div>
      <table v-if="steps.length" class="case-step-table web-step-table">
        <thead>
          <tr>
            <th>顺序</th>
            <th>元素名称</th>
            <th>交互</th>
            <th>默认值</th>
            <th>截图</th>
            <th>跳过</th>
            <th>定位信息</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(step, stepIndex) in steps" :key="stepKey(step, stepIndex)">
            <td>{{ stepOrder(step, stepIndex) }}</td>
            <td>{{ stepLabel(step) }}</td>
            <td>{{ stepAction(step) }}</td>
            <td>{{ stepInputValue(step) || '-' }}</td>
            <td><span class="status-pill" :class="{ success: stepScreenshot(step) }">{{ stepScreenshot(step) ? '是' : '否' }}</span></td>
            <td><span class="status-pill" :class="{ failed: stepSkip(step) }">{{ stepSkip(step) ? '是' : '否' }}</span></td>
            <td>{{ stepLocator(step) }}</td>
          </tr>
        </tbody>
      </table>
      <p v-else class="empty-route-detail">暂无操作步骤。</p>
    </section>

    <section class="web-case-screenshot-list">
      <div class="case-step-header">
        <strong>截图信息</strong>
        <span>共 {{ screenshots.length }} 张</span>
      </div>
      <div v-if="screenshots.length" class="web-case-screenshot-grid">
        <figure v-for="(screenshot, screenshotIndex) in screenshots" :key="screenshotKey(screenshot, screenshotIndex)">
          <button
            v-if="screenshotSrc(screenshot)"
            class="web-case-screenshot-thumb"
            type="button"
            :title="`放大查看${screenshotTitle(screenshot, screenshotIndex)}`"
            @click="openScreenshotPreview(screenshot)"
          >
            <img :src="screenshotSrc(screenshot)" :alt="screenshotTitle(screenshot, screenshotIndex)" />
          </button>
          <div v-else class="web-case-screenshot-empty">{{ screenshotMeta(screenshot) }}</div>
          <figcaption>
            <strong>{{ screenshotTitle(screenshot, screenshotIndex) }}</strong>
            <span>{{ screenshotMeta(screenshot) }}</span>
          </figcaption>
        </figure>
      </div>
      <p v-else class="empty-route-detail">暂无截图信息。</p>
    </section>

    <div v-if="previewScreenshot && previewImageSrc" class="screenshot-preview-backdrop" @click.self="closeScreenshotPreview">
      <section class="screenshot-preview-panel" role="dialog" aria-modal="true">
        <header>
          <strong>{{ screenshotTitle(previewScreenshot, 0) }}</strong>
          <button type="button" aria-label="关闭截图预览" @click="closeScreenshotPreview">×</button>
        </header>
        <img :src="previewImageSrc" :alt="screenshotTitle(previewScreenshot, 0)" />
        <p>{{ screenshotMeta(previewScreenshot) }}</p>
      </section>
    </div>

    <details class="result-detail">
      <summary>用例数据</summary>
      <pre>{{ stringifyJson(item) }}</pre>
    </details>
  </template>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { listResources } from '../../services/resource.service'
import type { ResourceItem } from '../../types/resource'

const props = defineProps<{ item: ResourceItem | null }>()

const executionRecords = ref<ResourceItem[]>([])
const previewScreenshot = ref<Record<string, unknown> | null>(null)
const steps = computed(() => props.item ? webCaseDetailSteps(props.item) : [])
const latestExecutionRecord = computed(() => executionRecords.value[0] || null)
const latestExecutionData = computed<Record<string, unknown>>(() => {
  const data = latestExecutionRecord.value?.data
  return isRecord(data) ? data : {}
})
const screenshots = computed(() => webCaseScreenshots())
const previewImageSrc = computed(() => previewScreenshot.value ? screenshotSrc(previewScreenshot.value) : '')
const runtimeStatusText = computed(() => {
  const status = String(latestExecutionRecord.value?.status || '')
  const labels: Record<string, string> = {
    success: '成功',
    failed: '失败',
    queued: '排队中',
    running: '执行中'
  }
  return status ? labels[status] || status : '未执行'
})
const runtimeStatusClass = computed(() => {
  const status = String(latestExecutionRecord.value?.status || '')
  if (status === 'success') return 'success'
  if (status === 'failed') return 'failed'
  return 'queued'
})
const runtimeErrorText = computed(() => {
  const error = latestExecutionData.value.error || latestExecutionRecord.value?.description
  return formatValue(error)
})
let executionRecordLoadSequence = 0

watch(
  () => [props.item?.id, props.item?.project_id],
  async ([caseId, projectId]) => {
    const sequence = ++executionRecordLoadSequence
    executionRecords.value = []
    previewScreenshot.value = null
    const normalizedCaseId = Number(caseId)
    if (!Number.isFinite(normalizedCaseId) || normalizedCaseId <= 0) return
    const params: Record<string, unknown> = {
      case_id: normalizedCaseId,
      case_type: 'WEB',
      page: 1,
      pageSize: 1
    }
    const normalizedProjectId = Number(projectId)
    if (Number.isFinite(normalizedProjectId) && normalizedProjectId > 0) {
      params.project_id = normalizedProjectId
    }
    try {
      const records = await listResources('/reports/records', params)
      if (sequence === executionRecordLoadSequence) {
        executionRecords.value = records.items
      }
    } catch {
      if (sequence === executionRecordLoadSequence) {
        executionRecords.value = []
      }
    }
  },
  { immediate: true }
)

function webCaseDetailSteps(item: ResourceItem) {
  const data = isRecord(item.data) ? item.data : {}
  const request = isRecord(data.request) ? data.request : {}
  const rawSteps = Array.isArray(item.steps)
    ? item.steps
    : Array.isArray(data.steps)
      ? data.steps
      : Array.isArray(request.steps)
        ? request.steps
        : []
  return normalizeStepRows(rawSteps)
}
function normalizeStepRows(rawSteps: unknown[]) {
  return rawSteps.filter(isRecord).map(step => ({ ...step })).sort((left, right) => Number(stepOrder(left, 0)) - Number(stepOrder(right, 0)))
}
function webCaseScreenshots() {
  const screenshotRows: Record<string, unknown>[] = []
  if (latestExecutionRecord.value) {
    collectScreenshots(screenshotRows, latestExecutionRecord.value.data)
  }
  const seen = new Set<string>()
  return screenshotRows.filter((screenshot, index) => {
    const key = screenshotKey(screenshot, index)
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}
function collectScreenshots(target: Record<string, unknown>[], value: unknown, depth = 0) {
  if (depth > 4) return
  if (Array.isArray(value)) {
    for (const item of value) collectScreenshots(target, item, depth + 1)
    return
  }
  if (!isRecord(value)) return
  if (screenshotSrc(value) || value.screenshot_error) target.push(value)
  for (const key of ['screenshots', 'feature_screenshot', 'screenshot', 'page_screenshot', 'recording', 'result', 'data']) {
    if (key in value) collectScreenshots(target, value[key], depth + 1)
  }
}
function screenshotSrc(screenshot: Record<string, unknown>) {
  const direct = readStepValue(screenshot, ['screenshot_url', 'image_url', 'src', 'screenshot_path'])
  if (typeof direct === 'string' && direct) {
    const normalized = normalizeScreenshotUrl(direct)
    if (normalized) return normalized
  }
  const path = readStepValue(screenshot, ['path'])
  if (typeof path === 'string' && looksLikeScreenshotReference(path)) {
    const normalized = normalizeScreenshotUrl(path)
    if (normalized) return normalized
  }
  const file = readStepValue(screenshot, ['screenshot_file', 'file', 'filename', 'screenshot_filename'])
  return typeof file === 'string' && file ? screenshotApiUrl(file) : ''
}
function looksLikeScreenshotReference(value: string) {
  const normalized = value.trim().replace(/\\/g, '/').toLowerCase()
  return normalized.includes('/api/v1/screenshots/') || normalized.includes('/screenshots/') || /\.(png|jpe?g|webp|gif)$/i.test(normalized)
}
function normalizeScreenshotUrl(value: string) {
  const trimmed = value.trim()
  if (!trimmed) return ''
  if (/^(https?:)?\/\//i.test(trimmed) || trimmed.startsWith('data:') || trimmed.startsWith('blob:')) return trimmed
  const normalized = trimmed.replace(/\\/g, '/')
  const apiIndex = normalized.indexOf('/api/v1/screenshots/')
  if (apiIndex >= 0) return normalized.slice(apiIndex)
  const screenshotIndex = normalized.toLowerCase().lastIndexOf('/screenshots/')
  if (screenshotIndex >= 0) return screenshotApiUrl(normalized.slice(screenshotIndex + '/screenshots/'.length))
  if (/^[^/]+\.png$/i.test(normalized)) return screenshotApiUrl(normalized)
  return ''
}
function screenshotApiUrl(value: string) {
  const filename = value.replace(/\\/g, '/').split('/').filter(Boolean).pop() || ''
  return filename ? `/api/v1/screenshots/${encodeURIComponent(filename)}` : ''
}
function screenshotTitle(screenshot: Record<string, unknown>, index: number) {
  return formatValue(readStepValue(screenshot, ['name', 'title', 'step_name', '元素名称']) ?? `截图 ${index + 1}`)
}
function screenshotMeta(screenshot: Record<string, unknown>) {
  return formatValue(readStepValue(screenshot, ['screenshot_file', 'file', 'filename', 'screenshot_error', 'created_at', 'path', 'screenshot_path']))
}
function screenshotKey(screenshot: Record<string, unknown>, index: number) {
  return String(screenshotSrc(screenshot) || readStepValue(screenshot, ['screenshot_file', 'file', 'filename', 'path', 'screenshot_path']) || index)
}
function openScreenshotPreview(screenshot: Record<string, unknown>) { previewScreenshot.value = screenshot }
function closeScreenshotPreview() { previewScreenshot.value = null }
function formatDuration(value: unknown): string {
  const duration = Number(value)
  return Number.isFinite(duration) ? `${duration} ms` : '-'
}
function stepKey(step: Record<string, unknown>, index: number) { return String(readStepValue(step, ['步骤标识', 'id', 'step_id', 'sort_order', 'order']) ?? index) }
function stepOrder(step: Record<string, unknown>, index: number) { return readStepValue(step, ['sort_order', 'order', 'index', '步骤标识']) ?? index + 1 }
function stepLabel(step: Record<string, unknown>) { return formatValue(readStepValue(step, ['元素名称', 'element_name', 'name', 'locator', 'selector'])) }
function stepAction(step: Record<string, unknown>) { return formatValue(readStepValue(step, ['交互类型', 'action', 'type', 'operation'])) }
function stepInputValue(step: Record<string, unknown>) { const value = readStepValue(step, ['元素值', 'value', 'default_value', 'input']); return value == null ? '' : String(value) }
function stepScreenshot(step: Record<string, unknown>) { return Boolean(readStepValue(step, ['是否截图', 'take_screenshot', 'screenshot'])) }
function stepSkip(step: Record<string, unknown>) { return Boolean(readStepValue(step, ['是否跳过', 'skip', 'skipped'])) }
function stepLocator(step: Record<string, unknown>) { return formatValue(readStepValue(step, ['selector', 'locator', 'xpath', 'css', 'placeholder', 'label', 'role'])) }
function readStepValue(step: Record<string, unknown>, keys: string[]) { for (const key of keys) if (step[key] !== undefined && step[key] !== '') return step[key]; return undefined }
function stringifyJson(value: unknown) { return JSON.stringify(value ?? {}, null, 2) }
function formatValue(value: unknown): string { if (value == null || value === '') return '-'; if (typeof value === 'boolean') return value ? '是' : '否'; if (typeof value === 'object') return JSON.stringify(value); return String(value) }
function isRecord(value: unknown): value is Record<string, unknown> { return Boolean(value) && typeof value === 'object' && !Array.isArray(value) }
</script>

<style scoped>
.web-case-runtime-panel {
  display: grid;
  gap: 12px;
  border: 1px solid #e4e9f2;
  border-radius: 8px;
  background: #ffffff;
  padding: 14px;
}

.web-case-screenshot-thumb {
  display: block;
  width: 100%;
  border: 0;
  background: transparent;
  padding: 0;
  cursor: zoom-in;
}

.screenshot-preview-backdrop {
  position: fixed;
  z-index: 1100;
  inset: 0;
  display: grid;
  place-items: center;
  background: rgb(15 23 42 / 72%);
  padding: 24px;
}

.screenshot-preview-panel {
  display: grid;
  width: min(1120px, 94vw);
  max-height: 92vh;
  grid-template-rows: auto minmax(0, 1fr) auto;
  overflow: hidden;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 24px 80px rgb(0 0 0 / 35%);
}

.screenshot-preview-panel header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid #e5e7eb;
  padding: 12px 16px;
}

.screenshot-preview-panel header button {
  width: 32px;
  height: 32px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  color: #374151;
  cursor: pointer;
  font-size: 20px;
  line-height: 1;
}

.screenshot-preview-panel img {
  display: block;
  width: 100%;
  max-height: calc(92vh - 112px);
  object-fit: contain;
  background: #0f172a;
}

.screenshot-preview-panel p {
  margin: 0;
  border-top: 1px solid #e5e7eb;
  color: #62708a;
  padding: 10px 16px;
  font-size: 13px;
}
</style>
