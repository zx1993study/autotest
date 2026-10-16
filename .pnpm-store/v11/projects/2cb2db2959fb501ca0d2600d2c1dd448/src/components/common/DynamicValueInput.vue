<template>
  <div class="dynamic-value-input">
    <div class="value-row">
      <input :value="textValue" :type="type || 'text'" :aria-label="label" :placeholder="placeholder" @input="setValue(($event.target as HTMLInputElement).value)" />
      <button v-if="mode !== 'fixed'" type="button" class="preview-button" :disabled="loading" :aria-label="`${label}预览动态值`" title="预览动态值" @click="preview">↻</button>
    </div>
    <div class="rule-row">
      <select :value="mode" :aria-label="`${label}生成方式`" @change="changeMode(($event.target as HTMLSelectElement).value)">
        <option value="fixed">固定值</option>
        <option value="timestamp_ms">追加毫秒时间戳</option>
        <option value="timestamp">追加秒时间戳</option>
        <option value="datetime">追加日期时间</option>
        <option value="phone">随机手机号</option>
        <option value="custom">自定义模板</option>
      </select>
      <template v-if="isTimestamp">
        <label class="separator-field"><span>分隔符</span><input :value="separator" :aria-label="`${label}时间戳分隔符`" maxlength="8" @input="changeSeparator(($event.target as HTMLInputElement).value)" /></label>
      </template>
      <label v-if="mode === 'phone'" class="prefix-field"><span>号段</span><input :value="phonePrefix" inputmode="numeric" maxlength="3" :aria-label="`${label}手机号号段`" @input="setValue(`{{random_phone:${($event.target as HTMLInputElement).value}}}`)" /></label>
    </div>
    <output v-if="previewValue !== ''" :aria-label="`${label}动态值预览`" class="preview-value">{{ previewValue }}</output>
    <p v-if="error" class="dynamic-error" role="alert">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { previewDynamicValue } from '../../services/dynamic-value.service'

const props = withDefaults(defineProps<{ modelValue: string | number | null | undefined; label?: string; placeholder?: string; type?: string; variables?: Record<string, unknown> }>(), { label: '输入值', variables: () => ({}) })
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
const loading = ref(false)
const previewValue = ref('')
const error = ref('')
const separator = ref('_')
const customMode = ref(false)
const textValue = computed(() => String(props.modelValue ?? ''))
const timeMatch = computed(() => textValue.value.match(/^(.*?)\{\{\s*(timestamp_ms|timestamp|datetime)\s*\}\}$/))
const phoneMatch = computed(() => textValue.value.match(/^\{\{\s*random_phone(?::([^{}]*))?\s*\}\}$/))
const phonePrefix = computed(() => phoneMatch.value?.[1]?.trim() ?? '138')
const mode = computed(() => customMode.value ? 'custom' : timeMatch.value?.[2] || (phoneMatch.value ? 'phone' : textValue.value.includes('{{') ? 'custom' : 'fixed'))
const isTimestamp = computed(() => ['timestamp', 'timestamp_ms', 'datetime'].includes(mode.value))

watch(() => props.modelValue, () => { previewValue.value = ''; error.value = '' })
watch(timeMatch, (match, previous) => {
  if (!match) return
  if (previous && match[1].endsWith(separator.value)) return
  const trailing = match[1].match(/[_\-.: /]+$/)?.[0]
  separator.value = trailing || ''
}, { immediate: true })

function setValue(value: string) { emit('update:modelValue', value) }

function baseValue() {
  if (timeMatch.value) {
    const base = timeMatch.value[1]
    return separator.value && base.endsWith(separator.value) ? base.slice(0, -separator.value.length) : base
  }
  return phoneMatch.value ? '' : textValue.value
}

function changeMode(next: string) {
  const base = baseValue()
  customMode.value = next === 'custom'
  if (next === 'phone') setValue('{{random_phone:138}}')
  else if (['timestamp', 'timestamp_ms', 'datetime'].includes(next)) setValue(`${base}${base ? separator.value : ''}{{${next}}}`)
  else if (next === 'fixed') setValue(base)
  else if (!textValue.value.includes('{{')) setValue(`${textValue.value}{{timestamp_ms}}`)
}

function changeSeparator(value: string) {
  const base = baseValue()
  separator.value = value
  setValue(`${base}${base ? value : ''}{{${mode.value}}}`)
}

async function preview() {
  if (loading.value) return
  loading.value = true
  error.value = ''
  const template = textValue.value
  try {
    const result = await previewDynamicValue(template, props.variables)
    if (template === textValue.value) previewValue.value = typeof result.resolved === 'object' ? JSON.stringify(result.resolved) : String(result.resolved ?? '')
  } catch (cause) {
    if (template === textValue.value) error.value = cause instanceof Error ? cause.message : '预览失败'
  } finally { loading.value = false }
}
</script>

<style scoped>
.dynamic-value-input { display: grid; gap: 6px; min-width: 0; }
.value-row, .rule-row { display: flex; align-items: center; gap: 6px; min-width: 0; }
.value-row input { width: 100%; min-width: 0; flex: 1; }
.preview-button { flex: 0 0 34px; width: 34px; height: 34px; padding: 0; }
.rule-row { flex-wrap: wrap; }
.rule-row select { width: 158px; min-width: 0; height: 30px; padding: 0 6px; font-size: 12px; }
.separator-field, .prefix-field { display: flex; align-items: center; gap: 5px; color: #68758a; font-size: 12px; }
.separator-field input, .prefix-field input { width: 60px; min-width: 0; height: 30px; padding: 0 6px; }
.preview-value { color: #166534; font-size: 12px; overflow-wrap: anywhere; }
.dynamic-error { margin: 0; color: #b42318; font-size: 12px; overflow-wrap: anywhere; }
</style>
