<template>
  <p v-if="!rows.length" class="empty">未记录断言</p>
  <ol v-else>
    <li v-for="(row, index) in rows" :key="index" :data-outcome="row.outcome">
      <header>
        <strong>{{ row.definition.type || `断言 ${index + 1}` }}</strong>
        <span :class="row.outcome"><component :is="icons[row.outcome]" :size="14" />{{ labels[row.outcome] }}</span>
      </header>
      <pre>{{ evidenceText(row.definition) }}</pre>
    </li>
  </ol>
</template>

<script setup lang="ts">
import { CircleCheck, CircleX, CircleHelp } from 'lucide-vue-next'
import type { ExecutionAssertionView } from '../../types/execution-evidence'
import { evidenceText } from '../../utils/executionEvidence'

defineProps<{ rows: ExecutionAssertionView[] }>()
const icons = { passed: CircleCheck, failed: CircleX, unknown: CircleHelp }
const labels = { passed: '通过', failed: '失败', unknown: '未记录结果' }
</script>

<style scoped>
ol { list-style: none; padding: 0; margin: 0; }
li + li { border-top: 1px solid #e7ecf2; margin-top: 14px; padding-top: 14px; }
header { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; margin-bottom: 8px; font-size: 13px; }
strong { overflow-wrap: anywhere; min-width: 0; }
span { display: inline-flex; align-items: center; gap: 4px; flex-shrink: 0; }
.passed { color: #157347; } .failed { color: #b42318; } .unknown, .empty { color: #738095; }
.empty { margin: 0; font-size: 13px; }
pre { margin: 0; white-space: pre-wrap; overflow-wrap: anywhere; font: 12px/1.65 Consolas, 'Courier New', monospace; }
</style>
