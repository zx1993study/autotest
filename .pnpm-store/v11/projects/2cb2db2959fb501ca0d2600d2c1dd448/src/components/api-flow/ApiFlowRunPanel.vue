<template>
  <section>
    <div class="flow-toolbar"><strong>运行记录</strong><button :disabled="busy" title="刷新运行记录" @click="emit('refresh')"><RefreshCw :size="16" />刷新</button></div>
    <div class="flow-table-wrap"><table><thead><tr><th>批次</th><th>模板</th><th>模式</th><th>场景结果</th><th>状态</th><th>操作</th></tr></thead><tbody>
      <tr v-for="batch in runs" :key="batch.id" :class="{'flow-selected-row': current?.id === batch.id}"><td>{{ batch.name }}</td><td>v{{ batch.data.template_version }}</td><td>{{ batch.data.mode === 'parallel' ? `并行 (${batch.data.concurrency})` : '串行' }}</td><td>{{ batch.data.results.filter(row => row.status === 'success').length }} / {{ batch.data.results.length }} 通过</td><td><span class="flow-status" :class="batch.status">{{ label(batch.status) }}</span></td><td><button :disabled="busy" @click="emit('select', batch.id)">查看结果</button></td></tr>
      <tr v-if="!runs.length"><td colspan="6" class="flow-empty">暂无运行记录</td></tr>
    </tbody></table></div>
    <section v-if="current" class="flow-run-detail">
      <header class="flow-section-heading"><h4>{{ current.name }} · {{ label(current.status) }}</h4><button v-if="['running', 'queued'].includes(current.status)" class="flow-danger" :disabled="busy" @click="emit('cancel', current.id)"><Square :size="14" />取消执行</button></header>
      <div class="flow-results-layout"><aside class="flow-node-rail"><button v-for="scene in current.data.results" :key="scene.scenario_id" class="flow-scene-node" :class="{active: selectedScene === scene.scenario_id}" @click="selectedScene = scene.scenario_id"><strong>{{ scene.name }}</strong><small class="flow-status" :class="scene.status">{{ label(scene.status) }}{{ scene.duration_ms != null ? ` · ${scene.duration_ms} ms` : '' }}</small></button></aside>
        <section v-if="result" class="flow-evidence">
          <div class="flow-path">{{ result.path?.join(' → ') || '暂无执行路径' }}</div>
          <p v-if="result.error || result.end_passed === false" class="flow-error">{{ result.error || `实际结束节点与预期 ${result.expected_end} 不一致` }}</p>
          <details v-for="node in result.nodes" :key="node.key" class="flow-node-evidence" :open="node.status === 'failed'">
            <summary><span><strong>{{ node.name }}</strong><small>{{ node.response_status ? `HTTP ${node.response_status} · ` : '' }}{{ node.duration_ms != null ? `${node.duration_ms} ms` : '' }}</small></span><span class="flow-status" :class="node.status">{{ label(node.status) }}</span></summary>
            <p v-if="node.reason" class="flow-muted">{{ node.reason }}</p><p v-if="node.error" class="flow-error">{{ node.error }}</p>
            <template v-if="node.request"><h5>请求</h5><pre>{{ json(node.request) }}</pre><h5>响应</h5><pre>{{ json({status: node.response_status, headers: node.response_headers, body: parseBody(node.response_body)}) }}</pre><h5>断言</h5><pre>{{ json(node.assertions) }}</pre><h5>提取变量</h5><pre>{{ json(node.outputs || {}) }}</pre></template>
          </details>
          <p v-if="!result.nodes.length" class="flow-empty">{{ ['queued', 'running'].includes(result.status) ? '等待场景执行完成' : '暂无节点证据' }}</p>
        </section>
      </div>
    </section>
  </section>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RefreshCw, Square } from 'lucide-vue-next'
import { flowStatusLabels } from '../../types/api-flow'
import type { ApiFlowRun } from '../../types/api-flow'
const props = defineProps<{runs: ApiFlowRun[]; current: ApiFlowRun | null; busy: boolean}>()
const emit = defineEmits<{(event: 'refresh'): void; (event: 'select' | 'cancel', id: number): void}>()
const selectedScene = ref(0)
const result = computed(() => props.current?.data.results.find(row => row.scenario_id === selectedScene.value))
watch(() => props.current, batch => { if (!batch?.data.results.some(row => row.scenario_id === selectedScene.value)) selectedScene.value = batch?.data.results[0]?.scenario_id || 0 }, {immediate: true})
const label = (status: string) => flowStatusLabels[status] || status
const json = (value: unknown) => JSON.stringify(value, null, 2)
function parseBody(value?: string) { try { return JSON.parse(value || '') } catch { return value || '' } }
</script>
