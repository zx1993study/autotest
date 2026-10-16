<template>
  <div class="input-grid"><label v-for="p in visibleParameters" :key="p.key" :class="{ wide: ['textarea','json'].includes(p.type) }"><span>{{ p.label }}<b v-if="p.required"> *</b><small>{{ p.key }}</small></span>
    <select v-if="p.type === 'select' || p.type === 'multiselect'" :multiple="p.type === 'multiselect'" :value="modelValue[p.key]" :aria-label="p.label" @change="select($event, p)"><option v-if="p.type === 'select'" value="">请选择</option><option v-for="(option, index) in p.options" :key="index" :value="optionValue(option)">{{ optionLabel(option) }}</option></select>
    <input v-else-if="p.type === 'boolean'" type="checkbox" :checked="modelValue[p.key] === true" :aria-label="p.label" @change="set(p.key, ($event.target as HTMLInputElement).checked)" />
    <textarea v-else-if="p.type === 'textarea' || p.type === 'json'" :value="p.type === 'json' ? JSON.stringify(modelValue[p.key] ?? {}, null, 2) : modelValue[p.key]" rows="3" :aria-label="p.label" @input="text($event, p)" />
    <input v-else-if="p.type === 'manual'" disabled value="执行到此步骤时人工填写" :aria-label="p.label" />
    <div v-else-if="p.type === 'password'" class="password-input"><input type="password" autocomplete="new-password" :value="modelValue[p.key]" :placeholder="secretKeys?.includes(p.key) ? '已保存，未修改则保留' : '输入用例密码'" :aria-label="p.label" @input="text($event, p)" /><button type="button" title="设为空密码" aria-label="设为空密码" @click="set(p.key,'')"><Eraser :size="16" /></button></div>
    <input v-else :type="p.type === 'date' ? 'date' : p.type === 'datetime' ? 'datetime-local' : p.type === 'number' ? 'number' : 'text'" :value="modelValue[p.key]" :aria-label="p.label" @input="text($event, p)" />
  </label><p v-if="!parameters.length" class="empty">此功能暂无定义的输入参数</p><p v-for="(error, key) in errors" :key="key" class="error" role="alert">{{ error }}</p></div>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import type { WebParameter } from '../../types/web-feature'
import { Eraser } from 'lucide-vue-next'
const props = defineProps<{ parameters: WebParameter[]; modelValue: Record<string, any>; secretKeys?: string[] }>()
const emit = defineEmits<{ 'update:modelValue': [value: Record<string,any>]; valid: [value: boolean] }>()
const errors = ref<Record<string,string>>({})
const visibleParameters = computed(() => props.parameters.filter(p => !p.condition?.key || props.modelValue[p.condition.key] === p.condition.equals))
const optionValue = (option: any) => typeof option === 'object' && option !== null ? option.value : option
const optionLabel = (option: any) => typeof option === 'object' && option !== null ? option.label ?? option.value : option
function set(key: string, value: any) { emit('update:modelValue', { ...props.modelValue, [key]: value }); delete errors.value[key]; emit('valid', !Object.keys(errors.value).length) }
function text(event: Event, p: WebParameter) { const value = (event.target as HTMLInputElement).value; try { set(p.key, p.type === 'json' ? JSON.parse(value) : p.type === 'number' ? value === '' ? null : Number(value) : value) } catch { errors.value[p.key] = `${p.label} 必须为有效 JSON`; emit('valid', false) } }
function select(event: Event, p: WebParameter) { const control = event.target as HTMLSelectElement; const selected = [...control.selectedOptions].map(o => p.options.map(optionValue).find(v => String(v) === o.value) ?? o.value); set(p.key, p.type === 'multiselect' ? selected : selected[0]) }
</script>
<style scoped>
.input-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:16px; } label { display:grid; gap:7px; align-content:start; min-width:0; } .wide { grid-column:1 / -1; } label span { overflow-wrap:anywhere; } small { display:block; color:#667085; margin-top:3px; } b { color:#b42318; } input,textarea,select { width:100%; min-width:0; } input[type=checkbox] { width:18px; height:18px; } .error { color:#b42318; grid-column:1 / -1; } .empty { color:#667085; } @media(max-width:600px) { .input-grid { grid-template-columns:1fr; } }
.password-input { display:grid; grid-template-columns:minmax(0,1fr) 36px; gap:6px; } .password-input button { padding:6px; display:grid; place-items:center; }
</style>
