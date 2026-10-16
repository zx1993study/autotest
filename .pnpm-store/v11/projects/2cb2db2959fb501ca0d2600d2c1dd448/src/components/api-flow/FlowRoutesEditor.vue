<template>
  <section>
    <header class="flow-section-heading"><h4>结果分支</h4><button type="button" title="新增分支" aria-label="新增分支" @click="routes.push({source: 'body', path: '/code', operator: 'eq', value: 0, target: 'end'})"><Plus :size="16" /></button></header>
    <div v-for="(route, index) in routes" :key="index" class="flow-rule-row flow-route-row">
      <label>响应来源<select v-model="route.source"><option value="body">Body</option><option value="header">Header</option><option value="status">HTTP 状态码</option></select></label>
      <label>路径<input v-model.trim="route.path" :disabled="route.source === 'status'" placeholder="/code" /></label>
      <label>判断<select v-model="route.operator"><option v-for="op in operatorOptions" :key="op.value" :value="op.value">{{ op.label }}</option></select></label>
      <label>期望值<FlowValueInput v-model="route.value" /></label>
      <label>后续节点<select v-model="route.target"><option value="end">结束流程</option><option value="auto">下一个节点</option><option v-for="node in nextNodes" :key="node.key" :value="node.key">{{ node.name }}</option></select></label>
      <button type="button" title="删除分支" aria-label="删除分支" @click="routes.splice(index, 1)"><Trash2 :size="15" /></button>
    </div>
    <p v-if="!routes.length" class="flow-empty-small">暂无结果分支</p>
    <label class="flow-default-next">未匹配分支<select v-model="next"><option value="auto">下一个节点</option><option value="end">结束流程</option><option v-for="node in nextNodes" :key="node.key" :value="node.key">{{ node.name }}</option></select></label>
  </section>
</template>
<script setup lang="ts">
import { Plus, Trash2 } from 'lucide-vue-next'
import { operatorOptions } from '../../types/api-flow'
import type { FlowNode, FlowRoute } from '../../types/api-flow'
import FlowValueInput from './FlowValueInput.vue'
defineProps<{nextNodes: FlowNode[]}>()
const routes = defineModel<FlowRoute[]>('routes', {required: true})
const next = defineModel<string>('next', {required: true})
</script>
