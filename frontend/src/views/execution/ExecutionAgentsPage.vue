<template>
  <section class="agents-page">
    <header class="page-header">
      <div>
        <h2>执行节点</h2>
        <p>管理本地 Agent 节点，并查看有头浏览器任务的派发与回传情况。</p>
      </div>
      <div class="header-actions">
        <button type="button" class="secondary-button" @click="openTokenDialog">生成 Token</button>
        <button type="button" :disabled="loading" @click="loadAll">
          {{ loading ? '刷新中...' : '刷新全部' }}
        </button>
      </div>
    </header>

    <p v-if="errorMessage" class="error-banner">{{ errorMessage }}</p>
    <p v-if="successMessage" class="success-banner">{{ successMessage }}</p>

    <section class="summary-grid" aria-label="Agent 运行概览">
      <article v-for="metric in metrics" :key="metric.key" class="metric-card" :class="metric.tone">
        <span>{{ metric.label }}</span>
        <strong>{{ metric.value }}</strong>
        <small>{{ metric.hint }}</small>
      </article>
    </section>

    <div class="agent-layout">
      <AgentNodeTable
        :nodes="nodes"
        :loading="nodesLoading"
        :setting-default-node-id="settingDefaultNodeId"
        @refresh="loadNodes"
        @set-default-local-headed="setDefaultNode"
        @reset-token="resetNodeToken"
      />
      <AgentTaskTable :tasks="tasks" :loading="tasksLoading" @refresh="loadTasks" />
    </div>

    <div v-if="tokenDialogOpen" class="modal-mask" role="dialog" aria-modal="true">
      <form class="token-dialog" @submit.prevent="submitTokenProvision">
        <header>
          <div>
            <h3>Agent Token</h3>
            <p>明文 token 只展示一次，请写入本地 Agent 配置。</p>
          </div>
          <button type="button" class="icon-button" @click="closeTokenDialog">×</button>
        </header>

        <label>
          <span>节点标识</span>
          <input v-model.trim="tokenForm.node_key" required maxlength="128" placeholder="local-win-01" />
        </label>
        <label>
          <span>节点名称</span>
          <input v-model.trim="tokenForm.name" required maxlength="128" placeholder="本机 Windows 节点" />
        </label>
        <label>
          <span>能力</span>
          <input v-model.trim="tokenForm.capabilities" placeholder="case_execution, stagehand" />
        </label>

        <div v-if="tokenPlaintext" class="token-result">
          <span>Agent Token</span>
          <code>{{ tokenPlaintext }}</code>
          <button type="button" class="secondary-button" @click="copyToken">复制</button>
        </div>

        <footer>
          <button type="button" class="secondary-button" @click="closeTokenDialog">关闭</button>
          <button type="submit" :disabled="savingToken">
            {{ savingToken ? '生成中...' : tokenPlaintext ? '重新生成' : '生成' }}
          </button>
        </footer>
      </form>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import AgentNodeTable from '../../components/execution/AgentNodeTable.vue'
import AgentTaskTable from '../../components/execution/AgentTaskTable.vue'
import { AgentNodeStatus, AgentTaskStatus } from '../../constants/enums'
import {
  listAgentNodes,
  listAgentTasks,
  provisionAgentNodeToken,
  resetAgentNodeToken,
  setDefaultLocalHeadedNode
} from '../../services/agent.service'
import type { AgentNode, AgentTask } from '../../types/agent'

const nodes = ref<AgentNode[]>([])
const tasks = ref<AgentTask[]>([])
const nodesLoading = ref(false)
const tasksLoading = ref(false)
const settingDefaultNodeId = ref(0)
const errorMessage = ref('')
const successMessage = ref('')
const tokenDialogOpen = ref(false)
const savingToken = ref(false)
const tokenPlaintext = ref('')
const tokenForm = ref({
  node_key: '',
  name: '',
  capabilities: 'case_execution, stagehand'
})

