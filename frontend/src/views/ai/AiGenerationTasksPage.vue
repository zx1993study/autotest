<template>
  <section class="ai-task-page">
    <ResourcePage
      ref="resourcePageRef"
      title="AI 生成任务"
      description="查看 AI 生成过程、状态和保存结果，生成结果需要先进入草稿再人工审核。"
      api-path="/ai/tasks"
      :fields="aiGenerationTaskFields"
      :columns="aiGenerationTaskColumns"
      :row-actions="rowActions"
      @custom-action="handleCustomAction"
    >
      <template #search-actions>
        <button type="button" @click="refreshTasks">刷新</button>
      </template>
    </ResourcePage>

    <AiTaskDetailModal
      :visible="detailVisible"
      :loading="detailLoading"
      :error="detailError"
      :task="detailTask"
      @close="closeDetail"
    />
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { getResource, type ResourceItem } from '../../api/http'
import AiTaskDetailModal from '../../components/ai/AiTaskDetailModal.vue'
import ResourcePage from '../../components/ResourcePage.vue'
import { aiGenerationTaskColumns, aiGenerationTaskFields } from '../../resourceSchemas'
import type { PageAction } from '../../types/page-actions'

const resourcePageRef = ref<{ load: () => Promise<void> } | null>(null)
const detailVisible = ref(false)
const detailLoading = ref(false)
const detailError = ref('')
const detailTask = ref<ResourceItem | null>(null)

const rowActions: PageAction[] = [
  {
    label: '查看',
    path: '',
    type: 'custom',
    name: 'view'
  },
  {
    label: '执行',
    path: '/ai/tasks/{id}/execute',
    type: 'request',
    reload: true,
    pollTask: {
      path: '/ai/tasks',
      intervalMs: 3000,
      timeoutMs: 660000
    },
    disabledWhen: {
      key: 'status',
      value: ['running', 'queued']
    }
  }
]

async function refreshTasks() {
  await resourcePageRef.value?.load()
}

async function handleCustomAction(action: PageAction, item?: ResourceItem) {
  if (action.name !== 'view' || !item) {
    return
  }
  detailVisible.value = true
  detailLoading.value = true
  detailError.value = ''
  detailTask.value = item
  try {
    detailTask.value = await getResource('/ai/tasks', item.id)
  } catch (error) {
    detailError.value = getErrorMessage(error)
  } finally {
    detailLoading.value = false
  }
}

function closeDetail() {
  if (detailLoading.value) {
    return
  }
  detailVisible.value = false
}

function stringifyJson(value: unknown) {
  if (value == null || value === '') {
    return '-'
  }
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}
function getErrorMessage(error: unknown) {
  const responseData = (error as { response?: { data?: { message?: string; detail?: unknown } } }).response?.data
  if (responseData?.message) {
    return responseData.message
  }
  if (typeof responseData?.detail === 'string') {
    return responseData.detail
  }
  if (responseData?.detail) {
    return stringifyJson(responseData.detail)
  }
  return error instanceof Error ? error.message : '加载任务详情失败'
}
</script>

<style scoped>
.ai-task-page {
  display: grid;
  gap: 12px;
}
</style>

