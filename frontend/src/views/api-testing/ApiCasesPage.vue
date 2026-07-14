<template>
  <TestCasePage
    title="API 正式用例"
    description="管理已采纳 API 用例，支持单个、批量和计划执行。"
    api-path="/api-testing/cases"
    :actions="actions"
    :row-actions="rowActions"
    :fields="apiTestCaseFields"
    :columns="apiTestCaseColumns"
  />
</template>

<script setup lang="ts">
import TestCasePage from '../../components/TestCasePage.vue'
import { ExecutionMode } from '../../constants/enums'
import { apiTestCaseColumns, apiTestCaseFields } from '../../resourceSchemas'

const actions = [
  {
    label: '执行选中 API 用例',
    path: '/api-testing/cases/run',
    selectedKey: 'case_ids',
    payload: { mode: ExecutionMode.LOCAL_HEADLESS }
  }
]

const rowActions = [
  {
    label: '执行',
    path: '/api-testing/cases/run',
    payload: { case_ids: ['$id'], project_id: '$project_id', mode: ExecutionMode.LOCAL_HEADLESS }
  }
]
</script>
