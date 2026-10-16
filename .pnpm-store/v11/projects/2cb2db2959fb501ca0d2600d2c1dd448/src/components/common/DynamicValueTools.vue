<template>
  <div v-if="entries.length" class="dynamic-value-tools">
    <select v-model="selectedPath" :aria-label="`${label}动态字段`">
      <option v-for="entry in entries" :key="entry.id" :value="entry.id">{{ entry.label }}</option>
    </select>
    <DynamicValueInput :key="selectedPath" :model-value="selectedValue" :label="`${label}字段值`" :variables="variables" @update:model-value="updateValue" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import DynamicValueInput from './DynamicValueInput.vue'

const props = withDefaults(defineProps<{ modelValue: string; label?: string; variables?: Record<string, unknown> }>(), { label: '参数', variables: () => ({}) })
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
const selectedPath = ref('')
const parsed = computed<unknown>(() => { try { return JSON.parse(props.modelValue) } catch { return null } })
const entries = computed(() => {
  const result: Array<{ id: string; path: Array<string | number>; label: string; value: string | number }> = []
  function walk(value: unknown, path: Array<string | number>, depth = 0) {
    if (depth > 30 || result.length >= 200) return
    if (Array.isArray(value)) value.forEach((item, index) => walk(item, [...path, index], depth + 1))
    else if (value && typeof value === 'object') Object.entries(value).forEach(([key, item]) => walk(item, [...path, key], depth + 1))
    else if ((typeof value === 'string' || typeof value === 'number') && path.length) result.push({ id: JSON.stringify(path), path, label: path.map(String).join(' / '), value })
  }
  walk(parsed.value, [])
  return result
})
const selectedEntry = computed(() => entries.value.find(entry => entry.id === selectedPath.value))
const selectedValue = computed(() => selectedEntry.value?.value ?? '')
watch(entries, next => { if (!next.some(entry => entry.id === selectedPath.value)) selectedPath.value = next[0]?.id || '' }, { immediate: true })

function updateValue(value: string) {
  const path = selectedEntry.value?.path
  if (!path || !parsed.value) return
  const root = JSON.parse(props.modelValue)
  let target = root
  for (const part of path.slice(0, -1)) target = target[part]
  const key = path[path.length - 1]
  const previous = target[key]
  target[key] = typeof previous === 'number' && value.trim() && Number.isFinite(Number(value)) ? Number(value) : value
  emit('update:modelValue', JSON.stringify(root, null, 2))
}
</script>

<style scoped>
.dynamic-value-tools { display: grid; grid-template-columns: minmax(120px, 0.7fr) minmax(0, 1fr); align-items: start; gap: 10px; min-width: 0; padding-top: 8px; }
.dynamic-value-tools > select { width: 100%; min-width: 0; height: 38px; }
@media (max-width: 600px) { .dynamic-value-tools { grid-template-columns: minmax(0, 1fr); } }
</style>
