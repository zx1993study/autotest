<template>
  <div v-if="visible" class="modal-backdrop" @click.self="requestClose">
    <section class="modal-panel" role="dialog" aria-modal="true">
      <header class="modal-header">
        <div>
          <h3>选择本地执行节点</h3>
          <p>本地有头执行会把 Web 用例投递给已安装的 Agent，由它打开本机浏览器运行。</p>
        </div>
        <button class="modal-close" type="button" aria-label="关闭" @click="requestClose">×</button>
      </header>

      <div class="modal-body">
        <label class="field">
          <span>执行节点<b>*</b></span>
          <select v-model="localNodeKey" :disabled="loading || submitting || !executableNodes.length">
            <option value="">请选择在线节点</option>
            <option v-for="node in executableNodes" :key="node.id" :value="node.data.node_key">
              {{ nodeOptionLabel(node) }}
            </option>
          </select>
        </label>

        <p v-if="error" class="form-error">{{ error }}</p>
        <p v-else-if="!loading && !executableNodes.length" class="empty-hint">
          未找到可执行 Web 用例的在线节点。请先启动本地 Agent，并确认能力包含 case_execution。
        </p>

        <div class="node-list">
          <div v-for="node in nodes" :key="node.id" class="node-row" :class="{ active: node.data.node_key === localNodeKey }">
            <div>
              <strong>{{ node.name }}</strong>
              <small>{{ node.data.node_key || '-' }}</small>
            </div>
            <span class="status-pill" :class="statusClass(node.data.agent_status)">
              {{ statusLabel(node.data.agent_status) }}
            </span>
          </div>
          <p v-if="loading" class="empty-hint">节点加载中...</p>
        </div>
      </div>

      <footer class="modal-actions">
        <button type="button" :disabled="loading || submitting" @click="$emit('refresh')">刷新节点</button>
        <button type="button" :disabled="submitting" @click="requestClose">取消</button>
        <button class="primary" type="button" :disabled="!canSubmit" @click="submit">
          {{ submitting ? '投递中...' : '投递执行' }}
        </button>
      </footer>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { AgentNodeStatus } from '../../constants/enums'
import type { AgentNode } from '../../types/agent'

const props = defineProps<{
  visible: boolean
  nodes: AgentNode[]
  loading?: boolean
  submitting?: boolean
  error?: string
  selectedNodeKey?: string
}>()

const emit = defineEmits<{
  (event: 'close'): void
  (event: 'refresh'): void
  (event: 'submit', nodeKey: string): void
}>()

const localNodeKey = ref('')

const executableNodes = computed(() => props.nodes.filter(canExecuteWebCase))

const canSubmit = computed(() => {
  return Boolean(localNodeKey.value) && !props.loading && !props.submitting
})

watch(
  () => [props.visible, props.selectedNodeKey, props.nodes.length],
  () => {
    if (!props.visible) return
    const preferred = props.selectedNodeKey || localNodeKey.value
    const matched = executableNodes.value.find(node => node.data.node_key === preferred)
    localNodeKey.value = matched?.data.node_key || executableNodes.value[0]?.data.node_key || ''
  },
  { immediate: true }
)

function submit() {
  if (!canSubmit.value) return
  emit('submit', localNodeKey.value)
}

function requestClose() {
  if (props.submitting) return
  emit('close')
}

function canExecuteWebCase(node: AgentNode): boolean {
  const status = String(node.data.agent_status || '')
  const isAvailable = status === AgentNodeStatus.ONLINE || status === AgentNodeStatus.BUSY
  const capabilities = Array.isArray(node.data.capabilities) ? node.data.capabilities : []
  const supportsCaseExecution =
    !capabilities.length || capabilities.includes('case_execution') || capabilities.includes('*')
  return Boolean(node.data.node_key) && isAvailable && supportsCaseExecution
}

