<template>
  <ResourcePage
    ref="resourcePage"
    title="App 设备池"
    description=""
    api-path="/app-testing/devices"
    :row-actions="rowActions"
    :fields="appDeviceFields"
    :columns="appDeviceColumns"
  >
    <template #search-actions>
      <button type="button" @click="openDiscovery">扫描设备</button>
      <button type="button" :disabled="checking" @click="batchCheckDevices">
        {{ checking ? '检测中...' : '批量检测' }}
      </button>
    </template>
  </ResourcePage>

  <div v-if="discoveryVisible" class="modal-backdrop" @click.self="closeDiscovery">
    <section class="modal-panel discovery-panel" role="dialog" aria-modal="true">
      <header class="modal-header">
        <div>
          <h3>扫描设备</h3>
        </div>
        <button class="modal-close" type="button" aria-label="关闭" @click="closeDiscovery">×</button>
      </header>

      <div class="discovery-layout">
        <aside class="discovery-side">
          <label class="field"><span>执行节点</span><select v-model="scanNodeKey" aria-label="扫描执行节点"><option value="">自动选择在线节点</option><option v-for="node in scanNodes" :key="node.id" :value="node.data.node_key">{{ node.name }}</option></select></label>
          <section class="setting-block">
            <span>扫描范围</span>
            <label class="check-row">
              <input v-model="selectedPlatforms" type="checkbox" value="iOS" />
              iOS
            </label>
          </section>

          <section class="setting-block">
            <span>导入设置</span>
            <label>
              关联项目
              <select v-model="importProjectId">
                <option value="">不关联项目</option>
                <option v-for="project in projectOptions" :key="project.id" :value="String(project.id)">
                  {{ project.name || `项目 ${project.id}` }}
                </option>
              </select>
            </label>
            <label>
              标签
              <input v-model.trim="deviceTags" placeholder="例如：本机,冒烟" />
            </label>
            <label class="check-row">
              <input v-model="updateExisting" type="checkbox" />
              已存在设备同步状态
            </label>
          </section>


          <section class="setting-block">
            <span>同 WiFi WDA</span>
            <label>
              扫描网段
              <input v-model.trim="wdaSubnet" placeholder="例如：192.168.1.0/24；留空自动推断" />
            </label>
            <label>
              WDA 端口
              <input v-model.number="wdaPort" type="number" min="1" max="65535" />
            </label>
          </section>
        </aside>

        <main class="discovery-main">
          <div class="discovery-actions">
            <button type="button" :disabled="discovering || !selectedPlatforms.length" @click="discoverDevices">
              {{ discovering ? '扫描中...' : '重新扫描' }}
            </button>
            <button type="button" :disabled="wdaDiscovering" @click="discoverWifiWda">
              {{ wdaDiscovering ? '扫描WDA中...' : '扫描同 WiFi WDA' }}
            </button>
            <button type="button" :disabled="!importableDevices.length" @click="toggleAllDiscovered">
              {{ allImportableSelected ? '取消全选' : '全选可导入' }}
            </button>
            <button type="button" :disabled="importing || !selectedDevices.length" @click="importDevices">
              {{ importing ? '导入中...' : `添加到设备池 (${selectedDevices.length})` }}
            </button>
          </div>

          <div v-if="discoveryMessage" class="message" :class="{ error: Boolean(discoveryError) }">
            {{ discoveryMessage }}
          </div>

          <div class="summary-row">
            <span>共 {{ discoveredDevices.length }} 台</span>
            <span>在线 {{ discoverySummary.online || 0 }} 台</span>
            <span>已添加 {{ discoverySummary.existing || 0 }} 台</span>
            <span>待新增 {{ discoverySummary.new || 0 }} 台</span>
          </div>

          <div class="device-table-wrap">
            <table>
              <thead>
                <tr>
                  <th class="check-column">选择</th>
                  <th>设备</th>
                  <th>平台</th>
                  <th>类型</th>
                  <th>系统</th>
                  <th>UDID</th>
                  <th>状态</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="device in discoveredDevices" :key="deviceKey(device)" :class="{ muted: !canImportDevice(device) }">
                  <td>
                    <input
                      v-model="selectedDeviceKeys"
                      type="checkbox"
                      :value="deviceKey(device)"
                      :disabled="!canImportDevice(device)"
                    />
                  </td>
                  <td>
                    <strong>{{ device.name || device.device_name || '未命名设备' }}</strong>
                    <small>{{ warningText(device) }}</small>
                  </td>
                  <td>{{ device.platform || '-' }}</td>
                  <td>{{ formFactorLabel(device.device_form_factor) }}</td>
                  <td>{{ device.platform_version || '-' }}</td>
                  <td class="mono">{{ device.udid || '-' }}</td>
                  <td>
                    <span class="status-pill" :class="statusClass(device)">
                      {{ device.exists ? '已添加' : connectionStatusLabel(device.connection_status) }}
                    </span>
                  </td>
                </tr>
                <tr v-if="!discoveredDevices.length">
                  <td class="empty-cell" colspan="7">暂无扫描结果</td>
                </tr>
              </tbody>
            </table>
          </div>
        </main>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

