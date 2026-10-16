<template>
  <section>
    <label>名称<input :value="modelValue.name" @input="setName(($event.target as HTMLInputElement).value)" /></label>
    <nav aria-label="候选内容"><button v-for="item in tabs" :key="item.key" type="button" :class="{ active: tab === item.key }" @click="switchTab(item.key)">{{ item.label }}</button></nav>
    <textarea v-model="text" rows="16" spellcheck="false" :aria-label="tab" @input="apply" />
    <p v-if="error" role="alert">{{ error }}</p>
  </section>
</template>
<script setup lang="ts">
import { ref, watch } from 'vue'
const props = defineProps<{ modelValue: Record<string, any>; domain: string }>()
const emit = defineEmits<{ 'update:modelValue': [Record<string, any>]; valid: [boolean] }>()
const tabs = props.domain === 'API' ? [{ key: 'body', label: '请求体' }, { key: 'query', label: '查询参数' }, { key: 'input_info', label: '输入信息' }, { key: 'assertions', label: '断言' }] : [{ key: 'steps', label: '操作步骤' }, { key: 'input_info', label: '输入信息' }, { key: 'assertions', label: '断言' }]
const tab = ref(tabs[0].key)
const text = ref('')
const error = ref('')
function refresh() { text.value = JSON.stringify(props.modelValue[tab.value] ?? (['steps', 'assertions'].includes(tab.value) ? [] : {}), null, 2) }
watch(() => props.modelValue, refresh, { immediate: true })
function switchTab(key: string) { if (error.value) return; tab.value = key; refresh() }
function setName(name: string) { emit('update:modelValue', { ...props.modelValue, name }) }
function apply() {
  try {
    const value = JSON.parse(text.value)
    if (['steps', 'assertions'].includes(tab.value) ? !Array.isArray(value) : !value || Array.isArray(value) || typeof value !== 'object') throw new Error('内容类型不正确')
    error.value = ''
    emit('update:modelValue', { ...props.modelValue, [tab.value]: value })
    emit('valid', true)
  } catch { error.value = '请输入有效的 JSON'; emit('valid', false) }
}
</script>
<style scoped>
label { display: grid; gap: 6px; } nav { display: flex; gap: 6px; margin: 14px 0 10px; flex-wrap: wrap; } nav button { border: 0; border-radius: 0; } .active { color: #0f6b7a; border-bottom: 2px solid #0f6b7a; } textarea { width: 100%; font-family: monospace; resize: vertical; } p { color: #b42318; }
</style>
