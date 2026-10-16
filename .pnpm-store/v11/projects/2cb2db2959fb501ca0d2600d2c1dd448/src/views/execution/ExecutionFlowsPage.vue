<template>
  <ResourcePage
    title="执行流程"
    description="编排 API、Web、App 用例流程和变量传递。"
    api-path="/execution/flows"
    :fields="executionFlowFields"
    :columns="executionFlowColumns"
    :row-actions="rowActions"
    :initial-params="flowSearchParams"
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
import { executionFlowColumns, executionFlowFields } from '../../resourceSchemas'
import type { PageAction } from '../../types/page-actions'

const selectedProjectId = ref(0)
const projectFilterReady = ref(false)
const flowSearchParams = computed<Record<string, unknown>>(() => (
  selectedProjectId.value ? { project_id: selectedProjectId.value } : {}
))

const rowActions: PageAction[] = [
  {
    label: '详情',
    path: '/execution/flows/{id}',
    type: 'route'
  }
]
</script>
