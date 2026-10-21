<template>
  <div class="flow-backdrop" @click.self="close">
    <section class="flow-dialog flow-scene-dialog" role="dialog" aria-modal="true" aria-label="功能场景配置">
      <header class="flow-dialog-header"><h3>{{ scene.id ? '配置功能场景' : '新增功能场景' }}</h3><button title="关闭" aria-label="关闭" @click="close"><X :size="18" /></button></header>
      <div class="flow-dialog-body">
        <div class="flow-form-grid">
          <label>场景名称<input v-model.trim="draft.name" required /></label>
          <label>状态<select v-model="draft.status"><option value="active">启用</option><option value="disabled">停用</option></select></label>
          <label>节点失败后<select v-model="draft.data.failure_policy"><option value="stop">停止当前场景</option><option value="continue">继续后续独立节点</option></select></label>
          <label>预期结束节点<select v-model="draft.data.expected_end"><option value="auto">自动</option><option v-for="node in definition.nodes" :key="node.key" :value="node.key">{{ draft.data.nodes[node.key]?.name || node.name }}</option></select></label>
          <label class="flow-wide">备注<input v-model="draft.description" /></label>
        </div>
        <FlowParametersEditor v-model="draft.data.inputs" title="场景输入覆盖" />
        <div class="flow-scenario-layout">
          <aside class="flow-node-rail"><button v-for="node in definition.nodes" :key="node.key" class="flow-scene-node" :class="{active: selected === node.key}" @click="selected = node.key"><strong>{{ draft.data.nodes[node.key]?.name || node.name }}</strong><small>{{ modeLabel(draft.data.nodes[node.key]?.mode || 'always') }}</small></button></aside>
          <section v-if="node && override" class="flow-node-editor">
            <div class="flow-form-grid">
              <label class="flow-wide">节点名称<input :value="override.name || ''" :placeholder="node.name" maxlength="200" @input="override.name = ($event.target as HTMLInputElement).value.trim() || null" /></label>
              <label>节点用例<FlowCaseSelect v-model="override.case_id" :api-id="node.api_id" :project-id="projectId" inherit-label="继承模板用例" /></label>
              <label>执行方式<select v-model="override.mode" @change="ensureCondition"><option value="always">始终执行</option><option value="skip">跳过</option><option value="condition">满足条件执行</option></select></label>
            </div>
            <div v-if="override.mode === 'condition' && override.condition" class="flow-rule-row flow-condition-row">
              <label>参数来源<select v-model="override.condition.source"><option value="global">场景输入</option><option v-for="previous in previousNodes" :key="previous.key" :value="previous.key">{{ previous.name }}</option></select></label>
              <label>变量名<input v-model.trim="override.condition.name" /></label>
              <label>判断<select v-model="override.condition.operator"><option v-for="op in operatorOptions" :key="op.value" :value="op.value">{{ op.label }}</option></select></label>
              <label>期望值<FlowValueInput v-model="override.condition.value" /></label>
            </div>
            <div class="flow-subtabs"><button v-for="item in tabs" :key="item.key" :class="{active: tab === item.key}" @click="tab = item.key">{{ item.label }}</button></div>
            <FlowRequestOverridesEditor v-show="tab === 'case'" :key="node.key" :node-key="node.key" :case-id="override.case_id ?? node.case_id" :value="override" :inherited="node" :draft="jsonDrafts[node.key]" title="节点参数覆盖" @change="Object.assign(override, $event)" @draft="setJsonDraft" @validity="setJsonValidity" />
            <template v-if="tab === 'case'">
              <label class="flow-checkbox"><input :checked="override.assertions === null" type="checkbox" @change="override.assertions = ($event.target as HTMLInputElement).checked ? null : [{type: 'status', expected: 200}]" />继承节点用例断言</label>
              <FlowAssertionsEditor v-if="override.assertions !== null" v-model="override.assertions" />
            </template>
            <template v-else>
              <div class="flow-inherit-controls">
                <label class="flow-checkbox"><input :checked="override.bindings === null" type="checkbox" @change="override.bindings = ($event.target as HTMLInputElement).checked ? null : cloneFlowValue(node.bindings)" />继承模板参数关联</label>
                <label class="flow-checkbox"><input :checked="override.extracts === null" type="checkbox" @change="override.extracts = ($event.target as HTMLInputElement).checked ? null : cloneFlowValue(node.extracts)" />继承模板响应提取</label>
              </div>
              <FlowMappingsEditor v-if="override.bindings !== null || override.extracts !== null" v-model:bindings="bindings" v-model:extracts="extracts" :previous-nodes="previousNodes" :readonly-bindings="override.bindings === null" :readonly-extracts="override.extracts === null" />
            </template>
          </section>
        </div>
        <p v-if="error" class="flow-error">{{ error }}</p>
      </div>
      <footer class="flow-dialog-footer"><button @click="close">取消</button><button class="primary" :disabled="busy || !draft.name || hasInvalidJson" @click="emit('save', draft)"><Save :size="16" />保存场景</button></footer>
    </section>
  </div>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Save, X } from 'lucide-vue-next'
