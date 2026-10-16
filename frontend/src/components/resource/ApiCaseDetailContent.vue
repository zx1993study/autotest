<template>
  <section class="api-detail-panel">
    <dl class="execution-meta">
      <div>
        <dt>请求方法</dt>
        <dd>{{ apiMethod }}</dd>
      </div>
      <div>
        <dt>接口路径</dt>
        <dd>{{ apiPath }}</dd>
      </div>
      <div>
        <dt>来源接口</dt>
        <dd>{{ sourceInterfaceName }}</dd>
      </div>
      <div>
        <dt>Content-Type</dt>
        <dd>{{ contentType }}</dd>
      </div>
    </dl>

    <section v-if="showExecution" class="execution-record-card">
      <header class="execution-record-header">
        <div>
          <h4>最近执行结果</h4>
          <p>{{ latestRecord?.name || '暂无执行记录' }}</p>
        </div>
        <span class="status-pill" :class="recordStatusClass">{{ recordStatusText }}</span>
      </header>
      <dl class="execution-meta">
        <div>
          <dt>记录 ID</dt>
          <dd>{{ latestRecord ? `#${latestRecord.id}` : '-' }}</dd>
        </div>
        <div>
          <dt>HTTP 状态</dt>
          <dd>{{ formatValue(recordData.response_status) }}</dd>
        </div>
        <div>
          <dt>耗时</dt>
          <dd>{{ formatDuration(recordData.duration_ms) }}</dd>
        </div>
        <div>
          <dt>错误</dt>
          <dd>{{ formatValue(recordData.error) }}</dd>
        </div>
      </dl>
    </section>

    <DynamicValueEvidence v-if="showExecution" :snapshot="recordData.dynamic_values" />
    <details v-if="showExecution" open class="result-detail">
      <summary>响应体</summary>
      <pre class="json-response">{{ responseBodyText }}</pre>
    </details>

    <details class="result-detail">
      <summary>请求信息</summary>
      <pre>{{ stringifyJson(requestInfo) }}</pre>
    </details>

    <details v-if="showExecution" class="result-detail">
      <summary>响应头</summary>
      <pre>{{ stringifyJson(recordData.response_headers || {}) }}</pre>
    </details>

    <details class="result-detail">
      <summary>断言结果</summary>
      <pre>{{ stringifyJson(assertionRows) }}</pre>
    </details>

    <details class="result-detail">
      <summary>策略信息</summary>
      <pre>{{ stringifyJson(strategyRows) }}</pre>
    </details>

    <details class="result-detail">
      <summary>用例定义</summary>
      <pre>{{ stringifyJson(caseDefinition) }}</pre>
    </details>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import DynamicValueEvidence from '../common/DynamicValueEvidence.vue'
import { getResource, listResources } from '../../services/resource.service'
import type { ResourceItem } from '../../types/resource'
import { formatJsonLikeText } from '../../utils/jsonFormatter'

const props = withDefaults(defineProps<{ item: ResourceItem | null; showExecution?: boolean }>(), {
  showExecution: true
})

const sourceInterface = ref<ResourceItem | null>(null)
const executionRecords = ref<ResourceItem[]>([])
let executionRecordLoadSequence = 0

