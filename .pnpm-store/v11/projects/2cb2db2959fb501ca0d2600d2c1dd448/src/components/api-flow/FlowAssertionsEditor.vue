<template>
  <section>
    <header class="flow-section-heading"><h4>节点断言</h4><button title="新增断言" aria-label="新增断言" type="button" @click="assertions.push({type: 'status', expected: 200})"><Plus :size="16" /></button></header>
    <div v-for="(assertion, index) in assertions" :key="index" class="flow-rule-row flow-assertion-row">
      <label>断言类型<select v-model="assertion.type"><option value="status">HTTP 状态码</option><option value="json_pointer">Body JSON Pointer</option><option value="json_equals">Body JSON 路径</option><option value="body_contains">响应包含</option><option value="response_time">响应耗时上限</option><option value="response_header">响应 Header</option></select></label>
      <label v-if="['json_pointer', 'json_equals'].includes(String(assertion.type))">路径<input v-model="assertion.path" placeholder="/code" /></label>
      <label>期望值<FlowValueInput v-model="assertion.expected" /></label>
      <button title="删除断言" aria-label="删除断言" type="button" @click="assertions.splice(index, 1)"><Trash2 :size="15" /></button>
    </div>
  </section>
</template>
<script setup lang="ts">
import { Plus, Trash2 } from 'lucide-vue-next'
import FlowValueInput from './FlowValueInput.vue'
const assertions = defineModel<Record<string, unknown>[]>({required: true})
</script>