import { cloneFlowValue, newScenarioNode, operatorOptions } from '../../types/api-flow'
import type { ApiFlowScenario, FlowDefinition } from '../../types/api-flow'
import FlowCaseSelect from './FlowCaseSelect.vue'
import FlowParametersEditor from './FlowParametersEditor.vue'
import FlowAssertionsEditor from './FlowAssertionsEditor.vue'
import FlowMappingsEditor from './FlowMappingsEditor.vue'
import FlowValueInput from './FlowValueInput.vue'
import FlowRequestOverridesEditor from './FlowRequestOverridesEditor.vue'
import { isFlowRequestDraftValid } from '../../utils/apiFlowRequest'
const props = defineProps<{scene: ApiFlowScenario; definition: FlowDefinition; projectId: number; busy: boolean; error: string}>()
const emit = defineEmits<{(event: 'close'): void; (event: 'save', value: ApiFlowScenario): void}>()
const draft = ref(cloneFlowValue(props.scene))
const baseline = JSON.stringify(props.scene)
const selected = ref(props.definition.nodes[0]?.key || '')
const jsonDrafts = ref<Record<string, string | undefined>>({})
const jsonValidity = ref<Record<string, boolean>>({})
const hasInvalidJson = computed(() => jsonValidity.value[selected.value] === false || props.definition.nodes.some(node => {
  const text = jsonDrafts.value[node.key]
  return text !== undefined && !isFlowRequestDraftValid(text)
}))
const tab = ref('case')
const tabs = [{key: 'case', label: '节点用例与断言'}, {key: 'mappings', label: '参数关联与提取'}]
const nodeIndex = computed(() => props.definition.nodes.findIndex(item => item.key === selected.value))
const node = computed(() => props.definition.nodes[nodeIndex.value])
const previousNodes = computed(() => props.definition.nodes.slice(0, nodeIndex.value).map(node => ({...node, extracts: draft.value.data.nodes[node.key]?.extracts ?? node.extracts})))
watch(selected, key => { if (key && !draft.value.data.nodes[key]) draft.value.data.nodes[key] = newScenarioNode() }, {immediate: true})
const override = computed(() => draft.value.data.nodes[selected.value])
const bindings = computed({get: () => override.value?.bindings ?? cloneFlowValue(node.value?.bindings || []), set: value => { if (override.value) override.value.bindings = value }})
const extracts = computed({get: () => override.value?.extracts ?? cloneFlowValue(node.value?.extracts || []), set: value => { if (override.value) override.value.extracts = value }})
function setJsonDraft(key: string, value: string | undefined) { jsonDrafts.value[key] = value }
function setJsonValidity(key: string, valid: boolean) { jsonValidity.value[key] = valid }
function ensureCondition() { if (override.value && !override.value.condition) override.value.condition = {source: 'global', name: '', operator: 'eq', value: true} }
function modeLabel(mode: string) { return {always: '始终执行', skip: '跳过', condition: '条件执行'}[mode] || mode }
function close() { if ((JSON.stringify(draft.value) === baseline && !Object.values(jsonDrafts.value).some(value => value !== undefined)) || window.confirm('放弃未保存的场景修改？')) emit('close') }
</script>