const itemData = computed(() => props.item && isRecord(props.item.data) ? props.item.data : {})
const latestRecord = computed(() => executionRecords.value[0] || null)
const recordData = computed<Record<string, unknown>>(() => {
  const data = latestRecord.value?.data
  return isRecord(data) ? data : {}
})
const requestInfo = computed(() => {
  const latestRequest = recordData.value.request
  return isRecord(latestRequest) ? latestRequest : caseDefinition.value
})
const caseDefinition = computed(() => {
  const request = itemData.value.request
  if (isRecord(request)) {
    const { request: _request, ...rest } = itemData.value
    void _request
    return { ...request, ...rest }
  }
  return itemData.value
})
const apiMethod = computed(() => formatValue(readFirst([
  itemData.value.api_method,
  itemData.value.method,
  requestInfo.value.method,
  sourceInterface.value?.data?.method
])))
const apiPath = computed(() => formatValue(readFirst([
  itemData.value.api_path,
  itemData.value.path,
  requestInfo.value.path,
  sourceInterface.value?.data?.path
])))
const sourceInterfaceName = computed(() => {
  if (sourceInterface.value) {
    return [sourceInterface.value.name, sourceInterface.value.id ? `#${sourceInterface.value.id}` : '']
      .filter(Boolean)
      .join(' ')
  }
  return props.item?.source_id ? `#${props.item.source_id}` : '-'
})
const contentType = computed(() => formatValue(readFirst([
  itemData.value.content_type,
  requestInfo.value.headers && isRecord(requestInfo.value.headers) ? headerValue(requestInfo.value.headers, 'content-type') : '',
  sourceInterface.value?.data?.content_type
])))
const responseBodyText = computed(() => {
  return formatJsonLikeText(recordData.value.response_body)
})
const assertionRows = computed(() => {
  const runtimeAssertions = recordData.value.assertions
  if (Array.isArray(runtimeAssertions) && runtimeAssertions.length) {
    return runtimeAssertions.filter(isRecord)
  }
  const assertions = props.item?.assertions
  return Array.isArray(assertions) ? assertions.filter(isRecord) : []
})
const strategyRows = computed(() => {
  const strategies = props.item?.strategies
  if (Array.isArray(strategies) && strategies.length) {
    return strategies
  }
  const strategyIds = props.item?.strategy_ids
  if (Array.isArray(strategyIds) && strategyIds.length) {
    return strategyIds.map(id => ({ id }))
  }
  return itemData.value.strategies || itemData.value.strategy_ids || []
})
const recordStatusText = computed(() => {
  const status = String(latestRecord.value?.status || '')
  const labels: Record<string, string> = {
    success: '成功',
    failed: '失败',
    queued: '排队中',
    running: '执行中'
  }
  return status ? labels[status] || status : '未执行'
})
const recordStatusClass = computed(() => {
  const status = String(latestRecord.value?.status || '')
  if (status === 'success') return 'success'
  if (status === 'failed') return 'failed'
  return 'queued'
})

watch(
  () => props.item?.source_id,
  async sourceId => {
    sourceInterface.value = null
    const interfaceId = Number(sourceId)
    if (!Number.isFinite(interfaceId) || interfaceId <= 0) return
    try {
      sourceInterface.value = await getResource('/api-testing/interfaces', interfaceId)
    } catch {
      sourceInterface.value = null
    }
  },
  { immediate: true }
)

watch(
  () => [props.item?.id, props.item?.project_id, props.showExecution] as const,
  async ([caseId, projectId, showExecution]) => {
    executionRecords.value = []
    if (!showExecution) return
    const normalizedCaseId = Number(caseId)
    if (!Number.isFinite(normalizedCaseId) || normalizedCaseId <= 0) return
    const sequence = ++executionRecordLoadSequence
    const params: Record<string, unknown> = {
      case_id: normalizedCaseId,
      case_type: 'API',
      page: 1,
      pageSize: 5
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

function headerValue(headers: Record<string, unknown>, name: string): unknown {
  const target = name.toLowerCase()
  const found = Object.entries(headers).find(([key]) => key.toLowerCase() === target)
  return found?.[1]
}

function readFirst(values: unknown[]): unknown {
  return values.find(value => value != null && value !== '')
}

function formatDuration(value: unknown): string {
  const duration = Number(value)
  return Number.isFinite(duration) ? `${duration} ms` : '-'
}

function stringifyJson(value: unknown): string {
  return JSON.stringify(value ?? {}, null, 2)
}

function formatValue(value: unknown): string {
  if (value == null || value === '') return '-'
  if (typeof value === 'boolean') return value ? '是' : '否'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}
</script>

<style scoped>
.api-detail-panel {
  display: grid;
  gap: 12px;
}

.execution-record-card {
  display: grid;
  gap: 12px;
  border: 1px solid #edf1f7;
  border-radius: 8px;
  background: #fff;
  padding: 12px;
}

.json-response {
  tab-size: 2;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
