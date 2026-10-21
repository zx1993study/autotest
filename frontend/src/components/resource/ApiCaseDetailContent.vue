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

    <h4 v-if="showExecution" class="recent-title">最近执行结果</h4>
    <p v-if="loading" class="load-state" role="status">加载最近执行结果...</p>
    <div v-else-if="error" class="load-error" role="alert"><span>加载最近执行结果失败：{{ evidenceText(error) }}</span><button type="button" @click="loadLatestRecord"><RefreshCw :size="14" />重试</button></div>
    <ExecutionRecordEvidence v-if="!loading && !error" :record="latestRecord" :show-execution="showExecution" :fallback-request="caseDefinition" :fallback-assertions="item?.assertions || itemData.assertions" />
    <DynamicValueEvidence v-if="showExecution && latestRecord && !loading" :snapshot="safeDynamicValues" />

    <details class="result-detail">
      <summary>策略信息</summary>
      <pre>{{ evidenceText(strategyRows) }}</pre>
    </details>

    <details class="result-detail">
      <summary>用例定义</summary>
      <pre>{{ evidenceText(caseDefinition) }}</pre>
    </details>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RefreshCw } from 'lucide-vue-next'
import DynamicValueEvidence from '../common/DynamicValueEvidence.vue'
import ExecutionRecordEvidence from '../reports/ExecutionRecordEvidence.vue'
import { useLatestRequest } from '../../composables/useLatestRequest'
import { getResource, listResources } from '../../services/resource.service'
import type { ResourceItem } from '../../types/resource'
import { evidenceText } from '../../utils/executionEvidence'
import { isEvidenceObject as isRecord, redactEvidence } from '../../utils/evidencePrivacy'

const props = withDefaults(defineProps<{ item: ResourceItem | null; showExecution?: boolean }>(), {
  showExecution: true
})

const sourceInterface = ref<ResourceItem | null>(null)
const latestRecord = ref<ResourceItem | null>(null)
const { loading, error, run, cancel } = useLatestRequest('加载最近执行结果失败')
const sourceRequest = useLatestRequest()

const itemData = computed(() => props.item && isRecord(props.item.data) ? props.item.data : {})
const recordData = computed<Record<string, unknown>>(() => {
  const data = latestRecord.value?.data
  return isRecord(data) ? data : {}
})
const safeDynamicValues = computed(() => redactEvidence(recordData.value.dynamic_values))
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

watch(
  () => props.item?.source_id,
  sourceId => {
    sourceRequest.cancel()
    sourceInterface.value = null
    const interfaceId = Number(sourceId)
    if (!Number.isFinite(interfaceId) || interfaceId <= 0) return
    void sourceRequest.run(signal => getResource('/api-testing/interfaces', interfaceId, signal), result => { sourceInterface.value = result })
  },
  { immediate: true }
)

watch(
  () => [props.item?.id, props.item?.project_id, props.showExecution] as const,
  loadLatestRecord,
  { immediate: true }
)

function loadLatestRecord() {
  cancel()
  latestRecord.value = null
  const caseId = Number(props.item?.id)
  if (!props.showExecution || !Number.isFinite(caseId) || caseId <= 0) return
  const params: Record<string, unknown> = { case_id: caseId, case_type: 'API', page: 1, pageSize: 1 }
  const projectId = Number(props.item?.project_id)
  if (Number.isFinite(projectId) && projectId > 0) params.project_id = projectId
  return run(signal => listResources('/reports/records', params, signal), result => { latestRecord.value = result.items[0] || null })
}

function headerValue(headers: Record<string, unknown>, name: string): unknown {
  const target = name.toLowerCase()
  const found = Object.entries(headers).find(([key]) => key.toLowerCase() === target)
  return found?.[1]
}

function readFirst(values: unknown[]): unknown {
  return values.find(value => value != null && value !== '')
}

function formatValue(value: unknown): string {
  if (value == null || value === '') return '-'
  if (typeof value === 'boolean') return value ? '是' : '否'
  return evidenceText(value)
}
</script>

<style scoped>
.api-detail-panel {
  display: grid;
  gap: 12px;
  min-width: 0;
}

.recent-title { margin: 4px 0 0; font-size: 14px; }
.load-state { color: #738095; font-size: 13px; }
.load-error { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; color: #b42318; font-size: 13px; overflow-wrap: anywhere; }
.load-error button { display: inline-flex; align-items: center; gap: 6px; }
@media (max-width: 720px) { .execution-meta { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
</style>