const loading = computed(() => nodesLoading.value || tasksLoading.value)
const onlineNodes = computed(() => nodes.value.filter(node => node.data.agent_status === AgentNodeStatus.ONLINE))
const defaultLocalHeadedNode = computed(() => nodes.value.find(node => node.data.default_local_headed))
const runningTasks = computed(() => tasks.value.filter(task => task.status === AgentTaskStatus.RUNNING))
const pendingTasks = computed(() => tasks.value.filter(task => task.status === AgentTaskStatus.PENDING))
const failedTasks = computed(() => tasks.value.filter(task => task.status === AgentTaskStatus.FAILED))

const metrics = computed(() => [
  {
    key: 'nodes',
    label: '注册节点',
    value: String(nodes.value.length),
    hint: `在线 ${onlineNodes.value.length} 个，默认 ${defaultLocalHeadedNode.value?.name || '未设置'}`,
    tone: 'info'
  },
  {
    key: 'pending',
    label: '待领取任务',
    value: String(pendingTasks.value.length),
    hint: '等待 Agent 领取',
    tone: 'warning'
  },
  {
    key: 'running',
    label: '执行中任务',
    value: String(runningTasks.value.length),
    hint: '本地浏览器运行中',
    tone: 'success'
  },
  {
    key: 'failed',
    label: '失败任务',
    value: String(failedTasks.value.length),
    hint: '最近 10 条内统计',
    tone: 'danger'
  }
])

onMounted(loadAll)

async function loadAll() {
  errorMessage.value = ''
  successMessage.value = ''
  await Promise.all([loadNodes(), loadTasks()])
}

async function loadNodes() {
  nodesLoading.value = true
  try {
    const result = await listAgentNodes({ page: 1, pageSize: 100 })
    nodes.value = result.items
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    nodesLoading.value = false
  }
}

async function setDefaultNode(node: AgentNode) {
  settingDefaultNodeId.value = node.id
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const updated = await setDefaultLocalHeadedNode(node.id)
    successMessage.value = `已将 ${updated.name} 设置为本地有头默认节点`
    await loadNodes()
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    settingDefaultNodeId.value = 0
  }
}

function openTokenDialog() {
  errorMessage.value = ''
  successMessage.value = ''
  tokenPlaintext.value = ''
  tokenForm.value = {
    node_key: '',
    name: '',
    capabilities: 'case_execution, stagehand'
  }
  tokenDialogOpen.value = true
}

function closeTokenDialog() {
  tokenDialogOpen.value = false
}

async function submitTokenProvision() {
  savingToken.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const result = await provisionAgentNodeToken({
      node_key: tokenForm.value.node_key,
      name: tokenForm.value.name,
      capabilities: parseCapabilities(tokenForm.value.capabilities),
      system: {}
    })
    tokenPlaintext.value = result.agent_token
    successMessage.value = `已生成 ${result.node.name} 的 Agent Token`
    await loadNodes()
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    savingToken.value = false
  }
}

async function resetNodeToken(node: AgentNode) {
  const confirmed = window.confirm(`重置 ${node.name} 的 Agent Token 后，旧配置会立即失效。是否继续？`)
  if (!confirmed) return
  errorMessage.value = ''
  successMessage.value = ''
  savingToken.value = true
  try {
    const result = await resetAgentNodeToken(node.id)
    tokenForm.value = {
      node_key: result.node.data.node_key,
      name: result.node.name,
      capabilities: capabilitiesToText(result.node)
    }
    tokenPlaintext.value = result.agent_token
    tokenDialogOpen.value = true
    successMessage.value = `已重置 ${result.node.name} 的 Agent Token`
    await loadNodes()
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    savingToken.value = false
  }
}

async function copyToken() {
  if (!tokenPlaintext.value) return
  try {
    await navigator.clipboard.writeText(tokenPlaintext.value)
    successMessage.value = 'Agent Token 已复制'
  } catch {
    errorMessage.value = '当前浏览器不允许自动复制，请手动复制 Token'
  }
}

