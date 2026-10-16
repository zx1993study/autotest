<template>
  <div class="api-auth-select">
    <select :value="modelValue ?? ''" :disabled="loading || !projectId" aria-label="鉴权信息" @change="changeSelection">
      <option value="">{{ loading ? '加载中...' : projectId ? '不配置鉴权' : '请先选择项目' }}</option>
      <option v-for="option in options" :key="option.id" :value="option.id">{{ option.name }}</option>
    </select>
    <p v-if="error" class="form-error" role="alert">{{ error }}<button type="button" @click="load">重试</button></p>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
import { listApiAuthOptions } from '../../services/api-interface.service'
import type { ApiAuthOption } from '../../types/api-interface'

const props = defineProps<{ projectId: number; modelValue: string | number | null }>()
const emit = defineEmits<{ 'update:modelValue': [value: number | string]; busy: [value: boolean] }>()
const options = ref<ApiAuthOption[]>([])
const loading = ref(false)
const error = ref('')
let sequence = 0

watch(() => props.projectId, (next, previous) => {
  if (previous !== undefined && next !== previous) emit('update:modelValue', '')
  void load()
}, { immediate: true })
watch(loading, value => emit('busy', value), { flush: 'sync' })
onBeforeUnmount(() => { sequence += 1; emit('busy', false) })

async function load() {
  const request = ++sequence
  const projectId = props.projectId
  options.value = []
  error.value = ''
  loading.value = true
  try {
    const result = projectId ? await listApiAuthOptions(projectId) : []
    if (request !== sequence) return
    options.value = result
    if (props.modelValue && !result.some(option => option.id === Number(props.modelValue))) emit('update:modelValue', '')
  } catch (cause) {
    if (request === sequence) error.value = cause instanceof Error ? cause.message : '鉴权加载失败'
  } finally {
    if (request === sequence) loading.value = false
  }
}

function changeSelection(event: Event) {
  const value = (event.target as HTMLSelectElement).value
  emit('update:modelValue', value ? Number(value) : '')
}
</script>

<style scoped>
.api-auth-select { min-width: 0; }
.api-auth-select select { width: 100%; }
.form-error { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-bottom: 0; }
</style>