import { request } from '../../api/client'
import { listRemoteOptions, postAction } from '../../api/http'
import ResourcePage from '../../components/ResourcePage.vue'
import { listAgentNodes, waitForAgentTask } from '../../services/agent.service'
import type { AgentNode, AgentTask } from '../../types/agent'
import { appDeviceColumns, appDeviceFields } from '../../resourceSchemas'
import type { PageAction } from '../../types/page-actions'
import type { SelectOptionRecord } from '../../types/resource'

interface DiscoveredDevice {
  source?: string
  platform?: string
  device_form_factor?: string
  udid?: string
  name?: string
  device_name?: string
  platform_version?: string
  connection_status?: string
  exists?: boolean
  existing_id?: number
  warnings?: string[]
  [key: string]: unknown
}

interface DiscoveryResult {
  items: DiscoveredDevice[]
  summary: {
    total?: number
    online?: number
    existing?: number
    new?: number
  }
  tool_status?: Record<string, unknown>
  warnings?: string[]
}

const rowActions: PageAction[] = [
  {
    label: '检测',
    path: '/app-testing/devices/check',
    payload: { id: '$id' },
    feedback: 'toast',
    successTitle: '检测完成',
    awaitAgentTasks: true
  },
  {
    label: '检测WDA',
    path: '/app-testing/devices/wda/check',
    payload: { id: '$id' },
    feedback: 'modal',
    successTitle: 'WDA 检测完成',
    awaitAgentTasks: true,
    enabledWhen: { key: 'data.platform', value: 'iOS' }
  },
  {
    label: '刷新',
    path: '/app-testing/devices/{id}/refresh',
    feedback: 'toast',
    successTitle: '设备信息已刷新',
    awaitAgentTasks: true
  }
]

const resourcePage = ref<InstanceType<typeof ResourcePage> | null>(null)
const discoveryVisible = ref(false)
const scanNodeKey = ref('')
const scanNodes = ref<AgentNode[]>([])
const discovering = ref(false)
const wdaDiscovering = ref(false)
const importing = ref(false)
const checking = ref(false)
const selectedPlatforms = ref(['iOS'])
const discoveredDevices = ref<DiscoveredDevice[]>([])
const selectedDeviceKeys = ref<string[]>([])
const discoverySummary = ref<DiscoveryResult['summary']>({})
const discoveryMessage = ref('')
const discoveryError = ref('')
const projectOptions = ref<SelectOptionRecord[]>([])
const importProjectId = ref('')
const deviceTags = ref('本机')
const updateExisting = ref(true)
const wdaSubnet = ref('')
const wdaPort = ref(8100)

const importableDevices = computed(() => discoveredDevices.value.filter(canImportDevice))
const allImportableSelected = computed(() => {
  const keys = importableDevices.value.map(deviceKey)
  return keys.length > 0 && keys.every(key => selectedDeviceKeys.value.includes(key))
})
const selectedDevices = computed(() => {
  const selected = new Set(selectedDeviceKeys.value)
  return discoveredDevices.value.filter(device => selected.has(deviceKey(device)) && canImportDevice(device))
})

async function openDiscovery() {
  discoveryVisible.value = true
  discoveryMessage.value = ''
  discoveryError.value = ''
  try {
    const nodes = await listAgentNodes({ pageSize: 100 })
    scanNodes.value = nodes.items.filter(node => node.data.capabilities?.includes('device_discovery'))
    if (scanNodes.value.length === 1) scanNodeKey.value = scanNodes.value[0].data.node_key
  } catch { scanNodes.value = [] }
  if (!projectOptions.value.length) {
    try {
      projectOptions.value = await listRemoteOptions('/projects/options')
    } catch {
      projectOptions.value = []
    }
  }
  await discoverDevices()
}

