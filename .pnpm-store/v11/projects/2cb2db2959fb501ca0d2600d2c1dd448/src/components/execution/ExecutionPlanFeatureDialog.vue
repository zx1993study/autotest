<template>
  <div v-if="open" class="modal-backdrop" @click.self="emit('close')">
    <section class="modal-panel" role="dialog" aria-modal="true">
      <header class="modal-header">
        <div>
          <h3>批量添加功能信息</h3>
          <p>关联正式用例会同步到当前执行计划。</p>
        </div>
        <button type="button" class="modal-close" aria-label="关闭" @click="emit('close')">×</button>
      </header>
      <div class="dialog-tabs">
        <button type="button" :class="{ active: type === 'API' }" @click="switchType('API')">API 信息</button>
        <button type="button" :class="{ active: type === 'WEB' }" @click="switchType('WEB')">Web 功能</button>
      </div>
      <div class="dialog-toolbar">
        <input v-model.trim="keyword" :placeholder="type === 'API' ? '搜索接口名称/路径' : '搜索页面功能名称'" @keyup.enter="search" />
        <button type="button" :disabled="loading" @click="search">查询</button>
      </div>
      <p v-if="errorMessage" class="form-error">{{ errorMessage }}</p>
      <div class="dialog-table">
        <table>
          <thead><tr><th><input type="checkbox" :checked="allChecked" @change="toggleAll" /></th><th>名称</th><th>类型/方法</th><th>地址/路径</th></tr></thead>
          <tbody>
            <tr v-if="loading"><td colspan="4" class="empty-cell">正在加载...</td></tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td><input v-model="selection" type="checkbox" :value="row.id" /></td>
              <td>{{ row.name }}</td>
              <td>{{ metaText(row) }}</td>
              <td>{{ pathText(row) }}</td>
            </tr>
            <tr v-if="!loading && !rows.length"><td colspan="4" class="empty-cell">暂无可选功能信息</td></tr>
          </tbody>
        </table>
      </div>
      <footer class="dialog-pager">
        <span>共 {{ total }} 条，第 {{ page }} / {{ totalPages }} 页</span>
        <div>
          <button type="button" :disabled="page <= 1 || loading" @click="load(1)">首页</button>
          <button type="button" :disabled="page <= 1 || loading" @click="load(page - 1)">上一页</button>
          <button type="button" :disabled="page >= totalPages || loading" @click="load(page + 1)">下一页</button>
          <button type="button" :disabled="page >= totalPages || loading" @click="load(totalPages)">末页</button>
        </div>
      </footer>
      <footer class="modal-actions">
        <span>已选择 {{ selection.length }} 项</span>
        <button type="button" @click="emit('close')">取消</button>
        <button type="button" class="primary" :disabled="!selection.length || saving" @click="submit">
          {{ saving ? '添加中...' : '添加' }}
        </button>
      </footer>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { addExecutionPlanFeatures } from '../../services/execution-plan.service'
import { listResources } from '../../services/resource.service'
import type { ExecutionPlanDetail } from '../../types/execution-plan'
import type { ResourceItem } from '../../types/resource'

type FeatureType = 'API' | 'WEB'
const props = defineProps<{ open: boolean; initialType: FeatureType; planId: number; projectId: number }>()
const emit = defineEmits<{ close: []; saved: [detail: ExecutionPlanDetail, message: string] }>()
const PAGE_SIZE = 10
const type = ref<FeatureType>('API')
const keyword = ref('')
const rows = ref<ResourceItem[]>([])
const selectionByType = ref<Record<FeatureType, number[]>>({ API: [], WEB: [] })
const page = ref(1)
const total = ref(0)
const loading = ref(false)
const saving = ref(false)
const errorMessage = ref('')

const selection = computed({
  get: () => selectionByType.value[type.value],
  set: value => { selectionByType.value = { ...selectionByType.value, [type.value]: value } }
})
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))
const allChecked = computed(() => rows.value.length > 0 && rows.value.every(row => selection.value.includes(row.id)))

watch(() => props.open, open => {
  if (!open) return
  type.value = props.initialType
  keyword.value = ''
  selectionByType.value = { API: [], WEB: [] }
  page.value = 1
  errorMessage.value = ''
  void load(1)
})

function switchType(value: FeatureType) {
  type.value = value
  keyword.value = ''
  void load(1)
}

function search() {
  void load(1)
}

async function load(nextPage: number) {
  loading.value = true
  errorMessage.value = ''
  page.value = Math.min(Math.max(nextPage, 1), totalPages.value)
  try {
    const path = type.value === 'API' ? '/api-testing/interfaces' : '/web-testing/pages'
    const result = await listResources(path, {
      keyword: keyword.value || undefined,
      project_id: props.projectId,
      page: page.value,
      pageSize: PAGE_SIZE
    })
    rows.value = result.items
    total.value = result.total
    page.value = result.page
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '功能信息加载失败'
  } finally {
    loading.value = false
  }
}

async function submit() {
  saving.value = true
  errorMessage.value = ''
  try {
    const detail = await addExecutionPlanFeatures(props.planId, {
      case_type: type.value,
      feature_ids: [...selection.value]
    })
    selectionByType.value = { ...selectionByType.value, [type.value]: [] }
    emit('saved', detail, '功能信息已添加，对应正式用例已同步')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '功能信息添加失败'
  } finally {
    saving.value = false
  }
}

function toggleAll(event: Event) {
  const ids = rows.value.map(row => row.id)
  selection.value = (event.target as HTMLInputElement).checked
    ? Array.from(new Set([...selection.value, ...ids]))
    : selection.value.filter(id => !ids.includes(id))
}

function metaText(row: ResourceItem) {
  return format(read(row, type.value === 'API' ? 'data.method' : 'data.feature_type'))
}

function pathText(row: ResourceItem) {
  if (type.value === 'API') return format(read(row, 'data.path'))
  return format(read(row, 'data.route') || read(row, 'data.url'))
}

function read(row: ResourceItem, path: string) {
  return path.split('.').reduce<unknown>((value, key) => value && typeof value === 'object' && key in value ? (value as Record<string, unknown>)[key] : undefined, row)
}

function format(value: unknown) {
  return value == null || value === '' ? '-' : String(value)
}
</script>

<style scoped src="./execution-plan-feature-dialog.css"></style>
