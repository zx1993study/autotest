<template>
  <ResourcePage
    title="执行记录"
    description="查看执行任务、步骤日志、截图、错误和附件。"
    api-path="/reports/records"
    :fields="reportRecordFields"
    :columns="reportRecordColumns"
    :initial-params="recordSearchParams"
    :defer-load="!projectFilterReady"
  >
    <template #search-before-button>
      <ProjectFilterSelect v-model="selectedProjectId" @ready="projectFilterReady = true" />
    </template>
  </ResourcePage>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import ProjectFilterSelect from '../../components/filters/ProjectFilterSelect.vue'
import ResourcePage from '../../components/ResourcePage.vue'
import { reportRecordColumns, reportRecordFields } from '../../resourceSchemas'

const selectedProjectId = ref(0)
const projectFilterReady = ref(false)
const recordSearchParams = computed<Record<string, unknown>>(() => (
  selectedProjectId.value ? { project_id: selectedProjectId.value } : {}
))
</script>
