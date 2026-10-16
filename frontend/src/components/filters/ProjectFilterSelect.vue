<template>
  <select
    v-model.number="localValue"
    class="project-filter-select"
    :aria-label="ariaLabel"
    :disabled="loading"
    @change="emitValue"
  >
    <option v-if="includeAll" :value="0">{{ allLabel }}</option>
    <option v-for="project in projects" :key="project.id" :value="project.id">
      {{ project.is_default ? `${project.name}（默认）` : project.name }}
    </option>
  </select>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'

import { listProjectOptions, resolveDefaultProjectId } from '../../services/project.service'
import type { ProjectOption } from '../../types/resource'

const props = withDefaults(defineProps<{
  modelValue: number
  includeAll?: boolean
  allLabel?: string
  ariaLabel?: string
  autoSelectDefault?: boolean
}>(), {
  includeAll: true,
  allLabel: '全部项目',
  ariaLabel: '按项目筛选',
  autoSelectDefault: true
})

const emit = defineEmits<{
  (event: 'update:modelValue', value: number): void
  (event: 'ready', value: number): void
}>()

const projects = ref<ProjectOption[]>([])
const loading = ref(false)
const localValue = ref(Number(props.modelValue || 0))

watch(() => props.modelValue, value => {
  localValue.value = Number(value || 0)
})

onMounted(loadProjects)

async function loadProjects() {
  loading.value = true
  try {
    projects.value = await listProjectOptions()
    const defaultProjectId = resolveDefaultProjectId(projects.value)
    if (props.autoSelectDefault && !props.modelValue && defaultProjectId) {
      localValue.value = defaultProjectId
      emitValue()
    }
  } finally {
    loading.value = false
    emit('ready', Number(localValue.value || 0))
  }
}

function emitValue() {
  emit('update:modelValue', Number(localValue.value || 0))
}
</script>

<style scoped>
.project-filter-select {
  flex: 0 0 180px;
  width: 180px;
  min-width: 148px;
  height: 34px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  color: #111827;
  padding: 0 10px;
}

.project-filter-select:disabled {
  background: #f8fafc;
  color: #94a3b8;
}

@media (max-width: 720px) {
  .project-filter-select {
    flex: 1 1 100%;
    width: 100%;
  }
}
</style>
