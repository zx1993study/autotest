<template>
  <div class="api-module-select">
    <div class="select-row">
      <select :value="modelValue ?? ''" :disabled="loading || busy || !projectId" aria-label="所属模块" @change="selectModule">
        <option value="">{{ loading ? '加载中...' : '请选择 API 模块' }}</option>
        <option v-for="module in modules" :key="module.id" :value="module.id">{{ module.name }}</option>
      </select>
      <button type="button" :disabled="busy || !projectId" title="新增模块" aria-label="新增模块" @click="begin('create')"><Plus :size="16" /></button>
      <button type="button" :disabled="busy || loading || !editable" title="编辑所选模块" aria-label="编辑模块" @click="begin('edit')"><Pencil :size="16" /></button>
      <button type="button" :disabled="busy || loading || !editable" title="删除所选模块" aria-label="删除模块" @click="begin('delete')"><Trash2 :size="16" /></button>
    </div>
    <section v-if="mode" class="module-editor" :aria-label="mode === 'delete' ? '确认删除模块' : '模块信息'">
      <template v-if="mode !== 'delete'">
        <label><span>模块名称</span><input v-model.trim="name" :disabled="busy" maxlength="128" autofocus @keydown.enter.stop.prevent="save" @keydown.esc.stop.prevent="cancel" /></label>
        <label><span>模块说明</span><textarea v-model.trim="description" :disabled="busy" maxlength="2000" rows="2" /></label>
      </template>
      <p v-else>确认删除模块“{{ selected?.name }}”？</p>
      <div class="editor-actions">
        <button type="button" :disabled="busy" @click="cancel">取消</button>
        <button type="button" :disabled="busy || (mode !== 'delete' && !name)" :class="{ danger: mode === 'delete' }" @click="save">{{ busy ? '处理中...' : mode === 'delete' ? '确认删除' : '保存模块' }}</button>
      </div>
    </section>
    <p v-if="error" class="form-error" role="alert">{{ error }}</p>
    <p v-else-if="message" class="module-message" role="status">{{ message }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { Pencil, Plus, Trash2 } from 'lucide-vue-next'
import { clearRemoteOptionsCache } from '../../services/resource.service'
import { createApiModule, deleteApiModule, getApiModule, listApiModuleOptions, updateApiModule } from '../../services/api-interface.service'
import type { ApiModuleChange, ApiModuleOption } from '../../types/api-interface'

const props = defineProps<{ projectId: number; modelValue: string | number | null }>()
const emit = defineEmits<{ 'update:modelValue': [value: number | string]; changed: [change: ApiModuleChange]; busy: [value: boolean] }>()
const modules = ref<ApiModuleOption[]>([])
const loading = ref(false)
const busy = ref(false)
const mode = ref<'create' | 'edit' | 'delete' | ''>('')
const name = ref('')
const description = ref('')
const error = ref('')
const message = ref('')
const selected = computed(() => modules.value.find(module => module.id === Number(props.modelValue)))
const editable = computed(() => selected.value && selected.value.key !== '__ungrouped__')
let sequence = 0

watch(() => props.projectId, (next, previous) => {
  mode.value = ''
  message.value = ''
  if (previous !== undefined && next !== previous) emit('update:modelValue', '')
  void load()
}, { immediate: true })
watch(busy, value => emit('busy', value), { flush: 'sync' })
onBeforeUnmount(() => { sequence += 1; emit('busy', false) })

async function load() {
  const request = ++sequence
  const projectId = props.projectId
  modules.value = []
  error.value = ''
  loading.value = true
  try {
    const rows = projectId ? await listApiModuleOptions(projectId) : []
    if (request !== sequence) return
    modules.value = rows
    if (props.modelValue && !rows.some(row => row.id === Number(props.modelValue))) emit('update:modelValue', '')
  } catch (cause) {
    if (request === sequence) error.value = errorText(cause)
  } finally {
    if (request === sequence) loading.value = false
  }
}

function selectModule(event: Event) {
  cancel()
  const value = (event.target as HTMLSelectElement).value
  emit('update:modelValue', value ? Number(value) : '')
}

async function begin(next: 'create' | 'edit' | 'delete') {
  error.value = ''
  message.value = ''
  name.value = next === 'create' ? '' : selected.value?.name || ''
  description.value = ''
  mode.value = next
  if (next !== 'edit' || !selected.value) return
  const projectId = props.projectId
  const id = selected.value.id
  busy.value = true
  try {
    const module = await getApiModule(projectId, id)
    if (projectId === props.projectId && mode.value === 'edit') description.value = module.description || ''
  } catch (cause) { error.value = errorText(cause); mode.value = '' }
  finally { busy.value = false }
}

function cancel() {
  if (busy.value) return
  mode.value = ''
  error.value = ''
  message.value = ''
}

async function save() {
  if (busy.value || !mode.value || !props.projectId) return
  const projectId = props.projectId
  const id = selected.value?.id
  const action = mode.value
  if (action !== 'create' && !id) return
  if (action !== 'delete' && !name.value.trim()) { error.value = '请输入模块名称'; return }
  busy.value = true
  error.value = ''
  try {
    const payload = { project_id: projectId, name: name.value.trim(), description: description.value || null }
    const result = action === 'delete' ? await deleteApiModule(projectId, id!) : action === 'edit' ? await updateApiModule(id!, payload) : await createApiModule(payload)
    clearRemoteOptionsCache('/api-testing/interfaces/modules/options')
    if (projectId !== props.projectId) return
    const change = action === 'delete' ? { id: id!, name: selected.value?.name || '', deleted: true } : { id: (result as { id: number }).id, name: payload.name, deleted: false }
    emit('update:modelValue', change.deleted ? '' : change.id)
    emit('changed', change)
    mode.value = ''
    await load()
    message.value = action === 'delete' ? '模块已删除' : '模块已保存'
  } catch (cause) { if (projectId === props.projectId) error.value = errorText(cause) }
  finally { busy.value = false }
}

function errorText(cause: unknown) { return cause instanceof Error ? cause.message : '模块操作失败，请重试' }
</script>

<style scoped>
.api-module-select{min-width:0}.select-row{display:flex;align-items:center;gap:6px}.select-row select{flex:1;min-width:0}.select-row button{width:32px;height:36px;flex:0 0 32px;padding:0;display:grid;place-items:center}.module-editor{margin-top:10px;padding-top:10px;border-top:1px solid #dce3ea}.module-editor label{display:grid;gap:5px;margin-bottom:10px}.module-editor label span{font-size:12px}.module-editor input,.module-editor textarea{width:100%;min-width:0}.module-editor p{overflow-wrap:anywhere}.editor-actions{display:flex;justify-content:flex-end;gap:8px}.module-message{margin:6px 0 0;color:#087e8b;font-size:12px}@media(max-width:480px){.select-row{gap:4px}.select-row button{width:28px;flex-basis:28px}}
</style>
