<template>
  <details v-if="Object.keys(values).length" class="dynamic-value-evidence">
    <summary>本次动态输入值</summary>
    <dl><div v-for="(value, name) in values" :key="name"><dt>{{ name }}</dt><dd>{{ typeof value === 'object' ? JSON.stringify(value) : value }}</dd></div></dl>
    <details v-if="Object.keys(templates).length"><summary>原始模板</summary><pre>{{ JSON.stringify(templates, null, 2) }}</pre></details>
  </details>
</template>

<script setup lang="ts">
import { computed } from 'vue'
const props = defineProps<{ snapshot: unknown }>()
const record = computed(() => isRecord(props.snapshot) ? props.snapshot : {})
const values = computed(() => isRecord(record.value.values) ? record.value.values : {})
const templates = computed(() => isRecord(record.value.templates) ? record.value.templates : {})
function isRecord(value: unknown): value is Record<string, unknown> { return Boolean(value) && typeof value === 'object' && !Array.isArray(value) }
</script>

<style scoped>
.dynamic-value-evidence { margin: 12px 0; min-width: 0; }
summary { cursor: pointer; font-size: 13px; font-weight: 600; }
dl { margin: 8px 0; }
dl > div { display: grid; grid-template-columns: minmax(90px, 1fr) minmax(0, 3fr); gap: 12px; padding: 6px 0; border-bottom: 1px solid #e5e7eb; }
dt, dd { margin: 0; font-size: 13px; overflow-wrap: anywhere; }
dt { color: #68758a; }
pre { white-space: pre-wrap; overflow-wrap: anywhere; font-size: 12px; }
</style>
