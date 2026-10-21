<template>
  <ExecutionRecordDetailDialog v-if="row.kind === 'api'" :record-id="row.record_id" @close="emit('close')" />
  <ApiFlowRunDetailDialog v-else-if="batch" :batch="batch" :busy="false" :initial-scenario-id="row.scenario_id || undefined" read-only @close="emit('close')" />
  <ResultDetailDialog v-else :title="`流程运行结果 #${row.record_id}`" @close="emit('close')">
    <p v-if="loading" role="status">加载中...</p>
    <div v-else-if="error" role="alert"><p>{{ evidenceText(error) }}</p><button type="button" @click="load"><RefreshCw :size="14" />重试</button></div>
  </ResultDetailDialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { RefreshCw } from 'lucide-vue-next'
import ApiFlowRunDetailDialog from '../api-flow/ApiFlowRunDetailDialog.vue'
import ResultDetailDialog from '../common/ResultDetailDialog.vue'
import ExecutionRecordDetailDialog from './ExecutionRecordDetailDialog.vue'
import { useLatestRequest } from '../../composables/useLatestRequest'
import { getFlowRun } from '../../services/api-flow.service'
import type { ApiFlowRun } from '../../types/api-flow'
import type { ApiReportRow } from '../../types/api-report'
import { evidenceText } from '../../utils/executionEvidence'

const props = defineProps<{ row: ApiReportRow }>()
const emit = defineEmits<{ close: [] }>()
const batch = ref<ApiFlowRun | null>(null)
const { loading, error, run, cancel } = useLatestRequest('加载流程结果失败')
function load() {
  cancel()
  batch.value = null
  if (props.row.kind !== 'flow') return
  return run(async signal => {
    if (!props.row.flow_id) throw new Error('历史记录未保存流程 ID')
    const result = await getFlowRun(props.row.flow_id, props.row.record_id, signal)
    if (!result) throw new Error('未找到流程运行记录')
    return result
  }, result => { batch.value = result })
}
watch(() => props.row.key, load, { immediate: true })
</script>
