<template>
  <section class="page app-feature-detail">
    <header class="page-header">
      <div>
        <button type="button" class="ghost-button" @click="router.push('/app/features')">返回功能清单</button>
        <h2>{{ feature?.name || 'App 功能详情' }}</h2>
      </div>
      <div class="header-actions">
        <button type="button" @click="openTextDialog">自然语言生成场景</button>
        <button type="button" @click="openRecordingDialog">开始操作生成脚本</button>
      </div>
    </header>

    <section class="summary-grid">
      <div>
        <span>场景数量</span>
        <strong>{{ feature?.scenario_count ?? 0 }}</strong>
      </div>
      <div>
        <span>最近结果</span>
        <strong>{{ formatStatus(feature?.last_run_status) }}</strong>
      </div>
      <div>
        <span>默认设备</span>
        <strong>{{ deviceName(readData(feature, 'default_device_id')) }}</strong>
      </div>
      <div>
        <span>更新时间</span>
        <strong>{{ feature?.updated_at || '-' }}</strong>
      </div>
    </section>

    <div class="toolbar feature-toolbar">
      <select v-model="filters.device_id" @change="search">
        <option value="">全部设备</option>
        <option v-for="device in devices" :key="device.id" :value="String(device.id)">{{ optionLabel(device) }}</option>
      </select>
      <select v-model="filters.source_type" @change="search">
        <option value="">全部来源</option>
        <option value="natural_language">自然语言</option>
        <option value="recording">录制</option>
        <option value="manual">手工</option>
      </select>
      <input v-model.trim="filters.keyword" placeholder="搜索场景名称/说明" @keyup.enter="search" />
      <button type="button" @click="search">查询</button>
    </div>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>场景名称</th>
            <th>来源</th>
            <th>默认设备</th>
            <th>步骤</th>
            <th>输入</th>
            <th>最近结果</th>
            <th>最近录屏</th>
            <th class="action-column">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="scenario in scenarios" :key="scenario.id" class="clickable-row" @click="goScenario(scenario.id)">
            <td>
              <strong>{{ scenario.name }}</strong>
              <small>{{ scenario.description || '-' }}</small>
            </td>
            <td>{{ sourceTypeLabel(scenario.source_type || readData(scenario, 'source_type')) }}</td>
            <td>{{ deviceName(readData(scenario, 'device_id')) }}</td>
            <td>{{ scenario.step_count ?? 0 }}</td>
            <td>{{ scenario.input_count ?? 0 }}</td>
            <td><span :class="['status-pill', statusClass(scenario.last_run_status)]">{{ formatStatus(scenario.last_run_status) }}</span></td>
            <td>
              <a v-if="scenario.last_video_url" :href="String(scenario.last_video_url)" target="_blank" @click.stop>查看录屏</a>
              <span v-else>-</span>
            </td>
            <td class="row-actions">
              <button type="button" @click.stop="goScenario(scenario.id)">查看场景</button>
            </td>
          </tr>
          <tr v-if="!scenarios.length">
            <td class="empty-cell" colspan="8">暂无场景，可使用自然语言或录制入口生成</td>
          </tr>
        </tbody>
      </table>
    </div>

    <CommonPagination
      :page="page"
      :page-size="pageSize"
      :total="total"
      :message="message"
      @change="handlePageChange"
    />

    <AppGenerationDialog v-if="feature" :visible="textDialogVisible" :feature="feature" @close="textDialogVisible = false" @saved="loadScenarios" />

    <div v-if="recordingDialogVisible" class="modal-backdrop" @click.self="closeRecordingDialog">
      <section class="modal-panel scenario-modal" role="dialog" aria-modal="true">
        <header class="modal-header">
          <h3>开始操作生成脚本</h3>
          <button class="modal-close" type="button" aria-label="关闭" @click="closeRecordingDialog">×</button>
        </header>
        <form class="modal-form" @submit.prevent="submitRecordingGeneration">
          <div class="form-grid">
            <label class="field">
              <span>操作名称<b>*</b></span>
              <input v-model.trim="recordingForm.name" required placeholder="例如：登录成功" />
            </label>
            <label class="field">
              <span>操作设备</span>
              <select v-model="recordingForm.device_id">
                <option value="">不指定</option>
                <option v-for="device in devices" :key="device.id" :value="String(device.id)">{{ optionLabel(device) }}</option>
              </select>
            </label>
            <label class="field full">
              <span>录制事件 JSON</span>
              <textarea v-model.trim="recordingForm.eventsJson" class="json-editor" rows="8" spellcheck="false" placeholder="可选；设备事件采集接入后会自动填充。为空时生成可编辑占位脚本。"></textarea>
            </label>
            <label class="check-row">
              <input v-model="recordingForm.record_video" type="checkbox" />
              执行时录制视频
            </label>
          </div>
          <p v-if="dialogError" class="form-error">{{ dialogError }}</p>
          <footer class="modal-actions">
            <button type="button" @click="closeRecordingDialog">取消</button>
            <button type="submit" :disabled="generating">{{ generating ? '生成中...' : '结束并生成脚本' }}</button>
          </footer>
        </form>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import CommonPagination from '../../components/common/CommonPagination.vue'
