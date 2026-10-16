<template>
  <div v-if="active" class="operation-controls">
    <span v-if="waiting && !waiting.confirmed" role="status">等待本地输入：{{ waiting.label }}</span>
    <button v-if="waiting && !waiting.confirmed" type="button" :disabled="busy" @click="control('continue')"><Play :size="15" />输入完成，继续</button>
    <button type="button" :disabled="busy" @click="control('cancel')"><Square :size="15" />中止</button>
    <p v-if="error" role="alert">{{ error }}</p>
  </div>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import { Play, Square } from 'lucide-vue-next'
import type { AgentTask } from '../../types/agent'
import { webOperationControl } from '../../services/web-feature.service'
const props = defineProps<{ task: AgentTask | null }>()
const emit = defineEmits<{ changed: [] }>()
const busy = ref(false), error = ref('')
const active = computed(() => ['pending', 'running'].includes(props.task?.status || ''))
const waiting = computed(() => props.task?.data.waiting_input as { label: string; nonce: string; confirmed: boolean } | undefined)
async function control(action: 'continue' | 'cancel') {
  if (!props.task) return
  busy.value = true; error.value = ''
  try { await webOperationControl(props.task.id, action, waiting.value?.nonce); emit('changed') }
  catch (e) { error.value = e instanceof Error ? e.message : '操作失败' }
  finally { busy.value = false }
}
</script>
<style scoped>
.operation-controls { display:flex; gap:10px; flex-wrap:wrap; align-items:center; padding:12px 0; }
button { display:inline-flex; gap:6px; align-items:center; } p { width:100%; color:#b42318; margin:0; }
</style>
