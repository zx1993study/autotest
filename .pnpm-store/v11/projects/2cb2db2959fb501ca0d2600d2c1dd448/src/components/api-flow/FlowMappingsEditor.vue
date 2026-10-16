<template>
  <section>
    <fieldset :disabled="readonlyBindings">
    <header class="flow-section-heading"><h4>参数关联</h4><button type="button" title="新增关联" aria-label="新增关联" @click="bindings.push({source: previousNodes.at(-1)?.key || 'global', name: '', target: 'auto', target_name: '', path: '', prefix: ''})"><Plus :size="16" /></button></header>
    <div v-for="(binding, index) in bindings" :key="index" class="flow-rule-row flow-binding-row">
      <label>来源节点<select v-model="binding.source"><option value="global">场景输入</option><option v-for="node in previousNodes" :key="node.key" :value="node.key">{{ node.name }}</option></select></label>
      <label>来源变量名<input v-model.trim="binding.name" :list="`variables-${binding.source}`" /></label>
      <label>目的变量名<input :value="targetName(binding)" @input="setTargetName(binding, ($event.target as HTMLInputElement).value)" /></label>
      <button type="button" title="删除关联" aria-label="删除关联" @click="bindings.splice(index, 1)"><Trash2 :size="15" /></button>
      <details class="flow-binding-extra"><summary>高级设置</summary><label>值前缀<input v-model="binding.prefix" placeholder="Bearer " /></label></details>
    </div>
    <datalist v-for="node in previousNodes" :id="`variables-${node.key}`" :key="node.key"><option v-for="extraction in node.extracts" :key="extraction.name" :value="extraction.name" /></datalist>
    <p v-if="!bindings.length" class="flow-empty-small">暂无参数关联</p>
    </fieldset>
    <fieldset :disabled="readonlyExtracts">
    <header class="flow-section-heading"><h4>响应提取</h4><button type="button" title="新增提取" aria-label="新增提取" @click="extracts.push({name: '', source: 'body', path: '/data/id', mode: 'single', paths: [], required: true, sensitive: false})"><Plus :size="16" /></button></header>
    <div v-for="(extraction, index) in extracts" :key="index" class="flow-rule-row flow-extract-row">
      <label>变量名<input v-model.trim="extraction.name" /></label>
      <label>来源<select v-model="extraction.source" @change="setExtractSource(extraction)"><option value="body">Body</option><option value="header">Header</option><option value="status">HTTP 状态码</option></select></label>
      <label>输出类型<select :value="extraction.mode || 'single'" :disabled="extraction.source === 'status'" @change="setExtractMode(extraction, ($event.target as HTMLSelectElement).value)"><option value="single">单值</option><option value="array">数组</option></select></label>
      <label class="flow-checkbox"><input v-model="extraction.required" type="checkbox" />必需</label>
      <label class="flow-checkbox"><input v-model="extraction.sensitive" type="checkbox" />敏感</label>
      <button type="button" title="删除提取" aria-label="删除提取" @click="extracts.splice(index, 1)"><Trash2 :size="15" /></button>
      <div v-if="extraction.source !== 'status'" class="flow-extract-paths">
        <template v-if="extraction.mode === 'array'">
          <div v-for="(_, pathIndex) in extraction.paths" :key="pathIndex" class="flow-extract-path-row">
            <label>提取路径 {{ pathIndex + 1 }}<input v-model.trim="extraction.paths![pathIndex]" placeholder="/data/list/0/id" /></label>
            <button type="button" title="删除路径" aria-label="删除提取路径" :disabled="extraction.paths!.length === 1" @click="extraction.paths!.splice(pathIndex, 1)"><Trash2 :size="15" /></button>
          </div>
          <button type="button" title="新增精确路径" aria-label="新增提取路径" @click="extraction.paths!.push('')"><Plus :size="15" /></button>
        </template>
        <label v-else>提取路径<input v-model.trim="extraction.path" placeholder="/data/id" /></label>
      </div>
    </div>
    <p v-if="!extracts.length" class="flow-empty-small">暂无响应提取</p>
    </fieldset>
  </section>
</template>
<script setup lang="ts">
import { Plus, Trash2 } from 'lucide-vue-next'
import type { FlowBinding, FlowExtract, FlowNode } from '../../types/api-flow'
defineProps<{previousNodes: FlowNode[]; readonlyBindings?: boolean; readonlyExtracts?: boolean}>()
const bindings = defineModel<FlowBinding[]>('bindings', {required: true})
const extracts = defineModel<FlowExtract[]>('extracts', {required: true})
function targetName(binding: FlowBinding) {
  return binding.target === 'auto' ? binding.target_name || '' : (binding.path.split('/').at(-1) || '').replace(/~1/g, '/').replace(/~0/g, '~')
}
function setTargetName(binding: FlowBinding, name: string) {
  binding.target_name = name.trim(); binding.target = 'auto'; binding.path = ''
}
function setExtractMode(extraction: FlowExtract, mode: string) {
  extraction.mode = mode === 'array' ? 'array' : 'single'
  if (extraction.mode === 'array' && !extraction.paths?.length) extraction.paths = [extraction.path || '/data/id']
  if (extraction.mode === 'single' && extraction.paths?.length) extraction.path = extraction.paths[0]!
}
function setExtractSource(extraction: FlowExtract) { if (extraction.source === 'status') extraction.mode = 'single' }
</script>
