<template>
  <section class="flow-node-editor">
    <div class="flow-form-grid">
      <label>节点名称<input v-model.trim="node.name" /></label>
      <label>节点标识<input :value="node.key" readonly /></label>
      <label class="flow-wide">节点 API<ApiSelect v-model="node.api_id" :options="apis" label="节点 API" @change="node.case_id = null" /></label>
      <label>默认节点用例<FlowCaseSelect v-model="node.case_id" :api-id="node.api_id" :project-id="projectId" /></label>
      <label>认证<select v-model="node.auth_id"><option :value="null">继承用例 / API 认证</option><option v-for="auth in auths" :key="auth.id" :value="auth.id">{{ auth.name }}</option></select></label>
    </div>
    <div class="flow-subtabs"><button v-for="item in tabs" :key="item.key" :class="{active: tab === item.key}" @click="tab = item.key">{{ item.label }}</button></div>
    <FlowRequestOverridesEditor v-show="tab === 'params'" :node-key="node.key" :case-id="node.case_id" :value="node" :draft="jsonDraft" title="默认参数覆盖" @change="Object.assign(node, $event)" @draft="forwardDraft" @validity="forwardValidity" />
    <FlowMappingsEditor v-if="tab === 'mappings'" v-model:bindings="node.bindings" v-model:extracts="node.extracts" :previous-nodes="previousNodes" />
    <FlowRoutesEditor v-if="tab === 'routes'" v-model:routes="node.routes" v-model:next="node.next" :next-nodes="nextNodes" />
  </section>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import type { FlowNode } from '../../types/api-flow'
import type { SelectOptionRecord } from '../../types/resource'
import ApiSelect from '../common/ApiSelect.vue'
import FlowCaseSelect from './FlowCaseSelect.vue'
import FlowRequestOverridesEditor from './FlowRequestOverridesEditor.vue'
import FlowMappingsEditor from './FlowMappingsEditor.vue'
import FlowRoutesEditor from './FlowRoutesEditor.vue'
defineProps<{projectId: number; apis: SelectOptionRecord[]; auths: SelectOptionRecord[]; previousNodes: FlowNode[]; nextNodes: FlowNode[]; jsonDraft?: string}>()
const emit = defineEmits<{(event: 'draft', key: string, value: string | undefined): void; (event: 'validity', key: string, valid: boolean): void}>()
const node = defineModel<FlowNode>({required: true})
const tab = ref('params')
const tabs = [{key: 'params', label: '节点参数'}, {key: 'mappings', label: '参数关联与提取'}, {key: 'routes', label: '结果分支'}]
function forwardDraft(key: string, value: string | undefined) { emit('draft', key, value) }
function forwardValidity(key: string, valid: boolean) { emit('validity', key, valid) }
</script>
