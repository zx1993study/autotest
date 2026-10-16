<template>
  <div class="flow-parameters">
    <header class="flow-section-heading"><h4>{{ title }}</h4><button type="button" title="新增参数" aria-label="新增参数" @click="add"><Plus :size="16" /></button></header>
    <div v-for="(row, index) in rows" :key="index" class="flow-parameter-row">
      <input v-model="row.name" aria-label="参数名称" placeholder="参数名" @change="rename(index)" />
      <FlowValueInput v-model="row.value" @update:model-value="publish" />
      <button type="button" title="删除参数" aria-label="删除参数" @click="remove(index)"><Trash2 :size="15" /></button>
    </div>
    <p v-if="!rows.length" class="flow-empty-small">暂无参数</p>
    <p v-if="error" class="flow-error">{{ error }}</p>
  </div>
</template>
<script setup lang="ts">
import { ref, watch } from 'vue'
import { Plus, Trash2 } from 'lucide-vue-next'
import FlowValueInput from './FlowValueInput.vue'
const props = withDefaults(defineProps<{modelValue: Record<string, unknown>; title?: string}>(), {title: '输入参数'})
const emit = defineEmits<{(event: 'update:modelValue', value: Record<string, unknown>): void}>()
const rows = ref<{name: string; savedName: string; value: unknown}[]>([])
const error = ref('')
let published = ''
watch(() => props.modelValue, value => {
  if (JSON.stringify(value) === published) return
  rows.value = Object.entries(value).map(([name, item]) => ({name, savedName: name, value: item}))
}, { immediate: true, deep: true })
function publish() {
  const names = rows.value.map(row => row.name.trim()).filter(Boolean)
  if (new Set(names).size !== names.length) { error.value = '参数名称不能重复'; return }
  error.value = ''
  const value = Object.fromEntries(rows.value.filter(row => row.name.trim()).map(row => [row.name.trim(), row.value]))
  published = JSON.stringify(value)
  emit('update:modelValue', value)
}
function rename(index: number) {
  const row = rows.value[index]
  if (!row) return
  const name = row.name.trim()
  if (!name || rows.value.some((item, position) => position !== index && item.name.trim() === name)) {
    row.name = row.savedName
    error.value = '参数名为空或重复，已保留原名称'
    return
  }
  row.name = name; row.savedName = name; publish()
}
function add() {
  let index = rows.value.length + 1
  while (rows.value.some(row => row.name === `param_${index}`)) index++
  const name = `param_${index}`
  rows.value.push({name, savedName: name, value: ''}); publish()
}
function remove(index: number) { rows.value.splice(index, 1); publish() }
</script>
