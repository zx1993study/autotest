<template>
  <section>
    <div class="flow-toolbar"><span>模板 v{{ definition.version }} · {{ definition.nodes.length }} 个节点</span><div class="flow-actions">
      <button title="新增节点" type="button" @click="add"><Plus :size="16" />新增节点</button>
      <button class="primary" type="button" :disabled="busy || hasInvalidJson" @click="emit('save')"><Save :size="16" />保存模板</button>
    </div></div>
    <details class="flow-inputs-band"><summary>流程默认输入</summary><FlowParametersEditor v-model="definition.inputs" /></details>
    <div class="flow-template-layout">
      <aside class="flow-node-rail">
        <div v-for="(node, index) in definition.nodes" :key="node.key" class="flow-rail-item" :class="{active: selected === node.key}">
          <button class="flow-node-label" @click="selected = node.key"><span>{{ index + 1 }}</span><div><strong>{{ node.name }}</strong><small>{{ apiLabel(node.api_id) }}</small></div></button>
          <div class="flow-rail-actions"><button title="上移" aria-label="上移节点" :disabled="index === 0" @click="move(index, -1)"><ArrowUp :size="14" /></button><button title="下移" aria-label="下移节点" :disabled="index === definition.nodes.length - 1" @click="move(index, 1)"><ArrowDown :size="14" /></button><button title="删除节点" aria-label="删除节点" @click="remove(index)"><Trash2 :size="14" /></button></div>
        </div>
        <p v-if="!definition.nodes.length" class="flow-empty-small">暂无流程节点</p>
      </aside>
      <ApiFlowNodeEditor v-if="current" :key="current.key" v-model="definition.nodes[currentIndex]!" :project-id="projectId" :apis="apis" :auths="auths" :previous-nodes="definition.nodes.slice(0, currentIndex)" :next-nodes="definition.nodes.slice(currentIndex + 1)" :json-draft="jsonDrafts[current.key]" @draft="setJsonDraft" @validity="setJsonValidity" />
      <div v-else class="flow-empty">暂无节点</div>
    </div>
  </section>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ArrowUp, ArrowDown, Plus, Save, Trash2 } from 'lucide-vue-next'
import type { FlowDefinition } from '../../types/api-flow'
import type { SelectOptionRecord } from '../../types/resource'
import ApiFlowNodeEditor from './ApiFlowNodeEditor.vue'
import FlowParametersEditor from './FlowParametersEditor.vue'
import { isFlowRequestDraftValid } from '../../utils/apiFlowRequest'
const props = defineProps<{projectId: number; apis: SelectOptionRecord[]; auths: SelectOptionRecord[]; busy: boolean}>()
const emit = defineEmits<{(event: 'save'): void}>()
const definition = defineModel<FlowDefinition>({required: true})
const selected = ref('')
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
  const key = `node_${Date.now().toString(36)}`
  definition.value.nodes.push({key, name: `节点 ${definition.value.nodes.length + 1}`, api_id: props.apis[0]?.id || 0, case_id: null, auth_id: null, params: {}, request: {}, bindings: [], extracts: [], routes: [], next: 'auto'})
  selected.value = key
}
function move(index: number, offset: number) {
  const node = definition.value.nodes.splice(index, 1)[0]
  if (node) definition.value.nodes.splice(index + offset, 0, node)
}
function remove(index: number) { if (window.confirm('删除此节点？引用此节点的参数关联需要同步调整。')) definition.value.nodes.splice(index, 1) }
</script>
