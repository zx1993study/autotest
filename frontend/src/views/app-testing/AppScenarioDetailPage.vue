<template>
  <section class="page app-scenario-detail">
    <header class="page-header">
      <div>
        <button type="button" class="ghost-button" @click="router.push(`/app/features/${featureId}`)">返回场景列表</button>
        <h2>{{ scenario?.name || 'App 场景详情' }}</h2>
        <p v-if="scenario?.description">{{ scenario.description }}</p>
      </div>
      <div class="header-actions">
        <select v-model="runNodeKey" class="run-device-select" aria-label="执行节点">
          <option value="">设备绑定节点</option>
          <option v-for="node in mobileNodes" :key="node.id" :value="node.data.node_key">{{ node.name }}</option>
        </select>
        <select v-model="runDeviceId" class="run-device-select">
          <option value="">默认设备</option>
          <option v-for="device in devices" :key="device.id" :value="String(device.id)">{{ device.name }}</option>
        </select>
        <button type="button" @click="saveInputInfo" :disabled="savingInput">{{ savingInput ? '保存中...' : '保存输入信息' }}</button>
        <button type="button" @click="runScenario" :disabled="running">{{ running ? '执行中...' : '执行场景' }}</button>
      </div>
    </header>

    <section class="summary-grid">
      <div>
        <span>来源</span>
        <strong>{{ sourceTypeLabel(readData('source_type')) }}</strong>
      </div>
      <div>
        <span>默认设备</span>
        <strong>{{ deviceName(readData('device_id')) }}</strong>
      </div>
      <div>
        <span>步骤数量</span>
        <strong>{{ steps.length }}</strong>
      </div>
      <div>
        <span>输入字段</span>
        <strong>{{ inputEntries.length }}</strong>
      </div>
    </section>

    <section class="scenario-section">
      <header>
        <h3>操作步骤</h3>
      </header>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>序号</th>
              <th>动作</th>
              <th>步骤名称</th>
              <th>定位方式</th>
              <th>定位/坐标</th>
              <th>输入字段</th>
              <th>截图</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(step, index) in steps" :key="index">
              <td>{{ step.sort_order || index + 1 }}</td>
              <td>{{ step.action || '-' }}</td>
              <td>{{ step.name || '-' }}</td>
              <td>{{ step.locator_type || '-' }}</td>
              <td>{{ stepLocator(step) }}</td>
              <td>{{ step.input_key || '-' }}</td>
              <td>{{ step.take_screenshot ? '是' : '否' }}</td>
            </tr>
            <tr v-if="!steps.length">
              <td class="empty-cell" colspan="7">暂无步骤</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="scenario-section">
      <header>
        <h3>输入信息</h3>
      </header>
      <div v-if="inputEntries.length" class="input-grid">
        <label v-for="[key, item] in inputEntries" :key="key" class="field">
          <span>{{ inputLabel(key, item) }}</span>
          <DynamicValueInput
            v-model="inputValues[key]"
            :label="inputLabel(key, item)"
            :variables="scenarioVariables"
            :type="inputType(item)"
            :placeholder="key"
          />
        </label>
      </div>
      <p v-else class="empty-detail">当前场景没有抽取到可编辑输入字段。</p>
      <details class="named-variables">
        <summary>命名变量</summary>
        <label class="field"><span>变量定义 JSON</span><textarea v-model="variablesJson" class="json-editor" rows="4" aria-label="变量定义 JSON" spellcheck="false"></textarea></label>
      </details>
      <p v-if="inputMessage" class="input-message">{{ inputMessage }}</p>
    </section>

    <section class="scenario-section">
      <header>
        <h3>录屏 / 截图信息</h3>
      </header>
      <div v-if="latestRun" class="evidence-grid">
        <div class="evidence-video">
          <video v-if="latestVideoUrl" :src="latestVideoUrl" controls></video>
          <p v-else>暂无录屏</p>
        </div>
        <div class="evidence-meta">
          <dl>
            <div><dt>执行状态</dt><dd>{{ formatStatus(latestRun.status) }}</dd></div>
            <div><dt>执行设备</dt><dd>{{ latestRunData.device_name || deviceName(latestRunData.device_id) }}</dd></div>
            <div><dt>耗时</dt><dd>{{ latestRunData.duration_ms ?? '-' }} ms</dd></div>
            <div><dt>错误</dt><dd>{{ latestRunData.error || '-' }}</dd></div>
          </dl>
          <a v-if="latestScreenshotUrl" :href="latestScreenshotUrl" target="_blank">查看最后截图</a>
        </div>
      </div>
      <p v-else class="empty-detail">暂无执行记录。</p>
      <DynamicValueEvidence :snapshot="latestRunData.dynamic_values" />
    </section>

    <section class="scenario-section">
      <header>
        <h3>历史执行</h3>
      </header>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>状态</th>
              <th>设备</th>
              <th>耗时</th>
              <th>录屏</th>
              <th>错误</th>
              <th>时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="run in runs" :key="run.id">
              <td><span :class="['status-pill', statusClass(run.status)]">{{ formatStatus(run.status) }}</span></td>
              <td>{{ runData(run).device_name || deviceName(runData(run).device_id) }}</td>
              <td>{{ runData(run).duration_ms ?? '-' }} ms</td>
              <td>
                <a v-if="runData(run).video_url" :href="withScreenshotAccessToken(String(runData(run).video_url))" target="_blank">查看</a>
                <span v-else>-</span>
              </td>
              <td>{{ runData(run).error || '-' }}</td>
              <td>{{ run.created_at }}</td>
            </tr>
            <tr v-if="!runs.length">
              <td class="empty-cell" colspan="6">暂无历史执行</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { listAgentNodes } from '../../services/agent.service'
