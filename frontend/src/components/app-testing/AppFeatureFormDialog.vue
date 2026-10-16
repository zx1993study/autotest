<template>
  <div class="modal-backdrop" @click.self="close">
    <section class="modal-panel" role="dialog" aria-modal="true" :aria-label="feature ? '编辑功能' : '新增功能'">
      <header class="modal-header">
        <h3>{{ feature ? '编辑功能' : '新增功能' }}</h3>
        <button class="modal-close" type="button" aria-label="关闭" @click="close">×</button>
      </header>
      <form class="modal-form" @submit.prevent="save">
        <div class="form-grid">
          <label class="field">
            <span>功能名称<b>*</b></span>
            <input v-model.trim="form.name" aria-label="功能名称" required placeholder="例如：登录、打卡、提交订单" />
          </label>
          <label class="field">
            <span>所属项目<b>*</b></span>
            <select v-model="form.project_id" aria-label="所属项目" required @change="loadDevices">
              <option value="">请选择项目</option>
              <option v-for="project in projects" :key="project.id" :value="String(project.id)">{{ project.name }}</option>
            </select>
          </label>
          <label class="field">
            <span>默认设备</span>
            <select v-model="form.default_device_id" aria-label="默认设备" :disabled="devicesLoading">
              <option value="">{{ devicesLoading ? '正在加载设备...' : '不指定' }}</option>
              <option v-for="device in devices" :key="device.id" :value="String(device.id)" :disabled="device.status === 'disabled'">{{ appDeviceOptionLabel(device) }}</option>
            </select>
            <span v-if="deviceError" class="form-error" role="alert">{{ deviceError }}<button type="button" title="重新加载设备" aria-label="重新加载设备" @click="loadDevices"><RefreshCw :size="14" /></button></span>
            <span v-else-if="!devicesLoading && !devices.length">设备池暂无设备</span>
          </label>
          <label class="field">
            <span>状态</span>
            <select v-model="form.status">
              <option value="active">启用</option>
              <option value="disabled">停用</option>
            </select>
          </label>
          <label class="field full">
            <span>功能说明</span>
            <textarea v-model.trim="form.description" rows="3" placeholder="说明这个功能覆盖的业务边界"></textarea>
          </label>
        </div>
        <p v-if="formError" class="form-error" role="alert">{{ formError }}</p>
        <footer class="modal-actions">
          <button type="button" @click="close">取消</button>
          <button type="submit" :disabled="saving || devicesLoading">{{ saving ? '保存中...' : '保存' }}</button>
        </footer>
      </form>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { RefreshCw } from 'lucide-vue-next'
import { createAppFeature, listDeviceOptions, updateAppFeature } from '../../services/app-feature.service'
import type { AppFeature } from '../../types/app-feature'
import type { SelectOptionRecord } from '../../types/resource'
import { appDeviceOptionLabel } from '../../utils/appDeviceOption'

const props = defineProps<{
  feature: AppFeature | null
  projects: SelectOptionRecord[]
  defaultProject: string
  defaultDevice: string
}>()
const emit = defineEmits<{ close: []; saved: [] }>()
const form = ref({
  name: props.feature?.name || '',
  project_id: props.feature?.project_id ? String(props.feature.project_id) : props.defaultProject,
  default_device_id: props.feature?.data?.default_device_id ? String(props.feature.data.default_device_id) : props.feature ? '' : props.defaultDevice,
  status: props.feature?.status || 'active',
  description: props.feature?.description || ''
})
const devices = ref<SelectOptionRecord[]>([])
const devicesLoading = ref(false)
const deviceError = ref('')
const saving = ref(false)
const formError = ref('')
let loadVersion = 0

onMounted(loadDevices)
onBeforeUnmount(() => { loadVersion++ })

async function loadDevices() {
  const version = ++loadVersion
  devicesLoading.value = true
  deviceError.value = ''
  try {
    const options = await listDeviceOptions(form.value.project_id)
    if (version !== loadVersion) return
    devices.value = options
    if (!options.some(d => String(d.id) === form.value.default_device_id)) form.value.default_device_id = ''
  } catch (error) {
    if (version !== loadVersion) return
    devices.value = []
    deviceError.value = error instanceof Error ? error.message : '设备加载失败'
  } finally {
    if (version === loadVersion) devicesLoading.value = false
  }
}

function close() {
  if (!saving.value) emit('close')
}

async function save() {
  formError.value = ''
  if (!form.value.name || !form.value.project_id) {
    formError.value = '请填写功能名称并选择项目'
    return
  }
  const selected = devices.value.find(d => String(d.id) === form.value.default_device_id)
  if (devicesLoading.value || (form.value.default_device_id && (!selected || selected.status === 'disabled'))) {
    formError.value = '请重新加载并选择有效设备'
    return
  }
  saving.value = true
  try {
    const payload = {
      name: form.value.name,
      project_id: Number(form.value.project_id),
      description: form.value.description || null,
      status: form.value.status,
      data: {
        default_device_id: form.value.default_device_id ? Number(form.value.default_device_id) : null,
        platforms: ['Android', 'iOS'],
        device_form_factors: ['phone', 'tablet']
      }
    }
    if (props.feature) await updateAppFeature(props.feature.id, payload)
    else await createAppFeature(payload)
    emit('saved')
  } catch (error) {
    formError.value = error instanceof Error ? error.message : '保存失败'
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.modal-backdrop { z-index: 1300; }
.form-error { overflow-wrap: anywhere; }
.form-error button { display: inline-flex; align-items: center; margin-left: 6px; }
</style>
