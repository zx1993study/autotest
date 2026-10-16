<template>
  <section class="page app-feature-page">
    <header class="page-header">
      <div>
        <h2>App 功能测试</h2>
      </div>
      <button type="button" @click="openCreateDialog">新增功能</button>
    </header>

    <div class="toolbar feature-toolbar">
      <select v-model="filters.project_id" @change="handleProjectChange">
        <option value="">全部项目</option>
        <option v-for="project in projects" :key="project.id" :value="String(project.id)">{{ project.name }}</option>
      </select>
      <select v-model="filters.device_id" :disabled="devicesLoading" @change="search">
        <option value="">全部设备</option>
        <option v-for="device in devices" :key="device.id" :value="String(device.id)">{{ optionLabel(device) }}</option>
      </select>
      <select v-model="filters.status" @change="search">
        <option value="">全部状态</option>
        <option value="active">启用</option>
        <option value="disabled">停用</option>
      </select>
      <input v-model.trim="filters.keyword" placeholder="搜索功能名称/说明" @keyup.enter="search" />
      <button type="button" :disabled="loading" @click="search">查询</button>
    </div>

    <p v-if="error || deviceError" role="alert">{{ error || deviceError }}</p>
    <div class="table-wrap" :aria-busy="loading">
      <table>
        <thead>
          <tr>
            <th>功能名称</th>
            <th>所属项目</th>
            <th>默认设备</th>
            <th>平台</th>
            <th>场景数</th>
            <th>最近结果</th>
            <th>更新时间</th>
            <th class="action-column">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="feature in features" :key="feature.id" class="clickable-row" @click="goDetail(feature.id)">
            <td>
              <strong>{{ feature.name }}</strong>
              <small>{{ feature.description || '-' }}</small>
            </td>
            <td>{{ projectName(feature.project_id) }}</td>
            <td>{{ deviceName(readDataNumber(feature, 'default_device_id')) }}</td>
            <td>{{ formatList(readData(feature, 'platforms')) }}</td>
            <td>{{ feature.scenario_count ?? readData(feature, 'scenario_count') ?? 0 }}</td>
            <td><span :class="['status-pill', statusClass(feature.last_run_status)]">{{ formatStatus(feature.last_run_status) }}</span></td>
            <td>{{ feature.updated_at || '-' }}</td>
            <td class="row-actions">
              <button type="button" @click.stop="goDetail(feature.id)">进入详情</button>
              <button type="button" @click.stop="openEditDialog(feature)">编辑</button>
              <button type="button" class="danger" @click.stop="deleteFeature(feature)">删除</button>
            </td>
          </tr>
          <tr v-if="loading"><td class="empty-cell" colspan="8">正在加载...</td></tr>
          <tr v-if="!loading && !error && !features.length">
            <td class="empty-cell" colspan="8">暂无功能，可先新增一个功能后生成测试场景</td>
          </tr>
        </tbody>
      </table>
    </div>

    <CommonPagination
      :page="page"
      :page-size="pageSize"
      :total="total"
      :loading="loading"
      :message="message"
      @change="handlePageChange"
    />

    <AppFeatureFormDialog v-if="dialogVisible" :feature="editingFeature" :projects="projects"
      :default-project="filters.project_id" :default-device="filters.device_id"
      @close="dialogVisible = false" @saved="handleFeatureSaved" />
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppFeatureFormDialog from '../../components/app-testing/AppFeatureFormDialog.vue'
import CommonPagination from '../../components/common/CommonPagination.vue'
import {
  deleteAppFeature,
  listAppFeatures,
  listDeviceOptions,
  listProjectOptions
} from '../../services/app-feature.service'
import type { AppFeature } from '../../types/app-feature'
import type { SelectOptionRecord } from '../../types/resource'
import { appDeviceOptionLabel as optionLabel } from '../../utils/appDeviceOption'
import { useLatestRequest } from '../../composables/useLatestRequest'

const router = useRouter()
const features = ref<AppFeature[]>([])
const projects = ref<SelectOptionRecord[]>([])
const devices = ref<SelectOptionRecord[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const message = ref('')
const { loading, error, run: loadRequest } = useLatestRequest('功能加载失败')
const { loading: devicesLoading, error: deviceError, run: loadDeviceRequest } = useLatestRequest('设备加载失败')
const dialogVisible = ref(false)
const editingFeature = ref<AppFeature | null>(null)
const filters = ref({
  project_id: '',
  device_id: '',
  status: '',
  keyword: ''
})

onMounted(async () => {
  try { await loadProjects(); await Promise.all([loadDevices(), loadFeatures()]) }
  catch (error) { message.value = error instanceof Error ? error.message : '加载失败' }
})

async function loadFeatures() {
  await loadRequest(signal => listAppFeatures({
    ...filters.value,
    page: page.value,
    pageSize: pageSize.value
  }, signal), result => {
    features.value = result.items
    total.value = result.total
    page.value = result.page
    pageSize.value = result.pageSize
  })
}

async function loadProjects() {
  projects.value = await listProjectOptions()
  if (!filters.value.project_id) {
    const defaultProject = projects.value.find(project => project.is_default || readOptionData(project, 'is_default')) || projects.value[0]
    if (defaultProject) {
      filters.value.project_id = String(defaultProject.id)
    }
  }
}

async function loadDevices() {
  devices.value = []
  await loadDeviceRequest(signal => listDeviceOptions(filters.value.project_id, signal), result => { devices.value = result })
}

async function handleProjectChange() {
  filters.value.device_id = ''
  features.value = []; total.value = 0
  await Promise.all([loadDevices(), search()])
}

async function search() {
  page.value = 1
  await loadFeatures()
}

async function handlePageChange(nextPage: number, nextPageSize: number) {
  page.value = nextPage
  pageSize.value = nextPageSize
  await loadFeatures()
}

function openCreateDialog() {
  editingFeature.value = null
  dialogVisible.value = true
}

function openEditDialog(feature: AppFeature) {
  editingFeature.value = feature
  dialogVisible.value = true
}

async function handleFeatureSaved() {
  dialogVisible.value = false
  try { await loadFeatures() }
  catch (error) { message.value = error instanceof Error ? error.message : '刷新失败' }
}

async function deleteFeature(feature: AppFeature) {
  if (!window.confirm(`确认删除功能「${feature.name}」及其场景？`)) return
  await deleteAppFeature(feature.id)
  await loadFeatures()
}

function goDetail(featureId: number) {
  void router.push(`/app/features/${featureId}`)
}

function projectName(projectId: unknown) {
  return projects.value.find(project => String(project.id) === String(projectId))?.name || '-'
}

function deviceName(deviceId: unknown) {
  if (!deviceId) return '-'
  return devices.value.find(device => String(device.id) === String(deviceId))?.name || `设备 ${deviceId}`
}

function readData(item: AppFeature, key: string) {
  return isRecord(item.data) ? item.data[key] : undefined
}

function readDataNumber(item: AppFeature, key: string) {
  const value = readData(item, key)
  return value == null || value === '' ? null : Number(value)
}

function readOptionData(option: SelectOptionRecord, key: string) {
  return isRecord(option.data) ? option.data[key] === true : false
}

function formatList(value: unknown) {
  return Array.isArray(value) ? value.join(' / ') : value || '-'
}

function formatStatus(value: unknown) {
  const labels: Record<string, string> = {
    success: '成功',
    failed: '失败',
    active: '启用',
    disabled: '停用',
    running: '执行中',
    queued: '排队中'
  }
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

<style scoped src="./app-features-page.css"></style>
