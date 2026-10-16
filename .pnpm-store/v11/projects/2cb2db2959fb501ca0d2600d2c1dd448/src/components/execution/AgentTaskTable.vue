<template>
  <section class="agent-section">
    <header class="section-header">
      <div>
        <h3>最近 Agent 任务</h3>
      </div>
      <button type="button" :disabled="loading" @click="$emit('refresh')">
        {{ loading ? '刷新中...' : '刷新' }}
      </button>
    </header>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>任务</th>
            <th>类型</th>
            <th>状态</th>
            <th>目标节点</th>
            <th>领取节点</th>
            <th>浏览器</th>
            <th>执行结果</th>
            <th>创建时间</th>
            <th>完成时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="9" class="empty-cell">任务加载中...</td>
          </tr>
          <tr v-for="task in tasks" v-else :key="task.id">
            <td>
              <strong>#{{ task.id }}</strong>
              <small>{{ task.name }}</small>
            </td>
            <td>{{ taskTypeLabel(task.data.task_type) }}</td>
            <td>
              <span class="status-pill" :class="statusClass(task.status)">
                {{ statusLabel(task.status) }}
              </span>
            </td>
            <td class="mono-cell">{{ task.data.node_key || '任意节点' }}</td>
            <td class="mono-cell">{{ task.data.claimed_by || '-' }}</td>
            <td><button v-if="isWebTask(task)" type="button" title="查看任务浏览器" aria-label="查看任务浏览器" @click="selectedTaskId = selectedTaskId === task.id ? null : task.id"><MonitorUp :size="16" /></button></td>
            <td>{{ resultSummary(task) }}</td>
            <td>{{ formatDateTime(task.data.created_at || task.created_at) }}</td>
            <td>{{ formatDateTime(task.data.finished_at) }}</td>
          </tr>
          <tr v-if="!loading && !tasks.length">
            <td colspan="9" class="empty-cell">暂无 Agent 任务。</td>
          </tr>
        </tbody>
      </table>
    </div>
    <BrowserWindowPanel v-if="selectedTaskId" :task-id="selectedTaskId" class="selected-browser" />
  </section>
</template>

<script setup lang="ts">
import { AgentTaskStatus, AgentTaskType } from '../../constants/enums'
import type { AgentTask } from '../../types/agent'
import { ref } from 'vue'
import { MonitorUp } from 'lucide-vue-next'
import BrowserWindowPanel from './BrowserWindowPanel.vue'

const selectedTaskId = ref<number | null>(null)
function isWebTask(task: AgentTask) { return ['web_vision_discovery', 'web_replay'].includes(task.data.task_type) || task.data.payload?.case_type === 'WEB' }

defineProps<{
  tasks: AgentTask[]
  loading?: boolean
}>()

defineEmits<{
  (event: 'refresh'): void
}>()

function taskTypeLabel(type: unknown): string {
  const labels: Record<string, string> = {
    [AgentTaskType.CASE_EXECUTION]: '用例执行',
    [AgentTaskType.DEVICE_DISCOVERY]: '设备检测'
  }
  return labels[String(type || '')] || String(type || '-')
}

function statusLabel(status: unknown): string {
  const labels: Record<string, string> = {
    [AgentTaskStatus.PENDING]: '待领取',
    [AgentTaskStatus.RUNNING]: '执行中',
    [AgentTaskStatus.SUCCESS]: '成功',
    [AgentTaskStatus.FAILED]: '失败',
    [AgentTaskStatus.CANCELED]: '已取消'
  }
  return labels[String(status || '')] || '-'
}

function statusClass(status: unknown): string {
  const value = String(status || '')
  if (value === AgentTaskStatus.SUCCESS) return 'success'
  if (value === AgentTaskStatus.FAILED) return 'danger'
  if (value === AgentTaskStatus.RUNNING) return 'info'
  if (value === AgentTaskStatus.PENDING) return 'warning'
  return 'neutral'
}

function resultSummary(task: AgentTask): string {
  if (task.data.error) return task.data.error
  const result = task.data.result
  if (!result) return '-'
  const total = Number(result.total ?? 0)
  const success = Number(result.success_count ?? 0)
  const failed = Number(result.failed_count ?? 0)
  const queued = Number(result.queued_count ?? 0)
  return `共 ${total}，成功 ${success}，失败 ${failed}，排队 ${queued}`
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
.selected-browser { margin: 0 18px; }

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
  min-width: 980px;
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

td strong,
td small {
  display: block;
}

td small {
  margin-top: 4px;
  color: #6b7280;
}

.mono-cell {
  color: #334155;
  font-family: Consolas, Monaco, 'Courier New', monospace;
}

.status-pill {
  display: inline-flex;
  min-width: 56px;
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

.status-pill.danger {
  background: #fee2e2;
  color: #991b1b;
}

.status-pill.info {
  background: #dbeafe;
  color: #1d4ed8;
}

.status-pill.warning {
  background: #fef3c7;
  color: #92400e;
}

.status-pill.neutral {
  background: #f3f4f6;
  color: #4b5563;
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
