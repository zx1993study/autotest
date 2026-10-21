<template>
  <ResourcePage
    title="执行记录"
    description="查看执行任务、步骤日志、截图、错误和附件。"
    api-path="/reports/records"
    :fields="reportRecordFields"
    :columns="reportRecordColumns"
    :initial-params="recordSearchParams"
    :defer-load="!projectFilterReady"
    :row-actions="recordActions"
    @custom-action="handleRecordAction"
  >
    <template #search-before-button>
      <ProjectFilterSelect v-model="selectedProjectId" @ready="projectFilterReady = true" />
      <select v-model="selectedStatus" class="status-filter" aria-label="按执行状态筛选">
        <option value="">全部状态</option>
        <option v-for="option in reportRecordStatusOptions" :key="option.value" :value="option.value">
          {{ option.label }}
        </option>
      </select>
    </template>
  </ResourcePage>
  <ExecutionRecordDetailDialog v-if="selectedRecordId !== null" :record-id="selectedRecordId" @close="selectedRecordId = null" />
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import ProjectFilterSelect from '../../components/filters/ProjectFilterSelect.vue'
import ResourcePage from '../../components/ResourcePage.vue'
import ExecutionRecordDetailDialog from '../../components/reports/ExecutionRecordDetailDialog.vue'
import type { PageAction } from '../../types/page-actions'
import type { ResourceItem } from '../../types/resource'
import { reportRecordColumns, reportRecordFields, reportRecordStatusOptions } from '../../resourceSchemas'

const selectedProjectId = ref(0)
const selectedStatus = ref('')
const projectFilterReady = ref(false)
const selectedRecordId = ref<number | null>(null)
const recordActions: PageAction[] = [{ label: '查看结果', path: '', type: 'custom', name: 'view-result' }]
function handleRecordAction(action: PageAction, item?: ResourceItem) {
  if (action.name === 'view-result' && item) selectedRecordId.value = item.id
}
const recordSearchParams = computed<Record<string, unknown>>(() => ({
  ...(selectedProjectId.value ? { project_id: selectedProjectId.value } : {}),
  ...(selectedStatus.value ? { status: selectedStatus.value } : {})
}))
</script>

<style scoped>
.status-filter {
  flex: 0 0 148px;
  width: 148px;
  min-width: 0;
  height: 34px;
}

@media (max-width: 720px) {
  .status-filter {
    flex: 1 1 auto;
    width: 100%;
  }
}
</style>
