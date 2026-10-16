<template>
  <section class="agent-section">
    <header class="section-header">
      <div>
        <h3>执行节点</h3>
        <p>展示已注册本地 Agent 的运行状态、能力和最近心跳。</p>
      </div>
      <button type="button" :disabled="loading" @click="$emit('refresh')">
        {{ loading ? '刷新中...' : '刷新' }}
      </button>
    </header>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>节点名称</th>
            <th>节点标识</th>
            <th>状态</th>
            <th>版本</th>
            <th>能力</th>
            <th>当前任务</th>
            <th>Token</th>
            <th>本地有头默认</th>
            <th>最近心跳</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="10" class="empty-cell">节点加载中...</td>
          </tr>
          <tr v-for="node in nodes" v-else :key="node.id">
            <td>{{ node.name }}</td>
            <td class="mono-cell">{{ node.data.node_key || '-' }}</td>
            <td>
              <span class="status-pill" :class="statusClass(node.data.agent_status)">
                {{ statusLabel(node.data.agent_status) }}
              </span>
            </td>
            <td>{{ node.data.version || '-' }}</td>
            <td>{{ capabilitiesText(node) }}</td>
            <td>{{ node.data.current_task_id || '-' }}</td>
            <td>
              <span v-if="node.data.has_agent_token" class="token-badge">
                已配置{{ node.data.token_last4 ? ` · ${node.data.token_last4}` : '' }}
              </span>
              <span v-else class="muted-text">未生成</span>
            </td>
            <td>
              <span v-if="node.data.default_local_headed" class="default-badge">默认</span>
              <span v-else class="muted-text">-</span>
            </td>
            <td>{{ formatDateTime(node.data.last_seen_at) }}</td>
            <td>
              <div class="action-group">
                <button
                  type="button"
                  class="ghost-button"
                  :disabled="loading || settingDefaultNodeId === node.id || node.data.default_local_headed"
                  @click="$emit('set-default-local-headed', node)"
                >
                  {{ settingDefaultNodeId === node.id ? '设置中...' : node.data.default_local_headed ? '已默认' : '设为默认' }}
                </button>
                <button type="button" class="ghost-button danger" :disabled="loading" @click="$emit('reset-token', node)">
                  重置 Token
                </button>
              </div>
            </td>
          </tr>
          <tr v-if="!loading && !nodes.length">
            <td colspan="10" class="empty-cell">暂无执行节点，请先生成 Token 并启动本地 Agent 客户端。</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script setup lang="ts">
import { AgentNodeStatus } from '../../constants/enums'
import type { AgentNode } from '../../types/agent'

defineProps<{
  nodes: AgentNode[]
  loading?: boolean
  settingDefaultNodeId?: number
}>()

defineEmits<{
  (event: 'refresh'): void
  (event: 'set-default-local-headed', node: AgentNode): void
  (event: 'reset-token', node: AgentNode): void
}>()

function capabilitiesText(node: AgentNode): string {
  const capabilities = node.data.capabilities
  return Array.isArray(capabilities) && capabilities.length ? capabilities.join(', ') : '-'
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

function formatDateTime(value: string | undefined): string {
  if (!value) return '-'
  return value.replace('T', ' ').replace('Z', '').slice(0, 19)
}
</script>

<style scoped>
.agent-section {
  min-width: 0;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 10px 28px rgb(15 23 42 / 6%);
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid #e5e7eb;
  padding: 16px 18px;
}

.section-header h3 {
  margin: 0;
  color: #111827;
  font-size: 17px;
}

.section-header p {
  margin: 5px 0 0;
  color: #6b7280;
  font-size: 13px;
}

.section-header button {
  height: 34px;
  border: 1px solid #2563eb;
  border-radius: 6px;
  background: #2563eb;
  color: #fff;
  cursor: pointer;
  padding: 0 12px;
}

.section-header button:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}

.table-wrap {
  overflow-x: auto;
}

table {
  width: 100%;
  min-width: 1060px;
  border-collapse: collapse;
}

th,
td {
  border-bottom: 1px solid #e5e7eb;
  padding: 12px 14px;
  text-align: left;
  vertical-align: top;
}

th {
  color: #6b7280;
  font-size: 12px;
  font-weight: 700;
}

td {
  color: #111827;
  font-size: 13px;
}

.mono-cell {
  color: #334155;
  font-family: Consolas, Monaco, 'Courier New', monospace;
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

.default-badge {
  display: inline-flex;
  min-width: 44px;
  justify-content: center;
  border-radius: 999px;
  background: #dbeafe;
  color: #1d4ed8;
  padding: 4px 9px;
  font-size: 12px;
  font-weight: 700;
}

.token-badge {
  display: inline-flex;
  justify-content: center;
  border-radius: 999px;
  background: #ecfdf5;
  color: #047857;
  padding: 4px 9px;
  font-size: 12px;
  font-weight: 700;
}

.muted-text {
  color: #9ca3af;
}

.action-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.ghost-button {
  height: 30px;
  border: 1px solid #bfdbfe;
  border-radius: 6px;
  background: #eff6ff;
  color: #1d4ed8;
  cursor: pointer;
  padding: 0 10px;
}

.ghost-button:disabled {
  cursor: not-allowed;
  opacity: 0.58;
}

.ghost-button.danger {
  border-color: #fecaca;
  background: #fef2f2;
  color: #b91c1c;
}

.empty-cell {
  color: #6b7280;
  text-align: center;
}

@media (max-width: 720px) {
  .section-header {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
