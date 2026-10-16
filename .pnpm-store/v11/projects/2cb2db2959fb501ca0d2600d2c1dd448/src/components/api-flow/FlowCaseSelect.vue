<template>
  <div>
    <select :value="modelValue ?? ''" :disabled="loading || !apiId" :aria-label="label" @change="emit('update:modelValue', Number(($event.target as HTMLSelectElement).value) || null)">
      <option value="">{{ inheritLabel || '选择节点用例' }}</option>
      <option v-for="item in cases" :key="item.id" :value="item.id">{{ item.name }}</option>
    </select>
    <p v-if="error" class="flow-error">{{ error }}</p>
  </div>
</template>
<script setup lang="ts">
import { ref, watch } from 'vue'
import { listResources } from '../../services/resource.service'
import type { ResourceItem } from '../../types/resource'
const props = withDefaults(defineProps<{modelValue: number | null; apiId: number; projectId: number; inheritLabel?: string; label?: string}>(), {label: '节点用例'})
const emit = defineEmits<{(event: 'update:modelValue', value: number | null): void}>()
const cases = ref<ResourceItem[]>([])
const loading = ref(false)
const error = ref('')
let generation = 0
watch(() => [props.apiId, props.projectId], async () => {
  const current = ++generation
  cases.value = []; error.value = ''
  if (!props.apiId) return
  loading.value = true
  try {
    const rows: ResourceItem[] = []
    for (let page = 1; page <= 50; page++) {
      const result = await listResources('/api-testing/cases', {project_id: props.projectId, source_id: props.apiId, status: 'active', page, pageSize: 200})
      rows.push(...result.items)
      if (rows.length >= result.total || !result.items.length) break
    }
    if (current === generation) cases.value = rows
  } catch (err) { if (current === generation) error.value = err instanceof Error ? err.message : '用例加载失败' }
  finally { if (current === generation) loading.value = false }
}, {immediate: true})
</script>