function nodeOptionLabel(node: AgentNode): string {
  const version = node.data.version ? `v${node.data.version}` : '未标记版本'
  return `${node.name} · ${statusLabel(node.data.agent_status)} · ${version}`
}

function statusLabel(status: unknown): string {
  const labels: Record<string, string> = {
    [AgentNodeStatus.ONLINE]: '在线',
    [AgentNodeStatus.OFFLINE]: '离线',
    [AgentNodeStatus.BUSY]: '忙碌',
    [AgentNodeStatus.DISABLED]: '停用'
  }
  return labels[String(status || '')] || '-'
}

function statusClass(status: unknown): string {
  const value = String(status || '')
  if (value === AgentNodeStatus.ONLINE) return 'success'
  if (value === AgentNodeStatus.BUSY) return 'warning'
  if (value === AgentNodeStatus.DISABLED) return 'neutral'
  return 'danger'
}
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: grid;
  place-items: center;
  padding: 28px;
  background: rgb(15 23 42 / 54%);
}

.modal-panel {
  width: min(680px, 100%);
  max-height: calc(100vh - 56px);
  overflow: auto;
  border: 1px solid #dbe3ef;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 24px 60px rgb(15 23 42 / 22%);
}

.modal-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  border-bottom: 1px solid #e5e7eb;
  padding: 18px 20px;
}

.modal-header h3 {
  margin: 0;
  color: #111827;
  font-size: 18px;
}

.modal-header p {
  margin: 6px 0 0;
  color: #6b7280;
  font-size: 13px;
  line-height: 1.5;
}

.modal-close {
  border: 0;
  background: transparent;
  color: #64748b;
  font-size: 24px;
  line-height: 1;
  cursor: pointer;
}

.modal-body {
  display: grid;
  gap: 14px;
  padding: 18px 20px;
}

.field {
  display: grid;
  gap: 7px;
  color: #374151;
  font-size: 13px;
  font-weight: 600;
}

.field b {
  margin-left: 3px;
  color: #dc2626;
}

.field select {
  height: 38px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  color: #111827;
  font: inherit;
  padding: 0 10px;
}

.field select:disabled {
  background: #f9fafb;
  color: #9ca3af;
}

.form-error,
.empty-hint {
  margin: 0;
  font-size: 13px;
}

.form-error {
  color: #dc2626;
}

.empty-hint {
  color: #6b7280;
}

.node-list {
  display: grid;
  gap: 8px;
  max-height: 260px;
  overflow: auto;
}

.node-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 10px 12px;
}

.node-row.active {
  border-color: #93c5fd;
  background: #eff6ff;
}

.node-row strong,
.node-row small {
  display: block;
}

.node-row strong {
  color: #111827;
  font-size: 14px;
}

.node-row small {
  margin-top: 4px;
  color: #64748b;
  font-family: Consolas, Monaco, 'Courier New', monospace;
  font-size: 12px;
}

.status-pill {
  display: inline-flex;
  min-width: 52px;
  justify-content: center;
  border-radius: 999px;
  padding: 4px 9px;
  font-size: 12px;
  font-weight: 700;
}

.status-pill.success {
  background: #dcfce7;
  color: #166534;
}

.status-pill.warning {
  background: #fef3c7;
  color: #92400e;
}

.status-pill.danger {
  background: #fee2e2;
  color: #991b1b;
}

.status-pill.neutral {
  background: #f3f4f6;
  color: #4b5563;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  border-top: 1px solid #e5e7eb;
  padding: 14px 20px;
}

.modal-actions button {
  height: 36px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  color: #374151;
  cursor: pointer;
  padding: 0 14px;
}

.modal-actions button.primary {
  border-color: #2563eb;
  background: #2563eb;
  color: #fff;
}

.modal-actions button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

@media (max-width: 640px) {
  .modal-backdrop {
    padding: 14px;
  }

  .modal-actions {
    flex-wrap: wrap;
  }
}
</style>
