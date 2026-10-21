<template>
  <div class="web-execution-result" @keydown.enter.stop>
    <span v-if="loading" class="result-loading" role="status">加载中...</span>
    <button v-else-if="error" type="button" class="result-retry" :title="error" aria-label="重试加载执行结果" @click.stop="emit('retry')"><RefreshCw :size="13" />加载失败</button>
    <template v-else-if="summary">
      <button v-if="summary.record_id" type="button" class="result-link" :class="summary.status" :title="summary.status === 'failed' ? '查看最近失败记录' : '查看最近执行记录'" :aria-label="`查看${labels[summary.status]}执行结果`" @click.stop="emit('open', summary.record_id)"><component :is="icon" :size="14" />{{ labels[summary.status] }}<Eye :size="12" /></button>
      <span v-else class="result-label" :class="summary.status"><component :is="icon" :size="14" />{{ labels[summary.status] }}</span>
      <small v-if="aggregate && summary.total_count" class="result-counts">{{ counts }}</small>
      <time v-if="summary.executed_at" :datetime="summary.executed_at" :title="`最近执行：${summary.executed_at}`">{{ summary.executed_at.replace('T', ' ').slice(0, 16) }}</time>
    </template>
    <span v-else class="result-label">-</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Ban, CircleCheck, CircleDashed, CircleHelp, CircleX, Eye, LoaderCircle, RefreshCw } from 'lucide-vue-next'
import type { WebExecutionStatus, WebExecutionSummary } from '../../types/web-execution'

const props = defineProps<{ summary?: WebExecutionSummary; loading?: boolean; error?: string; aggregate?: boolean }>()
const emit = defineEmits<{ open: [id: number]; retry: [] }>()
const labels: Record<WebExecutionStatus, string> = { success: '成功', failed: '失败', not_run: '未执行', partial: '部分执行', unverified: '未验证', running: '执行中', canceled: '已取消', empty: '无用例' }
const icon = computed(() => ({ success: CircleCheck, failed: CircleX, running: LoaderCircle, canceled: Ban, unverified: CircleHelp, partial: CircleDashed, not_run: CircleDashed, empty: CircleDashed })[props.summary?.status || 'not_run'])
const counts = computed(() => {
  const value = props.summary
  if (!value) return ''
  return [value.success_count && `成功 ${value.success_count}`, value.failed_count && `失败 ${value.failed_count}`,
    value.not_run_count && `未执行 ${value.not_run_count}`, value.unverified_count && `未验证 ${value.unverified_count}`,
    value.running_count && `执行中 ${value.running_count}`, value.canceled_count && `取消 ${value.canceled_count}`].filter(Boolean).join(' / ')
})
</script>

<style scoped>
.web-execution-result { display: grid; align-content: start; gap: 4px; min-height: 40px; min-width: 0; font-size: 13px; line-height: 1.4; }
.result-link, .result-label, .result-retry { display: inline-flex; align-items: center; gap: 5px; width: fit-content; max-width: 100%; color: #657184; }
.result-link, .result-retry { border: 0; padding: 0; background: none; font-size: inherit; min-height: 20px; }
.result-link:hover { text-decoration: underline; }
.result-link:focus-visible, .result-retry:focus-visible { outline: 2px solid #087a87; outline-offset: 3px; }
.success { color: #157347; } .failed, .result-retry { color: #b42318; } .partial, .unverified { color: #946400; } .running { color: #186ca4; }
.result-counts, time, .result-loading { color: #687589; font-size: 12px; overflow-wrap: anywhere; }
time { font-variant-numeric: tabular-nums; white-space: nowrap; }
</style>
