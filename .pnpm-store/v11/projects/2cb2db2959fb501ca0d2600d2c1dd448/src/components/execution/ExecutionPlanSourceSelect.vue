<template>
  <div class="source-picker-field">
    <button
      type="button"
      class="source-picker-trigger"
      :disabled="disabled"
      @click="openPicker"
    >
      <span :class="{ placeholder: !modelValue.length }">{{ selectedText }}</span>
      <span class="picker-open-icon" aria-hidden="true">...</span>
    </button>

    <div v-if="open" class="source-picker-backdrop" @click.self="closePicker">
      <section class="source-picker-modal" role="dialog" aria-modal="true" :aria-label="dialogTitle">
        <header class="source-picker-header">
          <div>
            <h3>{{ dialogTitle }}</h3>
            <p>点击列表行可选择多条数据，查询和翻页不会清空已选项。</p>
          </div>
          <button type="button" class="source-picker-close" aria-label="关闭" @click="closePicker">×</button>
        </header>

        <div class="source-picker-search">
          <input v-model.trim="keyword" :placeholder="searchPlaceholder" @keyup.enter="search" />
          <button type="button" :disabled="loading" @click="search">查询</button>
          <button type="button" :disabled="loading || (!keyword && !queryKeyword)" @click="resetSearch">重置</button>
          <span>已选择 {{ draftSelection.length }} 条</span>
        </div>

        <p v-if="errorMessage" class="picker-error">{{ errorMessage }}</p>
        <div class="source-picker-table-wrap">
          <table>
            <thead>
              <tr>
                <th class="check-column">
                  <input
                    type="checkbox"
                    :checked="allCurrentSelected"
                    :disabled="!rows.length"
                    aria-label="选择当前页"
                    @change="toggleCurrentPage"
                  />
                </th>
                <th>名称</th>
                <th>类型/方法</th>
                <th>地址/路径</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loading"><td colspan="4" class="empty-cell">正在加载...</td></tr>
              <tr
                v-for="row in rows"
                v-else
                :key="row.id"
                class="source-row"
                :class="{ selected: isSelected(row.id) }"
                @click="toggleRow(row.id)"
              >
                <td>
                  <input
                    type="checkbox"
                    :checked="isSelected(row.id)"
                    :aria-label="`选择${row.name}`"
                    @click.stop
                    @change="toggleRow(row.id)"
                  />
                </td>
                <td>{{ row.name }}</td>
                <td>{{ metaText(row) }}</td>
                <td>{{ pathText(row) }}</td>
              </tr>
              <tr v-if="!loading && !rows.length"><td colspan="4" class="empty-cell">暂无匹配数据</td></tr>
            </tbody>
          </table>
        </div>

        <CommonPagination
          :page="page"
          :page-size="pageSize"
          :total="total"
          :loading="loading"
          @change="handlePaginationChange"
        />

        <footer class="source-picker-actions">
          <button type="button" @click="closePicker">取消</button>
          <button type="button" class="primary" @click="confirmSelection">
            确认选择{{ draftSelection.length ? `（${draftSelection.length}）` : '' }}
          </button>
        </footer>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

import { listResources } from '../../services/resource.service'
import type { ResourceItem } from '../../types/resource'
import CommonPagination from '../common/CommonPagination.vue'

type SourceType = 'API' | 'WEB'

const props = withDefaults(defineProps<{
  modelValue: number[]
  projectId: number
  sourceType: SourceType
  disabled?: boolean
}>(), {
  disabled: false
})

const emit = defineEmits<{
  'update:modelValue': [value: number[]]
}>()

const open = ref(false)
const keyword = ref('')
const queryKeyword = ref('')
const rows = ref<ResourceItem[]>([])
const draftSelection = ref<number[]>([])
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)
const loading = ref(false)
const errorMessage = ref('')

const isApi = computed(() => props.sourceType === 'API')
const dialogTitle = computed(() => isApi.value ? '选择 API' : '选择 Web 功能')
const searchPlaceholder = computed(() => isApi.value ? '搜索 API 名称' : '搜索 Web 功能名称')
const selectedText = computed(() => props.modelValue.length
  ? `已选择 ${props.modelValue.length} 个${isApi.value ? ' API' : ' Web 功能'}`
  : `请选择${isApi.value ? ' API' : ' Web 功能'}`)
const allCurrentSelected = computed(() => rows.value.length > 0 && rows.value.every(row => isSelected(row.id)))

function openPicker() {
  if (props.disabled) return
  open.value = true
  keyword.value = ''
  queryKeyword.value = ''
  draftSelection.value = [...props.modelValue]
  page.value = 1
  void loadRows()
}

function closePicker() {
  open.value = false
  errorMessage.value = ''
}

function confirmSelection() {
  emit('update:modelValue', [...draftSelection.value])
  closePicker()
}

function search() {
  queryKeyword.value = keyword.value
  page.value = 1
  void loadRows()
}

function resetSearch() {
  keyword.value = ''
  queryKeyword.value = ''
  page.value = 1
  void loadRows()
}

function handlePaginationChange(nextPage: number, nextPageSize: number) {
  page.value = nextPage
  pageSize.value = nextPageSize
  void loadRows()
}

async function loadRows() {
  loading.value = true
  errorMessage.value = ''
  try {
    const result = await listResources(resourcePath(), {
      keyword: queryKeyword.value || undefined,
      project_id: props.projectId,
      page: page.value,
      pageSize: pageSize.value
    })
    rows.value = result.items
    total.value = result.total
    page.value = result.page
    pageSize.value = result.pageSize
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '列表加载失败'
  } finally {
    loading.value = false
  }
}

function toggleRow(rowId: number) {
  draftSelection.value = isSelected(rowId)
    ? draftSelection.value.filter(id => id !== rowId)
    : [...draftSelection.value, rowId]
}

function toggleCurrentPage(event: Event) {
  const currentIds = rows.value.map(row => row.id)
  draftSelection.value = (event.target as HTMLInputElement).checked
    ? Array.from(new Set([...draftSelection.value, ...currentIds]))
    : draftSelection.value.filter(id => !currentIds.includes(id))
}

function isSelected(rowId: number) {
  return draftSelection.value.includes(rowId)
}

function resourcePath() {
  return isApi.value ? '/api-testing/interfaces' : '/web-testing/pages'
}

function metaText(row: ResourceItem) {
  return format(readData(row, isApi.value ? 'method' : 'feature_type'))
}

function pathText(row: ResourceItem) {
  const value = isApi.value
    ? readData(row, 'path')
    : readData(row, 'route') || readData(row, 'url')
  return format(value)
}

function readData(row: ResourceItem, key: string) {
  return row.data && typeof row.data === 'object' ? row.data[key] : undefined
}

function format(value: unknown) {
  return value == null || value === '' ? '-' : String(value)
}
</script>

<style scoped src="./execution-plan-source-select.css"></style>