import type { AgentNode } from '../../types/agent'
import { withScreenshotAccessToken } from '../../utils/screenshotUrl'
import { useRoute, useRouter } from 'vue-router'
import DynamicValueInput from '../../components/common/DynamicValueInput.vue'
import DynamicValueEvidence from '../../components/common/DynamicValueEvidence.vue'
import { previewDynamicValue } from '../../services/dynamic-value.service'

import {
  getAppScenario,
  listAppScenarioRuns,
  listDeviceOptions,
  runAppScenario,
  updateAppScenario
} from '../../services/app-feature.service'
import type { AppFeatureScenario, AppScenarioRun } from '../../types/app-feature'
import type { SelectOptionRecord } from '../../types/resource'

const route = useRoute()
const router = useRouter()
const featureId = Number(route.params.featureId)
const scenarioId = Number(route.params.scenarioId)
const scenario = ref<AppFeatureScenario | null>(null)
const runs = ref<AppScenarioRun[]>([])
const devices = ref<SelectOptionRecord[]>([])
const inputValues = ref<Record<string, string>>({})
const variablesJson = ref('{}')
const savingInput = ref(false)
const running = ref(false)
const inputMessage = ref('')
const runDeviceId = ref('')
const runNodeKey = ref('')
const mobileNodes = ref<AgentNode[]>([])
let refreshTimer: ReturnType<typeof setTimeout> | undefined
let disposed = false
onUnmounted(() => { disposed = true; clearTimeout(refreshTimer) })

const steps = computed<Record<string, unknown>[]>(() => {
  const value = readData('operation_steps')
  return Array.isArray(value) ? value.filter(isRecord) : []
})

const inputInfo = computed<Record<string, unknown>>(() => {
  const value = readData('input_info')
  return isRecord(value) ? value : {}
})

const inputEntries = computed(() => Object.entries(inputInfo.value))
const scenarioVariables = computed(() => { try { const value = JSON.parse(variablesJson.value); return isRecord(value) ? value : {} } catch { return {} } })
const latestRun = computed(() => runs.value[0] || null)
const latestRunData = computed(() => latestRun.value ? runData(latestRun.value) : {})
const latestVideoUrl = computed(() => latestRunData.value.video_url ? withScreenshotAccessToken(String(latestRunData.value.video_url)) : '')
const latestScreenshotUrl = computed(() => latestRunData.value.screenshot_url ? withScreenshotAccessToken(String(latestRunData.value.screenshot_url)) : '')

onMounted(async () => {
  await loadScenario()
  await Promise.all([loadDevices(), loadRuns()])
  const nodes = await listAgentNodes({ pageSize: 100 })
  mobileNodes.value = nodes.items.filter(node => node.data.capabilities?.includes('app_execution'))
})

async function loadScenario() {
  scenario.value = await getAppScenario(scenarioId)
  variablesJson.value = JSON.stringify(readData('variables') || {}, null, 2)
  hydrateInputValues()
  runDeviceId.value = readData('device_id') ? String(readData('device_id')) : ''
}

async function loadDevices() {
  devices.value = await listDeviceOptions(scenario.value?.project_id)
}

async function loadRuns() {
  const result = await listAppScenarioRuns(scenarioId, 1, 20)
  runs.value = result.items
  clearTimeout(refreshTimer)
  if (!disposed && runs.value.some(run => ['queued', 'running'].includes(run.status))) {
    refreshTimer = setTimeout(() => { void loadRuns().catch(() => { inputMessage.value = '执行状态暂时无法更新，请检查平台连接' }) }, 3000)
  }
}

function hydrateInputValues() {
  const next: Record<string, string> = {}
  for (const [key, item] of Object.entries(inputInfo.value)) {
    if (isRecord(item)) {
      next[key] = String(item.value ?? item.default ?? '')
    } else {
      next[key] = String(item ?? '')
    }
  }
  inputValues.value = next
}

async function saveInputInfo() {
  savingInput.value = true
  inputMessage.value = ''
  try {
    const variables = parseVariables()
    await previewDynamicValue(inputValues.value, variables)
    scenario.value = await updateAppScenario(scenarioId, { input_info: buildInputInfoPayload(), variables })
    hydrateInputValues()
    inputMessage.value = '输入信息已保存'
  } catch (error) {
    inputMessage.value = error instanceof Error ? error.message : '保存失败'
  } finally {
    savingInput.value = false
  }
}