import AppGenerationDialog from '../../components/app-testing/AppGenerationDialog.vue'
import {
  generateAppScenarioFromRecording,
  getAppFeature,
  listAppFeatureScenarios,
  listDeviceOptions
} from '../../services/app-feature.service'
import type { AppFeature, AppFeatureScenario } from '../../types/app-feature'
import type { SelectOptionRecord } from '../../types/resource'

const route = useRoute()
const router = useRouter()
const featureId = Number(route.params.featureId)
const feature = ref<AppFeature | null>(null)
const scenarios = ref<AppFeatureScenario[]>([])
const devices = ref<SelectOptionRecord[]>([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const message = ref('')
const filters = ref({ device_id: '', source_type: '', keyword: '' })
const textDialogVisible = ref(false)
const recordingDialogVisible = ref(false)
const generating = ref(false)
const dialogError = ref('')
const recordingForm = ref({
  name: '',
  device_id: '',
  eventsJson: '',
  record_video: true
})

onMounted(async () => {
  await loadFeature()
  await loadDevices()
  await loadScenarios()
})

async function loadFeature() {
  feature.value = await getAppFeature(featureId)
}

async function loadDevices() {
  devices.value = await listDeviceOptions(feature.value?.project_id)
}

async function loadScenarios() {
  const result = await listAppFeatureScenarios(featureId, {
    ...filters.value,
    page: page.value,
    pageSize: pageSize.value
  })
  scenarios.value = result.items
  total.value = result.total
  page.value = result.page
  pageSize.value = result.pageSize
}

async function search() {
  page.value = 1
  await loadScenarios()
}

async function handlePageChange(nextPage: number, nextPageSize: number) {
  page.value = nextPage
  pageSize.value = nextPageSize
  await loadScenarios()
}

function openTextDialog() {
  textDialogVisible.value = true
}

function openRecordingDialog() {
  dialogError.value = ''
  recordingForm.value = {
    name: '',
    device_id: filters.value.device_id || '',
    eventsJson: '',
    record_video: true
  }
  recordingDialogVisible.value = true
}

function closeRecordingDialog() {
  if (!generating.value) recordingDialogVisible.value = false
}

async function submitRecordingGeneration() {
  dialogError.value = ''
  generating.value = true
  try {
    const events = parseEvents(recordingForm.value.eventsJson)
    const result = await generateAppScenarioFromRecording(featureId, {
      name: recordingForm.value.name,
      device_id: recordingForm.value.device_id ? Number(recordingForm.value.device_id) : null,
      events,
      record_video: recordingForm.value.record_video
    })
    recordingDialogVisible.value = false
    await Promise.all([loadFeature(), loadScenarios()])
    if (result.scenario?.id) {
      goScenario(result.scenario.id)
    }
  } catch (error) {
    dialogError.value = error instanceof Error ? error.message : '生成失败'
  } finally {
    generating.value = false
  }
}

function parseEvents(value: string) {
  if (!value.trim()) return []
  const parsed = JSON.parse(value) as unknown
  if (!Array.isArray(parsed)) {
    throw new Error('录制事件 JSON 必须是数组')
  }
  return parsed
}

function goScenario(scenarioId: number) {
  void router.push(`/app/features/${featureId}/scenarios/${scenarioId}`)
}

function optionLabel(option: SelectOptionRecord) {
  const data = isRecord(option.data) ? option.data : {}
  return [option.name, data.platform, data.device_form_factor, data.connection_status].filter(Boolean).join(' / ')
}

function deviceName(deviceId: unknown) {
  if (!deviceId) return '-'
  return devices.value.find(device => String(device.id) === String(deviceId))?.name || `设备 ${deviceId}`
}

function sourceTypeLabel(value: unknown) {
  const labels: Record<string, string> = {
    natural_language: '自然语言',
    recording: '录制',
    manual: '手工'
  }
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

function readData(item: AppFeature | AppFeatureScenario | null, key: string) {
  return item && isRecord(item.data) ? item.data[key] : undefined
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
  margin: 18px 0 6px;
}

.summary-grid div {
  border: 1px solid #edf1f7;
  border-radius: 8px;
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

.app-feature-detail small {
  display: block;
  margin-top: 4px;
  color: #7b879a;
}

.feature-toolbar {
  display: grid;
  grid-template-columns: minmax(180px, 1fr) minmax(160px, 0.9fr) minmax(260px, 2fr) auto;
  align-items: center;
  gap: 12px;
  margin: 18px 0 22px;
}

.feature-toolbar select,
.feature-toolbar input {
  min-width: 0;
  width: 100%;
}

.feature-toolbar button {
  min-width: 72px;
  height: 38px;
  white-space: nowrap;
}

@media (max-width: 860px) {
  .feature-toolbar {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .feature-toolbar input {
    grid-column: 1 / -1;
  }

  .feature-toolbar button {
    justify-self: start;
  }
}

@media (max-width: 640px) {
  .feature-toolbar {
    grid-template-columns: 1fr;
  }

  .feature-toolbar input {
    grid-column: auto;
  }

  .feature-toolbar button {
    width: 100%;
  }
}

.scenario-modal {
  width: min(820px, 100%);
}

.check-row {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #39465e;
}
</style>
