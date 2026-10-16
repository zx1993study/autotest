<template>
  <div v-if="visible" class="modal-backdrop" @click.self="$emit('close')">
    <section class="modal-panel" role="dialog" aria-modal="true" aria-label="生成记录详情">
      <header class="modal-header"><h3>{{ task?.name || '生成记录' }}</h3><button type="button" title="关闭" aria-label="关闭" @click="$emit('close')"><X :size="18" /></button></header>
      <p v-if="loading">加载中</p><p v-else-if="error" role="alert">{{ error }}</p>
      <template v-else-if="task">
        <dl><dt>状态</dt><dd>{{ task.status }}</dd><dt>进度</dt><dd>{{ task.data.progress || '-' }}</dd><dt>模型 HTTP 调用</dt><dd>{{ task.data.model_http_calls || 0 }}</dd></dl>
        <pre>{{ JSON.stringify(task.data.result || task.data, null, 2) }}</pre>
      </template>
    </section>
  </div>
</template>
<script setup lang="ts">
import { X } from 'lucide-vue-next'
import type { ResourceItem } from '../../types/resource'
defineProps<{ visible: boolean; loading: boolean; error: string; task: ResourceItem | null }>()
defineEmits<{ close: [] }>()
</script>
<style scoped>
.modal-panel { width: min(850px, calc(100vw - 24px)); max-height: 90dvh; overflow: auto; padding: 20px; } h3 { font-size: 18px; margin: 0; } dl { display: grid; grid-template-columns: 140px 1fr; gap: 12px; } dd { margin: 0; } pre { max-height: 60dvh; overflow: auto; white-space: pre-wrap; overflow-wrap: anywhere; font-size: 12px; background: #f6f8fa; padding: 12px; } button { width: 32px; height: 32px; padding: 6px; }
</style>
