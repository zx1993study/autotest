<template>
  <div v-if="open" class="modal-backdrop" @click.self="emit('close')">
    <section class="modal-panel" role="dialog" aria-modal="true">
      <header class="modal-header">
        <div>
          <h3>添加手动测试功能点</h3>
          <p>手动功能点执行时会自动标记为已跳过。</p>
        </div>
        <button type="button" class="modal-close" aria-label="关闭" @click="emit('close')">×</button>
      </header>
      <form class="manual-form" @submit.prevent="submit">
        <label><span>功能点名称</span><input v-model.trim="name" maxlength="128" placeholder="请输入功能点名称" /></label>
        <label><span>备注</span><textarea v-model.trim="description" maxlength="2000" rows="4" placeholder="请输入测试口径或验收说明"></textarea></label>
        <p v-if="errorMessage" class="form-error">{{ errorMessage }}</p>
        <footer class="modal-actions">
          <button type="button" @click="emit('close')">取消</button>
          <button type="submit" class="primary" :disabled="saving">{{ saving ? '添加中...' : '添加' }}</button>
        </footer>
      </form>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

import { addExecutionPlanManualFeature } from '../../services/execution-plan.service'
import type { ExecutionPlanDetail } from '../../types/execution-plan'

const props = defineProps<{ open: boolean; planId: number }>()
const emit = defineEmits<{ close: []; saved: [detail: ExecutionPlanDetail, message: string] }>()
const name = ref('')
const description = ref('')
const saving = ref(false)
const errorMessage = ref('')

watch(() => props.open, open => {
  if (!open) return
  name.value = ''
  description.value = ''
  errorMessage.value = ''
})

async function submit() {
  if (!name.value) {
    errorMessage.value = '请输入功能点名称'
    return
  }
  saving.value = true
  errorMessage.value = ''
  try {
    const detail = await addExecutionPlanManualFeature(props.planId, {
      feature_name: name.value,
      description: description.value || null
    })
    emit('saved', detail, '手动测试功能点已添加')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '手动功能点添加失败'
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.modal-panel { width: min(560px, calc(100vw - 32px)); }
.modal-header,
.modal-actions { align-items: center; display: flex; justify-content: space-between; }
.modal-header h3,
.modal-header p { margin: 0; }
.modal-header p { color: #64748b; margin-top: 4px; }
.manual-form,
.manual-form label { display: flex; flex-direction: column; gap: 8px; }
.manual-form { gap: 16px; }
.manual-form input,
.manual-form textarea { border: 1px solid #cad4e2; border-radius: 6px; padding: 9px 10px; }
.modal-actions { justify-content: flex-end; gap: 10px; }
.form-error { color: #dc2626; }
</style>
