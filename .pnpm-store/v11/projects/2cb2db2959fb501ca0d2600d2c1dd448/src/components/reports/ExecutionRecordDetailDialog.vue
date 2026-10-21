<template>
  <ResultDetailDialog :title="`执行结果 #${recordId}`" @close="emit('close')">
    <p v-if="loading" class="state" role="status">加载中...</p>
    <div v-else-if="error" class="error-state" role="alert"><p>加载执行结果失败：{{ evidenceText(error) }}</p><button type="button" @click="load"><RefreshCw :size="14" />重试</button></div>
    <ExecutionRecordEvidence v-else-if="record" :record="record" />
    <p v-else class="state">未找到执行记录</p>
  </ResultDetailDialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { RefreshCw } from 'lucide-vue-next'
import ResultDetailDialog from '../common/ResultDetailDialog.vue'
import { useLatestRequest } from '../../composables/useLatestRequest'
import { getExecutionRecord } from '../../services/execution-record.service'
import type { ResourceItem } from '../../types/resource'
import { evidenceText } from '../../utils/executionEvidence'
import ExecutionRecordEvidence from './ExecutionRecordEvidence.vue'

const props = defineProps<{ recordId: number }>()
const emit = defineEmits<{ close: [] }>()
const record = ref<ResourceItem | null>(null)
const { loading, error, run } = useLatestRequest('加载执行结果失败')
function load() {
  record.value = null
  return run(signal => getExecutionRecord(props.recordId, signal), result => { record.value = result })
}
watch(() => props.recordId, load, { immediate: true })
</script>

<style scoped>
.state { padding: 30px 12px; text-align: center; color: #738095; }
.error-state { padding: 12px; color: #b42318; overflow-wrap: anywhere; }
.error-state button { display: inline-flex; align-items: center; gap: 6px; }
</style>
