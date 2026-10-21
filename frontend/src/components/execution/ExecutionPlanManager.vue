<template>
  <section class="execution-plan-manager">
    <header class="page-header">
      <div>
        <h2>执行计划</h2>
        <p>按项目配置 API 与 Web 功能范围，并生成可执行测试内容。</p>
      </div>
      <button type="button" class="primary" :disabled="!projectReady || !projectId" @click="openCreate">新增</button>
    </header>

    <div v-if="toastVisible" class="operation-toast" role="status" aria-live="polite">
      <strong>操作成功</strong>
      <span>{{ toastMessage }}</span>
    </div>

    <div class="toolbar">
      <input class="plan-search-input" v-model.trim="keyword" placeholder="搜索执行计划名称/备注" @keyup.enter="search" />
      <ProjectFilterSelect
        v-model="projectId"
        :include-all="false"
        @ready="handleProjectReady"
      />
      <button type="button" :disabled="loading" @click="search">查询</button>
      <button type="button" :disabled="!selectedIds.length || loading" @click="removeSelected">{{ deleting ? '删除中...' : '批量删除' }}</button>
    </div>

    <p v-if="errorMessage" class="form-error">{{ errorMessage }}</p>
    <div class="table-wrap" :aria-busy="loading">
      <table>
        <thead>
          <tr>
            <th class="check-column"><input type="checkbox" :checked="allChecked" @change="toggleAll" /></th>
            <th>执行计划名称</th>
            <th>API 数量</th>
            <th>Web 功能数量</th>
            <th>备注</th>
            <th>创建时间</th>
            <th class="actions-column">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading"><td colspan="7" class="empty-cell">正在加载...</td></tr>
          <tr v-for="item in plans" v-else :key="item.id">
            <td><input v-model="selectedIds" type="checkbox" :value="item.id" /></td>
            <td>{{ item.name }}</td>
            <td>{{ item.api_count }}</td>
            <td>{{ item.web_feature_count }}</td>
            <td>{{ item.description || '-' }}</td>
            <td>{{ formatTime(item.created_at) }}</td>
            <td class="row-actions">
              <button type="button" @click="openDetail(item.id)">详情</button>
              <button type="button" @click="openEdit(item)">编辑</button>
              <button type="button" class="danger" @click="removeOne(item)">删除</button>
            </td>
          </tr>
          <tr v-if="!loading && !errorMessage && !plans.length"><td colspan="7" class="empty-cell">暂无执行计划</td></tr>
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

    <ExecutionPlanFormDialog
      :open="dialogOpen"
      :plan="editingPlan"
      :project-id="projectId"
      :saving="saving"
      :error="formError"
      @close="closeDialog"
      @save="savePlan"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import {
  batchDeleteExecutionPlans,
  createExecutionPlan,
  deleteExecutionPlan,
  listExecutionPlans,
  updateExecutionPlan
} from '../../services/execution-plan.service'
import type { ExecutionPlanInfo, ExecutionPlanSavePayload } from '../../types/execution-plan'
import CommonPagination from '../common/CommonPagination.vue'
import ProjectFilterSelect from '../filters/ProjectFilterSelect.vue'
import ExecutionPlanFormDialog from './ExecutionPlanFormDialog.vue'
import { useLatestRequest } from '../../composables/useLatestRequest'

