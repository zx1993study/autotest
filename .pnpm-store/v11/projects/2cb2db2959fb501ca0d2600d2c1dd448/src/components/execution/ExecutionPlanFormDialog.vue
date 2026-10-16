<template>
  <div v-if="open" class="modal-backdrop" @click.self="emit('close')">
    <section class="modal-panel" role="dialog" aria-modal="true">
      <header class="modal-header">
        <h3>{{ plan ? '编辑执行计划' : '新增执行计划' }}</h3>
        <button type="button" class="modal-close" aria-label="关闭" @click="emit('close')">×</button>
      </header>

      <form class="plan-form" @submit.prevent="submit">
        <label class="form-field full-field">
          <span>执行计划名称<b>*</b></span>
          <input v-model.trim="form.name" maxlength="128" placeholder="请输入执行计划名称" />
        </label>
        <div class="form-field">
          <span>API</span>
          <ExecutionPlanSourceSelect
            v-model="form.api_ids"
            :project-id="projectId"
            source-type="API"
          />
        </div>
        <div class="form-field">
          <span>Web 功能</span>
          <ExecutionPlanSourceSelect
            v-model="form.web_feature_ids"
            :project-id="projectId"
            source-type="WEB"
          />
        </div>
        <label class="form-field full-field">
          <span>备注</span>
          <textarea v-model.trim="form.description" maxlength="2000" rows="4" placeholder="请输入备注"></textarea>
        </label>
        <p v-if="localError || error" class="form-error">{{ localError || error }}</p>
        <footer class="modal-actions">
          <button type="button" @click="emit('close')">取消</button>
          <button type="submit" class="primary" :disabled="saving">
            {{ saving ? '保存中...' : '保存' }}
          </button>
        </footer>
      </form>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

import type { ExecutionPlanInfo, ExecutionPlanSavePayload } from '../../types/execution-plan'
import ExecutionPlanSourceSelect from './ExecutionPlanSourceSelect.vue'

const props = defineProps<{
  open: boolean
  plan: ExecutionPlanInfo | null
  projectId: number
  saving: boolean
  error: string
}>()

const emit = defineEmits<{
  close: []
  save: [payload: ExecutionPlanSavePayload]
}>()

const localError = ref('')
const form = ref<ExecutionPlanSavePayload>(emptyForm())

watch(
  () => props.open,
  open => {
    if (!open) return
    form.value = props.plan
      ? {
          name: props.plan.name,
          project_id: props.projectId,
          api_ids: [...props.plan.api_ids],
          web_feature_ids: [...props.plan.web_feature_ids],
          description: props.plan.description || ''
        }
      : emptyForm()
    localError.value = ''
  }
)

function submit() {
  localError.value = ''
  if (!form.value.name) {
    localError.value = '请输入执行计划名称'
    return
  }
  if (!form.value.api_ids.length && !form.value.web_feature_ids.length) {
    localError.value = '请至少选择一个 API 或 Web 功能'
    return
  }
  emit('save', {
    ...form.value,
    api_ids: form.value.api_ids.map(Number),
    web_feature_ids: form.value.web_feature_ids.map(Number),
    description: form.value.description || null
  })
}

function emptyForm(): ExecutionPlanSavePayload {
  return {
    name: '',
    project_id: props.projectId,
    api_ids: [],
    web_feature_ids: [],
    description: ''
  }
}

</script>

<style scoped>
.modal-panel {
  display: flex;
  flex-direction: column;
  width: min(760px, calc(100vw - 32px));
  height: min(560px, calc(100vh - 32px));
  max-height: none;
  overflow: hidden;
}

.plan-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-content: start;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  gap: 16px;
  padding: 20px 22px;
}

.form-field {
  display: flex;
  flex-direction: column;
  min-width: 0;
  gap: 7px;
}

.full-field,
.form-error,
.modal-actions {
  grid-column: 1 / -1;
}

.plan-form input,
.plan-form textarea {
  border: 1px solid #cad4e2;
  border-radius: 6px;
  color: #1f2937;
  padding: 9px 10px;
}

.plan-form input {
  min-height: 38px;
}

.plan-form b,
.form-error {
  color: #dc2626;
}

.modal-actions {
  position: sticky;
  bottom: 0;
  z-index: 5;
  margin: 2px -22px -20px;
  border-top: 1px solid #edf1f7;
  background: #ffffff;
  padding: 14px 22px;
}

@media (max-width: 720px) {
  .modal-panel {
    width: calc(100vw - 24px);
    height: calc(100vh - 24px);
  }

  .plan-form {
    grid-template-columns: 1fr;
    padding: 16px;
  }

  .modal-actions {
    margin: 2px -16px -16px;
    padding: 12px 16px;
  }
}
</style>
