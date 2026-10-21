<template>
  <section>
    <div class="flow-toolbar"><strong>运行记录</strong><button :disabled="busy" title="刷新运行记录" @click="emit('refresh')"><RefreshCw :size="16" />刷新</button></div>
    <div class="flow-table-wrap"><table><thead><tr><th>批次</th><th>模板</th><th>模式</th><th>场景结果</th><th>状态</th><th>操作</th></tr></thead><tbody>
      <tr v-for="batch in runs" :key="batch.id" :class="{'flow-selected-row': current?.id === batch.id}"><td>{{ batch.name }}</td><td>v{{ batch.data.template_version }}</td><td>{{ batch.data.mode === 'parallel' ? `并行 (${batch.data.concurrency})` : '串行' }}</td><td>{{ batch.data.results.filter(row => row.status === 'success').length }} / {{ batch.data.results.length }} 通过</td><td><span class="flow-status" :class="batch.status">{{ label(batch.status) }}</span></td><td><button :disabled="busy" @click="emit('select', batch.id)">查看结果</button></td></tr>
      <tr v-if="!runs.length"><td colspan="6" class="flow-empty">暂无运行记录</td></tr>
    </tbody></table></div>
    <ApiFlowRunDetailDialog v-if="current" :batch="current" :busy="busy" @close="emit('close')" @cancel="emit('cancel', $event)" />
  </section>
</template>
<script setup lang="ts">
import { RefreshCw } from 'lucide-vue-next'
import { flowStatusLabels } from '../../types/api-flow'
import type { ApiFlowRun } from '../../types/api-flow'
import ApiFlowRunDetailDialog from './ApiFlowRunDetailDialog.vue'
defineProps<{runs: ApiFlowRun[]; current: ApiFlowRun | null; busy: boolean}>()
const emit = defineEmits<{(event: 'refresh' | 'close'): void; (event: 'select' | 'cancel', id: number): void}>()
const label = (status: string) => flowStatusLabels[status] || status
</script>