function closeDiscovery() {
  if (discovering.value || wdaDiscovering.value || importing.value) return
  discoveryVisible.value = false
}

async function discoverDevices() {
  discovering.value = true
  discoveryMessage.value = ''
  discoveryError.value = ''
  try {
    const params = new URLSearchParams()
    if (scanNodeKey.value) params.set('node_id', scanNodeKey.value)
    selectedPlatforms.value.forEach(platform => params.append('platform', platform))
    const query = params.toString()
    const result = await resolveDiscovery(await request<DiscoveryResult & { queued?: boolean; agent_task?: AgentTask }>({
      method: 'GET',
      url: query ? `/app-testing/devices/discover?${query}` : '/app-testing/devices/discover'
    }))
    discoveredDevices.value = result.items || []
    discoverySummary.value = result.summary || {}
    selectedDeviceKeys.value = defaultSelectedDeviceKeys(discoveredDevices.value)
    discoveryMessage.value = result.warnings?.length ? result.warnings.join('；') : '扫描完成'
  } catch (error) {
    discoveryError.value = getErrorMessage(error)
    discoveryMessage.value = discoveryError.value
  } finally {
    discovering.value = false
  }
}

async function discoverWifiWda() {
  wdaDiscovering.value = true
  discoveryMessage.value = ''
  discoveryError.value = ''
  try {
    const params = new URLSearchParams()
    if (scanNodeKey.value) params.set('node_id', scanNodeKey.value)
    if (wdaSubnet.value) params.set('subnet', wdaSubnet.value)
    if (wdaPort.value) params.append('port', String(wdaPort.value))
    const query = params.toString()
    const result = await resolveDiscovery(await request<DiscoveryResult & { queued?: boolean; agent_task?: AgentTask }>({
      method: 'GET',
      url: query ? `/app-testing/devices/wda/discover?${query}` : '/app-testing/devices/wda/discover'
    }))
    discoveredDevices.value = result.items || []
    discoverySummary.value = result.summary || {}
    selectedDeviceKeys.value = defaultSelectedDeviceKeys(discoveredDevices.value)
    discoveryMessage.value = result.warnings?.length ? result.warnings.join('；') : 'WDA 扫描完成'
  } catch (error) {
    discoveryError.value = getErrorMessage(error)
    discoveryMessage.value = discoveryError.value
  } finally {
    wdaDiscovering.value = false
  }
}

async function resolveDiscovery(result: DiscoveryResult & { queued?: boolean; agent_task?: AgentTask }): Promise<DiscoveryResult> {
  if (!result.queued || !result.agent_task) return result
  discoveryMessage.value = '已提交本地节点扫描，等待结果…'
  return await waitForAgentTask(result.agent_task.id) as unknown as DiscoveryResult
}

async function importDevices() {
  if (!selectedDevices.value.length) return
  importing.value = true
  discoveryMessage.value = ''
  discoveryError.value = ''
  try {
    const result = await postAction<{
      created_count: number
      updated_count: number
      skipped_count: number
    }>('/app-testing/devices/import-discovered', {
      project_id: importProjectId.value ? Number(importProjectId.value) : null,
      tags: deviceTags.value || null,
      update_existing: updateExisting.value,
      items: selectedDevices.value
    })
    discoveryMessage.value = `导入完成：新增 ${result.created_count} 台，更新 ${result.updated_count} 台，跳过 ${result.skipped_count} 台`
    await resourcePage.value?.load()
    await discoverDevices()
  } catch (error) {
    discoveryError.value = getErrorMessage(error)
    discoveryMessage.value = discoveryError.value
  } finally {
    importing.value = false
  }
}

async function batchCheckDevices() {
  checking.value = true
  try {
    const { resolveAgentAction } = await import('../../services/agent.service')
    await resolveAgentAction(await postAction('/app-testing/devices/batch-check', { ids: [] }))
    await resourcePage.value?.load()
  } finally {
    checking.value = false
  }
}

function toggleAllDiscovered() {
  selectedDeviceKeys.value = allImportableSelected.value ? [] : importableDevices.value.map(deviceKey)
}

function defaultSelectedDeviceKeys(devices: DiscoveredDevice[]) {
  const fresh = devices.filter(device => canImportDevice(device) && !device.exists)
  return (fresh.length ? fresh : devices.filter(canImportDevice)).map(deviceKey)
}

function canImportDevice(device: DiscoveredDevice) {
  return Boolean(device.platform && device.udid)
}

