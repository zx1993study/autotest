<template>
  <div v-if="mode" class="modal-backdrop" @click.self="close" @keydown.esc.stop.prevent="close">
    <section class="modal-panel module-dialog" role="dialog" aria-modal="true" :aria-labelledby="titleId">
      <header class="modal-header">
        <h3 :id="titleId">{{ title }}</h3>
        <button type="button" class="modal-close" aria-label="关闭模块弹窗" :disabled="busy" @click="close"><X :size="18" /></button>
      </header>
      <form class="modal-form" @submit.prevent="save">
        <p v-if="mode === 'delete'" class="delete-confirmation">确认删除模块“{{ module?.name }}”？</p>
        <div v-else class="form-grid">
          <label class="field full"><span>模块名称<b aria-hidden="true">*</b></span><input v-model.trim="name" required maxlength="128" :disabled="busy" autofocus /></label>
          <label class="field full"><span>模块说明</span><textarea v-model.trim="description" rows="3" maxlength="2000" :disabled="busy" /></label>
        </div>
        <p v-if="error" class="form-error" role="alert">{{ error }}</p>
        <footer class="modal-actions">
          <button type="button" :disabled="busy" @click="close">取消</button>
          <button type="submit" :class="{ danger: mode === 'delete' }" :disabled="busy || (mode !== 'delete' && !name.trim())">{{ busy ? '处理中...' : mode === 'delete' ? '确认删除' : '保存模块' }}</button>
        </footer>
      </form>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, useId, watch } from 'vue'
import { X } from 'lucide-vue-next'
import { createApiModule, deleteApiModule, updateApiModule } from '../../services/api-interface.service'
import { clearRemoteOptionsCache } from '../../services/resource.service'
import type { ApiModuleChange, ApiModuleSummary } from '../../types/api-interface'

const props = defineProps<{ projectId: number; mode: 'create' | 'edit' | 'delete' | ''; module: ApiModuleSummary | null }>()
const emit = defineEmits<{ close: []; changed: [change: ApiModuleChange] }>()
const titleId = useId()
const title = computed(() => props.mode === 'create' ? '新增模块' : props.mode === 'edit' ? '编辑模块' : '删除模块')
const name = ref('')
const description = ref('')
const busy = ref(false)
const error = ref('')
watch(() => [props.mode, props.module?.id, props.projectId], () => {
  name.value = props.mode === 'create' ? '' : props.module?.name || ''
  description.value = props.mode === 'create' ? '' : props.module?.description || ''
  error.value = ''
}, { immediate: true })

function close() { if (!busy.value) emit('close') }

async function save() {
  if (busy.value || !props.mode || !props.projectId) return
  const mode = props.mode
  const projectId = props.projectId
  const id = props.module?.id
  if (mode !== 'create' && !id) return
  if (mode !== 'delete' && !name.value.trim()) { error.value = '请输入模块名称'; return }
  busy.value = true
  error.value = ''
  try {
    const payload = { project_id: projectId, name: name.value.trim(), description: description.value || null }
    const result = mode === 'delete' ? await deleteApiModule(projectId, id!) : mode === 'edit' ? await updateApiModule(id!, payload) : await createApiModule(payload)
    clearRemoteOptionsCache('/api-testing/interfaces/modules/options')
    if (props.projectId !== projectId || props.mode !== mode) return
    emit('changed', { id: mode === 'delete' ? id! : (result as { id: number }).id, name: mode === 'delete' ? props.module?.name || '' : payload.name, deleted: mode === 'delete' })
    emit('close')
  } catch (cause) { error.value = cause instanceof Error ? cause.message : '模块操作失败，请重试' }
  finally { busy.value = false }
}
</script>

<style scoped>
.modal-backdrop { z-index: 70; }
.module-dialog { width: min(520px, calc(100vw - 24px)); max-height: calc(100dvh - 24px); align-self: center; }
.modal-close { display: grid; place-items: center; }
.delete-confirmation { margin: 0; overflow-wrap: anywhere; }
</style>
