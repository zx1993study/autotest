<template>
  <div class="mini-backdrop" @click.self="emit('close')"><section class="mini-dialog" role="dialog" aria-modal="true" aria-label="小程序运行结果" @keydown.esc="emit('close')">
    <header><h3>批次 #{{ run.id }} · {{ sourceStatuses[run.status] || run.status }}</h3><div class="mini-toolbar"><button title="下载 JSON 报告" aria-label="下载 JSON 报告" @click="download"><Download :size="18" /></button><button title="关闭" aria-label="关闭" @click="emit('close')"><X :size="18" /></button></div></header>
    <p v-if="run.data.error" class="mini-error">{{ run.data.error }}</p>
    <div class="mini-table-scroll"><table><thead><tr><th>用例</th><th>结果</th><th>实际执行</th><th>原因</th></tr></thead><tbody>
      <tr v-for="result in run.data.results" :key="result.case_id"><td>#{{ result.case_id }} {{ result.name }}</td><td>{{ sourceStatuses[result.status] || result.status }}</td><td>{{ result.executed ? '是' : '否' }}</td><td>{{ result.reason || '-' }}</td></tr>
      <tr v-if="!run.data.results?.length"><td colspan="4">{{ ['queued', 'running'].includes(run.status) ? '执行中，等待结果' : '暂无结果' }}</td></tr>
    </tbody></table></div>
  </section></div>
</template>
<script setup lang="ts">
import { Download, X } from 'lucide-vue-next'
import { sourceStatuses, type SourceRun } from '../../types/miniapp-source'
const props = defineProps<{ run: SourceRun }>()
const emit = defineEmits<{ (event: 'close'): void }>()
function download() {
  const url = URL.createObjectURL(new Blob([JSON.stringify(props.run, null, 2)], { type: 'application/json' }))
  const link = document.createElement('a')
  link.href = url; link.download = `miniapp-run-${props.run.id}.json`; link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
</script>
