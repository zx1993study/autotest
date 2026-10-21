<template>
  <section>
    <div class="flow-toolbar"><span>模板 v{{ definition.version }} · {{ definition.nodes.length }} 个节点</span><div class="flow-actions">
      <button title="新增节点" type="button" :disabled="busy" @click="add"><Plus :size="16" />新增节点</button>
      <button class="primary" type="button" :disabled="busy || hasInvalidJson" @click="emit('save')"><Save :size="16" />保存模板</button>
    </div></div>
    <details class="flow-inputs-band"><summary>流程默认输入</summary><FlowParametersEditor v-model="definition.inputs" /></details>
    <div class="flow-template-layout">
      <ViewportScrollArea ref="nodeRail" class="flow-node-rail flow-template-rail" label="流程节点" :active-key="selected" :horizontal-below="700">
        <div v-for="(node, index) in definition.nodes" :key="node.key" :data-scroll-key="node.key" class="flow-rail-item" :class="{active: selected === node.key}">
          <button type="button" class="flow-node-label" data-scroll-focus :title="`${node.name}\n${apiLabel(node.api_id)}`" :aria-pressed="selected === node.key" :tabindex="selected === node.key ? 0 : -1" @click="selected = node.key" @keydown="navigate($event, index)"><span>{{ index + 1 }}</span><div><strong>{{ node.name }}</strong><small>{{ apiLabel(node.api_id) }}</small></div></button>
          <div class="flow-rail-actions"><button type="button" title="上移" aria-label="上移节点" :tabindex="selected === node.key ? 0 : -1" :disabled="busy || index === 0" @click="move(index, -1)"><ArrowUp :size="14" /></button><button type="button" title="下移" aria-label="下移节点" :tabindex="selected === node.key ? 0 : -1" :disabled="busy || index === definition.nodes.length - 1" @click="move(index, 1)"><ArrowDown :size="14" /></button><button type="button" title="删除节点" aria-label="删除节点" :tabindex="selected === node.key ? 0 : -1" :disabled="busy" @click="remove(index)"><Trash2 :size="14" /></button></div>
        </div>
        <p v-if="!definition.nodes.length" class="flow-empty-small">暂无流程节点</p>
      </ViewportScrollArea>
      <ApiFlowNodeEditor v-if="current" :key="current.key" v-model="definition.nodes[currentIndex]!" :project-id="projectId" :apis="apis" :auths="auths" :previous-nodes="definition.nodes.slice(0, currentIndex)" :next-nodes="definition.nodes.slice(currentIndex + 1)" :json-draft="jsonDrafts[current.key]" @draft="setJsonDraft" @validity="setJsonValidity" />
      <div v-else class="flow-empty">暂无节点</div>
    </div>
  </section>
</template>
<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { ArrowUp, ArrowDown, Plus, Save, Trash2 } from 'lucide-vue-next'
import type { FlowDefinition } from '../../types/api-flow'
import type { SelectOptionRecord } from '../../types/resource'
import ApiFlowNodeEditor from './ApiFlowNodeEditor.vue'
import FlowParametersEditor from './FlowParametersEditor.vue'
import { isFlowRequestDraftValid } from '../../utils/apiFlowRequest'
import ViewportScrollArea from '../common/ViewportScrollArea.vue'
const props = defineProps<{projectId: number; apis: SelectOptionRecord[]; auths: SelectOptionRecord[]; busy: boolean}>()
const emit = defineEmits<{(event: 'save'): void}>()
const definition = defineModel<FlowDefinition>({required: true})
const selected = ref('')
const nodeRail = ref<InstanceType<typeof ViewportScrollArea> | null>(null)
const jsonDrafts = ref<Record<string, string | undefined>>({})
const jsonValidity = ref<Record<string, boolean>>({})
const hasInvalidJson = computed(() => jsonValidity.value[selected.value] === false || definition.value.nodes.some(node => {
  const draft = jsonDrafts.value[node.key]
  return draft !== undefined && !isFlowRequestDraftValid(draft)
}))
const currentIndex = computed(() => definition.value.nodes.findIndex(node => node.key === selected.value))
const current = computed(() => definition.value.nodes[currentIndex.value])
function setJsonDraft(key: string, value: string | undefined) { jsonDrafts.value[key] = value }
function setJsonValidity(key: string, valid: boolean) { jsonValidity.value[key] = valid }
watch(() => definition.value.nodes, nodes => { if (!nodes.some(node => node.key === selected.value)) selected.value = nodes[0]?.key || '' }, {immediate: true, deep: true})
function apiLabel(id: number) { const api = props.apis.find(item => item.id === id); return api ? `${api.method || ''} ${api.path || api.name || ''}` : '未选择 API' }
function add() {
  if (props.busy) return
  const key = `node_${Date.now().toString(36)}`
  definition.value.nodes.push({key, name: props.apis[0]?.name || '', api_id: props.apis[0]?.id || 0, case_id: null, auth_id: null, params: {}, request: {}, bindings: [], extracts: [], routes: [], next: 'auto'})
  selected.value = key
}
function move(index: number, offset: number) {
  if (props.busy || index + offset < 0 || index + offset >= definition.value.nodes.length) return
  const node = definition.value.nodes.splice(index, 1)[0]
  if (!node) return
  definition.value.nodes.splice(index + offset, 0, node)
  selected.value = node.key
  void nextTick(() => nodeRail.value?.revealActive())
}
function remove(index: number) {
  const node = definition.value.nodes[index]
  if (!node || props.busy || !window.confirm('删除此节点？引用此节点的参数关联需要同步调整。')) return
  definition.value.nodes.splice(index, 1)
  delete jsonDrafts.value[node.key]
  delete jsonValidity.value[node.key]
  if (selected.value === node.key) selected.value = definition.value.nodes[Math.min(index, definition.value.nodes.length - 1)]?.key || ''
  void nextTick(() => nodeRail.value?.revealActive())
}
function navigate(event: KeyboardEvent, index: number) {
  const last = definition.value.nodes.length - 1
  const target = { ArrowUp: index - 1, ArrowDown: index + 1, ArrowLeft: index - 1, ArrowRight: index + 1, Home: 0, End: last }[event.key]
  if (target === undefined) return
  event.preventDefault()
  selected.value = definition.value.nodes[Math.max(0, Math.min(target, last))]?.key || ''
  void nextTick(() => nodeRail.value?.revealActive(true))
}
</script>