function deviceKey(device: DiscoveredDevice) {
  return `${device.platform || 'unknown'}:${device.udid || device.name || 'unknown'}`
}

function formFactorLabel(value: unknown) {
  return value === 'tablet' ? '平板' : value === 'phone' ? '手机' : '-'
}

function connectionStatusLabel(value: unknown) {
  const labels: Record<string, string> = {
    online: '在线',
    offline: '离线',
    busy: '占用',
    unknown: '未知'
  }
  return labels[String(value || '')] || String(value || '-')
}

function statusClass(device: DiscoveredDevice) {
  if (device.exists) return 'existing'
  return String(device.connection_status || 'unknown')
}

function warningText(device: DiscoveredDevice) {
  return Array.isArray(device.warnings) && device.warnings.length ? device.warnings.join('；') : device.source || ''
}

function getErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : '操作失败'
}
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 40;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgb(15 23 42 / 0.45);
}

.modal-panel {
  width: min(1120px, 96vw);
  max-height: 90vh;
  overflow: hidden;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 24px 80px rgb(15 23 42 / 0.28);
}

.modal-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 20px;
  border-bottom: 1px solid #e5e7eb;
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
}

.modal-header p {
  margin: 6px 0 0;
  color: #64748b;
}

.modal-close {
  border: 0;
  background: transparent;
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
}

.discovery-layout {
  display: grid;
  grid-template-columns: 280px 1fr;
  min-height: 560px;
}

.discovery-side {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 18px;
  border-right: 1px solid #e5e7eb;
  background: #f8fafc;
}

.setting-block {
  display: grid;
  gap: 10px;
}

.setting-block > span {
  font-weight: 700;
  color: #0f172a;
}

.setting-block label {
  display: grid;
  gap: 6px;
  color: #475569;
  font-size: 14px;
}

.setting-block input,
.setting-block select {
  width: 100%;
  min-height: 34px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 6px 8px;
  background: #fff;
}

.check-row {
  display: flex !important;
  align-items: center;
  gap: 8px !important;
}

.check-row input {
  width: auto;
  min-height: auto;
}

.tool-status p {
  display: flex;
  justify-content: space-between;
  margin: 0;
  color: #64748b;
}

.tool-status b {
  color: #b91c1c;
}

.tool-status b.ok {
  color: #047857;
}

.discovery-main {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 14px;
  padding: 18px;
}

.discovery-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.discovery-actions button,
.modal-panel button {
  min-height: 34px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 6px 12px;
  background: #fff;
  cursor: pointer;
}

.discovery-actions button:disabled,
.modal-panel button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.message {
  padding: 10px 12px;
  border: 1px solid #bfdbfe;
  border-radius: 6px;
  color: #1d4ed8;
  background: #eff6ff;
}

.message.error {
  border-color: #fecaca;
  color: #b91c1c;
  background: #fef2f2;
}

.summary-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  color: #475569;
}

.summary-row span {
  padding: 4px 8px;
  border-radius: 6px;
  background: #f1f5f9;
}

.device-table-wrap {
  overflow: auto;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.device-table-wrap table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.device-table-wrap th,
.device-table-wrap td {
  padding: 10px 12px;
  border-bottom: 1px solid #e5e7eb;
  text-align: left;
  vertical-align: top;
}

.device-table-wrap th {
  position: sticky;
  top: 0;
  background: #f8fafc;
}

.device-table-wrap strong {
  display: block;
}

.device-table-wrap small {
  display: block;
  margin-top: 4px;
  color: #64748b;
}

.check-column {
  width: 64px;
}

.mono {
  max-width: 240px;
  overflow-wrap: anywhere;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}

.muted {
  color: #94a3b8;
}

.status-pill {
  display: inline-flex;
  min-width: 52px;
  justify-content: center;
  border-radius: 999px;
  padding: 2px 8px;
  color: #475569;
  background: #f1f5f9;
}

.status-pill.online {
  color: #047857;
  background: #d1fae5;
}

.status-pill.offline {
  color: #b91c1c;
  background: #fee2e2;
}

.status-pill.existing {
  color: #1d4ed8;
  background: #dbeafe;
}

.empty-cell {
  height: 120px;
  color: #94a3b8;
  text-align: center !important;
}

@media (max-width: 860px) {
  .modal-backdrop {
    align-items: stretch;
    padding: 12px;
  }

  .discovery-layout {
    grid-template-columns: 1fr;
  }

  .discovery-side {
    border-right: 0;
    border-bottom: 1px solid #e5e7eb;
  }
}
</style>
