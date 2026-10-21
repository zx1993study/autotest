<template>
  <Teleport to="body">
    <dialog ref="dialog" class="api-flow flow-dialog flow-run-result-dialog" aria-modal="true" aria-labelledby="flow-run-result-title" @cancel.prevent="emit('close')" @click.self="emit('close')">
      <header class="flow-dialog-header">
        <div><h3 id="flow-run-result-title">运行结果 #{{ batch.id }}</h3><p class="flow-muted">{{ batch.name }} · {{ label(batch.status) }}</p></div>
        <div class="flow-actions"><button v-if="!readOnly && ['running', 'queued'].includes(batch.status)" class="flow-danger" :disabled="busy" @click="emit('cancel', batch.id)"><Square :size="14" />取消执行</button><button autofocus title="关闭运行结果" aria-label="关闭运行结果" @click="emit('close')"><X :size="18" /></button></div>
      </header>
      <div class="flow-dialog-body">
        <div class="flow-results-layout">
          <aside class="flow-node-rail"><button v-for="scene in batch.data.results" :key="scene.scenario_id" class="flow-scene-node" :class="{active: selectedScene === scene.scenario_id}" :aria-pressed="selectedScene === scene.scenario_id" @click="selectedScene = scene.scenario_id"><strong>{{ scene.name }}</strong><small class="flow-status" :class="scene.status">{{ label(scene.status) }}{{ scene.duration_ms != null ? ` · ${scene.duration_ms} ms` : '' }}</small></button></aside>
          <section v-if="result" class="flow-evidence">
            <div class="flow-segments" aria-label="节点筛选"><button :class="{active: !failedOnly}" :aria-pressed="!failedOnly" @click="failedOnly = false"><List :size="14" />全部节点 ({{ nodes.length }})</button><button v-if="failedNodes.length" :class="{active: failedOnly}" :aria-pressed="failedOnly" @click="failedOnly = true"><CircleAlert :size="14" />失败节点 ({{ failedNodes.length }})</button></div>
            <details v-if="result.path?.length" class="flow-result-path"><summary>执行路径 ({{ result.path.length }})</summary><div class="flow-path">{{ result.path.join(' → ') }}</div></details>
            <p v-if="result.error || result.end_passed === false" class="flow-error">{{ result.error || `实际结束节点与预期 ${result.expected_end} 不一致` }}</p>
            <details v-for="node in visibleNodes" :key="node.key" class="flow-node-evidence" :open="node.status === 'failed'">
              <summary><span><strong>{{ node.name }}</strong><small>{{ node.response_status != null ? `HTTP ${node.response_status} · ` : '' }}{{ node.response_code != null ? `code ${node.response_code} · ` : '' }}{{ node.duration_ms != null ? `${node.duration_ms} ms` : '' }}</small></span><span class="flow-status" :class="node.status">{{ label(node.status) }}</span></summary>
              <p v-if="node.reason" class="flow-muted">{{ node.reason }}</p><p v-if="node.error" class="flow-error">{{ node.error }}</p>
              <p v-if="node.status === 'failed' && responseMessage(node.response_body)" class="flow-error">{{ responseMessage(node.response_body) }}</p>
              <template v-if="node.request"><h5>请求</h5><pre>{{ json(node.request) }}</pre><h5>响应</h5><pre>{{ json({status: node.response_status, headers: node.response_headers, body: parseBody(node.response_body)}) }}</pre><h5>断言</h5><pre>{{ json(node.assertions) }}</pre><h5>提取变量</h5><pre>{{ json(node.outputs || {}) }}</pre></template>
            </details>
            <p v-if="!nodes.length" class="flow-empty">{{ ['queued', 'running'].includes(result.status) ? '等待场景执行完成' : '暂无节点证据' }}</p>
          </section>
          <p v-else class="flow-empty">暂无场景结果</p>
        </div>
      </div>
    </dialog>
  </Teleport>
</template>
<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { CircleAlert, List, Square, X } from 'lucide-vue-next'
import { flowStatusLabels } from '../../types/api-flow'
import type { ApiFlowRun } from '../../types/api-flow'
import { evidenceText } from '../../utils/executionEvidence'
import { parseEvidence } from '../../utils/evidencePrivacy'
const props = defineProps<{batch: ApiFlowRun; busy: boolean; initialScenarioId?: number; readOnly?: boolean}>()
const emit = defineEmits<{(event: 'close'): void; (event: 'cancel', id: number): void}>()
const dialog = ref<HTMLDialogElement | null>(null)
const selectedScene = ref(0)
const failedOnly = ref(false)
const result = computed(() => props.batch.data.results.find(row => row.scenario_id === selectedScene.value))
const nodes = computed(() => result.value?.nodes || [])
const failedNodes = computed(() => nodes.value.filter(node => node.status === 'failed'))
const visibleNodes = computed(() => failedOnly.value ? failedNodes.value : nodes.value)
watch(() => props.batch, (batch, previous) => {
  if (batch.id !== previous?.id || !batch.data.results.some(row => row.scenario_id === selectedScene.value)) {
    selectedScene.value = (batch.data.results.find(row => row.scenario_id === props.initialScenarioId) || batch.data.results.find(row => row.status === 'failed') || batch.data.results[0])?.scenario_id || 0
  }
}, {immediate: true})
watch(() => [props.batch.id, selectedScene.value, result.value?.status], () => { failedOnly.value = failedNodes.value.length > 0 }, {immediate: true})
onMounted(() => dialog.value?.showModal())
onBeforeUnmount(() => dialog.value?.close())
const label = (status: string) => flowStatusLabels[status] || status
const json = evidenceText
const parseBody = parseEvidence
function responseMessage(value?: string) {
  const body = parseBody(value)
  const message = body && typeof body === 'object' ? (body as Record<string, unknown>).msg || (body as Record<string, unknown>).message : null
  return typeof message === 'string' ? message : ''
}
</script>