async function runScenario() {
  running.value = true
  inputMessage.value = ''
  try {
    const result = await runAppScenario(scenarioId, {
      node_id: runNodeKey.value || null,
      device_id: runDeviceId.value ? Number(runDeviceId.value) : readData('device_id') || null,
      input_info: inputValues.value,
      variables: parseVariables(),
      record_video: readData('record_video') !== false
    })
    await Promise.all([loadScenario(), loadRuns()])
    inputMessage.value = result.queued ? '已提交本地执行节点，结果将自动更新' : '执行完成，已刷新录屏/截图证据'
  } catch (error) {
    inputMessage.value = error instanceof Error ? error.message : '执行失败'
    await loadRuns()
  } finally {
    running.value = false
  }
}

function buildInputInfoPayload() {
  const payload: Record<string, unknown> = {}
  for (const [key, item] of Object.entries(inputInfo.value)) {
    payload[key] = isRecord(item) ? { ...item, value: inputValues.value[key] ?? '' } : { label: key, type: 'text', value: inputValues.value[key] ?? '' }
  }
  return payload
}

function parseVariables(): Record<string, unknown> {
  let parsed: unknown
  try { parsed = JSON.parse(variablesJson.value) } catch { throw new Error('变量定义不是合法 JSON') }
  if (!isRecord(parsed)) throw new Error('变量定义必须是 JSON 对象')
  return parsed
}

function readData(key: string) {
  return scenario.value && isRecord(scenario.value.data) ? scenario.value.data[key] : undefined
}

function runData(run: AppScenarioRun) {
  return isRecord(run.data) ? run.data : {}
}

function stepLocator(step: Record<string, unknown>) {
  const locator = step.locator || step.text || step.resource_id || step.xpath
  if (locator) return String(locator)
  const x = step.x_pct ?? step.x
  const y = step.y_pct ?? step.y
  return x || y ? `(${x ?? '-'}, ${y ?? '-'})` : '-'
}

function inputLabel(key: string, item: unknown) {
  return isRecord(item) ? String(item.label || key) : key
}

function inputType(item: unknown) {
  return isRecord(item) && item.type === 'password' ? 'password' : 'text'
}

function deviceName(deviceId: unknown) {
  if (!deviceId) return '-'
  return devices.value.find(device => String(device.id) === String(deviceId))?.name || `设备 ${deviceId}`
}

function sourceTypeLabel(value: unknown) {
  const labels: Record<string, string> = { natural_language: '自然语言', recording: '录制', manual: '手工' }
  return labels[String(value || '')] || '-'
}

function formatStatus(value: unknown) {
  const labels: Record<string, string> = { success: '成功', failed: '失败', active: '启用', disabled: '停用', queued: '排队中', running: '执行中' }
  return labels[String(value || '')] || '-'
}

function statusClass(value: unknown) {
  const status = String(value || '')
  return status === 'success' ? 'success' : status === 'failed' ? 'failed' : 'queued'
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}
</script>

<style scoped>
.header-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.run-device-select {
  min-width: 180px;
}

.ghost-button {
  margin-bottom: 8px;
  border-color: #d8e0ef;
  background: #ffffff;
  color: #42526c;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin: 18px 0;
}

.summary-grid div,
.scenario-section {
  border: 1px solid #edf1f7;
  border-radius: 8px;
  background: #ffffff;
}

.summary-grid div {
  background: #f8fbff;
  padding: 12px;
}

.summary-grid span {
  display: block;
  color: #7b879a;
  font-size: 12px;
}

.summary-grid strong {
  display: block;
  margin-top: 6px;
}

.scenario-section {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 12px;
  margin-top: 16px;
  padding: 16px;
}

.scenario-section header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
}

.scenario-section h3 {
  margin: 0;
}

.scenario-section small {
  color: #7b879a;
}

.input-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}

.input-message {
  margin: 0;
  color: #2368e8;
}

.evidence-grid {
  display: grid;
  grid-template-columns: minmax(280px, 1.2fr) minmax(240px, 0.8fr);
  gap: 16px;
}

.evidence-video {
  display: grid;
  place-items: center;
  min-height: 220px;
  border: 1px solid #edf1f7;
  border-radius: 8px;
  background: #101928;
  color: #ffffff;
}

.evidence-video video {
  width: 100%;
  max-height: 420px;
}

.evidence-meta dl {
  display: grid;
  gap: 10px;
  margin: 0 0 12px;
}

.evidence-meta div {
  border: 1px solid #edf1f7;
  border-radius: 6px;
  padding: 10px;
}

.evidence-meta dt {
  margin-bottom: 4px;
  color: #7b879a;
  font-size: 12px;
}

.evidence-meta dd {
  margin: 0;
  word-break: break-word;
}

.input-grid > .field, .named-variables, .evidence-meta, .table-wrap { min-width: 0; }
.named-variables .field { margin-top: 10px; }
.named-variables textarea { width: 100%; min-width: 0; }

@media (max-width: 760px) {
  .page-header { flex-wrap: wrap; }
  .page-header > div { min-width: 0; max-width: 100%; }
  .summary-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .evidence-grid { grid-template-columns: minmax(0, 1fr); }
  .input-grid { grid-template-columns: minmax(0, 1fr); }
}
</style>
