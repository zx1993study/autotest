<template>
  <div class="login-case-picker" :aria-busy="loading">
    <label v-if="kind === 'API'" class="field">
      <span>登录 API<b v-if="required">*</b></span>
      <ApiSelect v-model="selectedApi" :options="apiOptions" label="登录 API" :disabled="!project" :loading="loading" :required="required" @change="changeApi" />
    </label>
    <label class="field">
      <span>登录用例<b v-if="required || selectedApi">*</b></span>
      <select :value="caseId ? String(caseId) : ''" aria-label="登录用例" :disabled="!project || loading || (kind === 'API' && !selectedApi)" :required="required || Boolean(selectedApi)" @change="changeCase">
        <option value="">{{ !project ? '请选择项目' : loading ? '加载中...' : kind === 'API' && !selectedApi ? '请先选择 API' : caseOptions.length ? '请选择登录用例' : '暂无启用的正式用例' }}</option>
        <option v-for="item in caseOptions" :key="item.id" :value="String(item.id)">{{ item.name }} (#{{ item.id }})</option>
        <option v-if="caseId && !caseOptions.some(item => item.id === caseId)" :value="String(caseId)">用例 #{{ caseId }}（不可用）</option>
      </select>
    </label>
    <div v-if="error" class="picker-error" role="alert"><span>{{ error }}</span><button type="button" :disabled="loading" @click="retry">重试</button></div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { getResource, listRemoteOptions, listResources } from '../../services/resource.service'
import type { ResourceItem, SelectOptionRecord } from '../../types/resource'
import ApiSelect from '../common/ApiSelect.vue'

const props = withDefaults(defineProps<{
  modelValue: string | number | null
  projectId?: string | number | null
  caseType: string
  required?: boolean
}>(), { required: false })
const emit = defineEmits<{ 'update:modelValue': [value: number | null]; blocked: [value: boolean] }>()
const project = computed(() => positiveId(props.projectId))
const kind = computed(() => props.caseType.toUpperCase())
const caseId = computed(() => positiveId(props.modelValue))
const casePath = computed(() => kind.value === 'WEB' ? '/web-testing/cases' : '/api-testing/cases')
const selectedApi = ref(0)
const apiOptions = ref<SelectOptionRecord[]>([])
const caseOptions = ref<ResourceItem[]>([])
const loading = ref(false)
const error = ref('')
let requestId = 0
const blocked = computed(() => Boolean(
  loading.value || (caseId.value && !caseOptions.value.some(item => item.id === caseId.value)) ||
  (selectedApi.value && !caseId.value) || (props.required && (!project.value || !caseId.value))
))

watch(blocked, value => emit('blocked', value), { immediate: true })
watch([project, kind], (_current, previous) => { void initialize(Boolean(previous?.length)) }, { immediate: true })
onBeforeUnmount(() => { requestId += 1; emit('blocked', false) })

function positiveId(value: unknown) {
  const id = Number(value)
  return Number.isInteger(id) && id > 0 ? id : 0
}

async function initialize(clearSelection: boolean) {
  const sequence = ++requestId
  if (clearSelection) emit('update:modelValue', null)
  const savedId = clearSelection ? 0 : caseId.value
  selectedApi.value = 0
  apiOptions.value = []
  caseOptions.value = []
  error.value = ''
  loading.value = Boolean(project.value)
  if (!project.value) return
  try {
    if (!['API', 'WEB'].includes(kind.value)) throw new Error('该用例类型不支持登录鉴权')
    if (kind.value === 'API') {
      const options = await listRemoteOptions('/api-testing/interfaces/options', { project_id: project.value })
      if (sequence !== requestId) return
      apiOptions.value = options
      if (!savedId) return
      const saved = await getResource(casePath.value, savedId)
      if (sequence !== requestId) return
      if (positiveId(saved.project_id) !== project.value) throw new Error('登录用例不属于当前项目，请重新选择')
      const apiId = positiveId(saved.source_id)
      if (!apiId) throw new Error('登录用例没有关联 API，请重新选择')
      if (!options.some(option => option.id === apiId)) {
        const source = await getResource('/api-testing/interfaces', apiId)
        if (sequence !== requestId) return
        if (positiveId(source.project_id) !== project.value) throw new Error('登录 API 不属于当前项目')
        apiOptions.value = [...options, { id: source.id, name: source.name, method: String(source.data.method || ''), path: String(source.data.path || '') }]
      }
      selectedApi.value = apiId
    }
    const options = await fetchCases(sequence)
    if (sequence !== requestId || !options) return
    caseOptions.value = options
    if (savedId && !options.some(item => item.id === savedId)) throw new Error('原登录用例已删除或停用，请重新选择')
  } catch (cause) {
    if (sequence === requestId) error.value = cause instanceof Error ? cause.message : '登录用例加载失败'
  } finally {
    if (sequence === requestId) loading.value = false
  }
}

async function fetchCases(sequence: number) {
  const params = { project_id: project.value, source_id: kind.value === 'API' ? positiveId(selectedApi.value) : undefined, status: 'active', pageSize: 200 }
  const first = await listResources(casePath.value, { ...params, page: 1 })
  if (sequence !== requestId) return
  const rows = [...first.items]
  for (let page = 2; page <= Math.ceil(first.total / first.pageSize); page += 1) {
    const result = await listResources(casePath.value, { ...params, page })
    if (sequence !== requestId) return
    rows.push(...result.items)
  }
  return rows.filter(item => positiveId(item.project_id) === project.value && item.status === 'active' &&
    (kind.value !== 'API' || positiveId(item.source_id) === positiveId(selectedApi.value)))
}

async function changeApi() {
  const sequence = ++requestId
  emit('update:modelValue', null)
  caseOptions.value = []
  error.value = ''
  loading.value = Boolean(selectedApi.value)
  if (!selectedApi.value) return
  try {
    const options = await fetchCases(sequence)
    if (sequence === requestId && options) caseOptions.value = options
  } catch (cause) {
    if (sequence === requestId) error.value = cause instanceof Error ? cause.message : '登录用例加载失败'
  } finally {
    if (sequence === requestId) loading.value = false
  }
}

function changeCase(event: Event) {
  emit('update:modelValue', positiveId((event.target as HTMLSelectElement).value) || null)
}

function retry() {
  if (kind.value === 'API' && selectedApi.value && !caseId.value) void changeApi()
  else void initialize(false)
}
</script>

<style scoped>
.login-case-picker { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; min-width: 0; }
.login-case-picker .field { min-width: 0; }
.login-case-picker select { width: 100%; min-width: 0; }
.picker-error { grid-column: 1 / -1; display: flex; flex-wrap: wrap; align-items: center; gap: 8px; color: #b42318; font-size: 13px; }
@media (max-width: 600px) { .login-case-picker { grid-template-columns: minmax(0, 1fr); } }
</style>