function parseCapabilities(value: string): string[] {
  return value
    .split(',')
    .map(item => item.trim())
    .filter(Boolean)
}

function capabilitiesToText(node: AgentNode): string {
  const capabilities = node.data.capabilities
  return Array.isArray(capabilities) ? capabilities.join(', ') : ''
}

async function loadTasks() {
  tasksLoading.value = true
  try {
    const result = await listAgentTasks({ page: 1, pageSize: 10 })
    tasks.value = result.items
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    tasksLoading.value = false
  }
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Agent 数据加载失败'
}
</script>

<style scoped>
.agents-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
}

.page-header h2 {
  margin: 0;
  color: #111827;
  font-size: 22px;
}

.page-header p {
  margin: 6px 0 0;
  color: #6b7280;
  font-size: 14px;
}

.page-header button {
  height: 36px;
  border: 1px solid #2563eb;
  border-radius: 6px;
  background: #2563eb;
  color: #fff;
  cursor: pointer;
  padding: 0 14px;
}

.header-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: flex-end;
}

.secondary-button {
  border-color: #d1d5db !important;
  background: #fff !important;
  color: #374151 !important;
}

.page-header button:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}

.error-banner,
.success-banner {
  margin: 0;
  border-radius: 6px;
  padding: 10px 12px;
}

.error-banner {
  border: 1px solid #fecaca;
  background: #fef2f2;
  color: #b91c1c;
}

.success-banner {
  border: 1px solid #bbf7d0;
  background: #f0fdf4;
  color: #166534;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.metric-card {
  display: flex;
  min-height: 112px;
  flex-direction: column;
  justify-content: space-between;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 10px 24px rgb(15 23 42 / 5%);
  padding: 16px;
}

.metric-card span,
.metric-card small {
  color: #6b7280;
}

.metric-card strong {
  color: #111827;
  font-size: 28px;
  line-height: 1.1;
}

.metric-card.info {
  border-color: #bfdbfe;
}

.metric-card.warning {
  border-color: #fde68a;
}

.metric-card.success {
  border-color: #bbf7d0;
}

.metric-card.danger {
  border-color: #fecaca;
}

.agent-layout {
  display: grid;
  gap: 18px;
}

.modal-mask {
  position: fixed;
  z-index: 40;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgb(15 23 42 / 45%);
  padding: 24px;
}

.token-dialog {
  display: grid;
  width: min(560px, 100%);
  gap: 14px;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 24px 80px rgb(15 23 42 / 26%);
  padding: 20px;
}

.token-dialog header,
.token-dialog footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.token-dialog h3 {
  margin: 0;
  color: #111827;
  font-size: 18px;
}

.token-dialog p {
  margin: 5px 0 0;
  color: #6b7280;
  font-size: 13px;
}

.token-dialog label {
  display: grid;
  gap: 7px;
  color: #374151;
  font-size: 13px;
  font-weight: 700;
}

.token-dialog input {
  height: 36px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  color: #111827;
  padding: 0 10px;
}

.token-dialog footer {
  justify-content: flex-end;
}

.token-dialog footer button,
.token-result button {
  height: 34px;
  border: 1px solid #2563eb;
  border-radius: 6px;
  background: #2563eb;
  color: #fff;
  cursor: pointer;
  padding: 0 12px;
}

.icon-button {
  width: 32px;
  height: 32px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #fff;
  color: #6b7280;
  cursor: pointer;
  font-size: 20px;
  line-height: 1;
}

.token-result {
  display: grid;
  gap: 8px;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  background: #eff6ff;
  padding: 12px;
}

.token-result span {
  color: #1e40af;
  font-size: 13px;
  font-weight: 700;
}

.token-result code {
  overflow-wrap: anywhere;
  color: #111827;
  font-family: Consolas, Monaco, 'Courier New', monospace;
  font-size: 13px;
}

@media (max-width: 920px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .page-header {
    align-items: stretch;
    flex-direction: column;
  }

  .summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>