const router = useRouter()
const projectId = ref(0)
const projectReady = ref(false)
const keyword = ref('')
const plans = ref<ExecutionPlanInfo[]>([])
const selectedIds = ref<number[]>([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const { loading: listLoading, error: errorMessage, run: loadRequest, cancel: cancelLoad } = useLatestRequest('执行计划加载失败')
const deleting = ref(false)
const loading = computed(() => listLoading.value || deleting.value)
const saving = ref(false)
const formError = ref('')
const dialogOpen = ref(false)
const editingPlan = ref<ExecutionPlanInfo | null>(null)
const toastVisible = ref(false)
const toastMessage = ref('')
let toastTimer: ReturnType<typeof window.setTimeout> | undefined

const allChecked = computed(() => plans.value.length > 0 && selectedIds.value.length === plans.value.length)

watch([projectId, projectReady], () => {
  if (!projectReady.value) return
  page.value = 1
  plans.value = []; total.value = 0; selectedIds.value = []
  void loadPlans()
})

onBeforeUnmount(() => {
  if (toastTimer) window.clearTimeout(toastTimer)
})

async function loadPlans() {
  if (!projectId.value) { cancelLoad(); return }
  await loadRequest(signal => listExecutionPlans({
      keyword: keyword.value || undefined,
      project_id: projectId.value,
      page: page.value,
      pageSize: pageSize.value
    }, signal), result => {
    plans.value = result.items
    total.value = result.total
    page.value = result.page
    selectedIds.value = []
  })
}

function handleProjectReady() {
  projectReady.value = true
}

function search() {
  page.value = 1
  void loadPlans()
}

function handlePaginationChange(nextPage: number, nextPageSize: number) {
  page.value = nextPage
  pageSize.value = nextPageSize
  void loadPlans()
}

function openCreate() {
  editingPlan.value = null
  formError.value = ''
  dialogOpen.value = true
}

function openEdit(plan: ExecutionPlanInfo) {
  editingPlan.value = plan
  formError.value = ''
  dialogOpen.value = true
}

function closeDialog() {
  if (!saving.value) dialogOpen.value = false
}

async function savePlan(payload: ExecutionPlanSavePayload) {
  saving.value = true
  formError.value = ''
  try {
    if (editingPlan.value) {
      await updateExecutionPlan(editingPlan.value.id, payload)
      showToast('执行计划已更新')
    } else {
      await createExecutionPlan(payload)
      showToast('执行计划已新增')
    }
    dialogOpen.value = false
    await loadPlans()
  } catch (error) {
    formError.value = errorText(error, '执行计划保存失败')
  } finally {
    saving.value = false
  }
}

async function removeOne(plan: ExecutionPlanInfo) {
  if (deleting.value) return
  if (!window.confirm(`确认删除执行计划“${plan.name}”吗？`)) return
  await runDelete(async () => { await deleteExecutionPlan(plan.id); return 1 }, '执行计划已删除')
}

async function removeSelected() {
  if (deleting.value || !selectedIds.value.length) return
  if (!window.confirm(`确认删除选中的 ${selectedIds.value.length} 条执行计划吗？`)) return
  const ids = [...selectedIds.value]
  await runDelete(async () => (await batchDeleteExecutionPlans(ids)).deleted_count, '选中的执行计划已删除')
}

async function runDelete(action: () => Promise<number>, message: string) {
  if (deleting.value) return
  const origin = projectId.value
  deleting.value = true
  errorMessage.value = ''
  try {
    const count = await action()
    if (origin !== projectId.value) return
    page.value = Math.min(page.value, Math.max(1, Math.ceil(Math.max(0, total.value - count) / pageSize.value)))
    showToast(message)
    await loadPlans()
  } catch (error) {
    if (origin === projectId.value) errorMessage.value = errorText(error, '执行计划删除失败')
  } finally {
    deleting.value = false
  }
}

function toggleAll(event: Event) {
  selectedIds.value = (event.target as HTMLInputElement).checked
    ? plans.value.map(item => item.id)
    : []
}

function openDetail(planId: number) {
  void router.push(`/execution/plans/${planId}`)
}

function showToast(message: string) {
  toastMessage.value = message
  toastVisible.value = true
  if (toastTimer) window.clearTimeout(toastTimer)
  toastTimer = window.setTimeout(() => { toastVisible.value = false }, 3000)
}

function formatTime(value: string) {
  return value ? value.replace('T', ' ') : '-'
}

function errorText(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback
}
</script>

<style scoped src="./execution-plan-manager.css"></style>
