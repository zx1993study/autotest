<template>
  <div class="parameter-editor">
    <div class="parameter-tools"><button type="button" @click="add"><Plus :size="15" />添加参数</button></div>
    <div class="table-wrap"><table><thead><tr><th>参数标识</th><th>字段名称</th><th>输入类型</th><th>必填</th><th>选项 / 默认值</th><th>操作</th></tr></thead>
      <tbody><template v-for="(p, index) in modelValue" :key="index"><tr>
        <td><input v-model="p.key" aria-label="参数标识" /></td><td><input v-model="p.label" aria-label="字段名称" /></td>
        <td><select v-model="p.type" aria-label="输入类型" @change="p.default_value = null"><option v-for="(label, type) in types" :key="type" :value="type">{{ label }}</option></select></td>
        <td><input v-model="p.required" type="checkbox" aria-label="必填" /></td>
        <td><span v-if="['manual','password'].includes(p.type)">{{ p.type === 'password' ? '按用例设置' : '执行时人工输入' }}</span><select v-else-if="p.type === 'boolean'" v-model="p.default_value" aria-label="默认值"><option :value="null">不设置</option><option :value="true">是</option><option :value="false">否</option></select><input v-else :value="displayValue(p.default_value)" aria-label="默认值" @input="setDefault($event, p)" /></td>
        <td><div class="row-actions"><button type="button" :title="expanded === index ? '收起配置' : '更多配置'" aria-label="更多配置" @click="expanded = expanded === index ? -1 : index"><Settings2 :size="15" /></button><button type="button" title="删除参数" aria-label="删除参数" @click="remove(index)"><Trash2 :size="15" /></button></div></td>
      </tr><tr v-if="expanded === index"><td colspan="6"><div class="details-grid">
        <label v-if="p.type === 'select' || p.type === 'multiselect'">选项<textarea :value="JSON.stringify(p.options)" rows="3" @input="parse($event, p, 'options')" /></label>
        <label>显示条件<textarea :value="JSON.stringify(p.condition)" rows="3" @input="parse($event, p, 'condition')" /></label>
        <label>校验规则<textarea :value="JSON.stringify(p.validation)" rows="3" @input="parse($event, p, 'validation')" /></label>
        <label>定位方式<select v-model="p.locator_type"><option v-for="type in locators" :key="type">{{ type }}</option></select></label><label>定位内容<input v-model="p.locator" /></label>
        <label class="check"><input v-model="p.confirmed" type="checkbox" />规则已确认</label>
      </div></td></tr></template><tr v-if="!modelValue.length"><td colspan="6" class="empty">暂无输入参数</td></tr></tbody>
    </table></div><p v-for="(error, key) in errors" :key="key" class="error" role="alert">{{ error }}</p>
  </div>
</template>
<script setup lang="ts">
import { ref, watch } from 'vue'
import { Plus, Settings2, Trash2 } from 'lucide-vue-next'
import type { WebParameter } from '../../types/web-feature'
const props = defineProps<{ modelValue: WebParameter[] }>()
const emit = defineEmits<{ 'update:modelValue': [value: WebParameter[]]; valid: [value: boolean] }>()
const expanded = ref(-1), errors = ref<Record<string,string>>({})
watch(() => props.modelValue, () => { errors.value = {}; emit('valid', true) })
const types = { text: '文本', password:'密码', textarea: '多行文本', number: '数字', select: '下拉框', multiselect: '多选框', date: '日期', datetime: '日期时间', boolean: '开关', json: '结构化数据', manual: '人工输入' }
const locators = ['label', 'role', 'testid', 'placeholder', 'text', 'css', 'xpath']
function add() { let index = props.modelValue.length + 1; while (props.modelValue.some(p => p.key === `field_${index}`)) ++index; emit('update:modelValue', [...props.modelValue, { key: `field_${index}`, label: '', type: 'text', required: false, options: [], condition: {}, validation: {}, locator_type: 'label', locator: '', confirmed: false }]) }
function remove(index: number) { expanded.value = -1; emit('update:modelValue', props.modelValue.filter((_, i) => i !== index)) }
function displayValue(value: any) { return value == null ? '' : typeof value === 'object' ? JSON.stringify(value) : String(value) }
function mark(parameter: WebParameter, field: string, message = '') {
  const key = `${props.modelValue.indexOf(parameter)}:${field}`
  if (message) errors.value[key] = message; else delete errors.value[key]
  emit('valid', !Object.keys(errors.value).length)
}
function setDefault(event: Event, parameter: WebParameter) {
  const raw = (event.target as HTMLInputElement).value
  try {
    let value: any = raw === '' ? null : raw
    if (raw && parameter.type === 'number' && !raw.includes('{{')) {
      value = Number(raw); if (!Number.isFinite(value)) throw new Error('默认值必须为数字')
    }
    if (raw && ['json','multiselect'].includes(parameter.type)) {
      value = JSON.parse(raw); if (parameter.type === 'multiselect' && !Array.isArray(value)) throw new Error('多选默认值须为 JSON 数组')
    }
    parameter.default_value = value; mark(parameter, 'default')
  } catch { mark(parameter, 'default', `${parameter.label || parameter.key} 默认值格式无效`) }
}
function parse(event: Event, parameter: WebParameter, field: 'options' | 'condition' | 'validation') {
  try { const value = JSON.parse((event.target as HTMLTextAreaElement).value); if ((field === 'options') !== Array.isArray(value) || value == null || typeof value !== 'object') throw new Error(); parameter[field] = value; mark(parameter, field) }
  catch { mark(parameter, field, `${parameter.label || parameter.key}：选项须为 JSON 数组，显示条件和校验规则须为 JSON 对象`) }
}
</script>
<style scoped>
.parameter-tools { display:flex; justify-content:flex-end; margin-bottom:10px; } button { display:inline-flex; align-items:center; gap:6px; } table { table-layout:fixed; min-width:680px; } th:nth-child(1) { width:125px; } th:nth-child(3) { width:115px; } th:nth-child(4) { width:55px; } th:last-child { width:85px; } input,select,textarea { width:100%; min-width:0; } input[type=checkbox] { width:16px; } .details-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; } label { display:grid; gap:6px; } label.check { display:flex; align-items:center; } .error { color:#b42318; } .empty { text-align:center; padding:25px; color:#667085; } @media(max-width:600px) { .details-grid { grid-template-columns:1fr; } }
</style>
