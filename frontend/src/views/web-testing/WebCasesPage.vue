<template>
  <TestCasePage
    title="Web 正式用例"
    description="管理 Playwright 可执行的 Web 正式用例。"
    api-path="/web-testing/cases"
    :actions="actions"
    :row-actions="rowActions"
    :fields="testCaseFields"
    :columns="testCaseColumns"
  />
</template>

<script setup lang="ts">
import TestCasePage from '../../components/TestCasePage.vue'
import { ExecutionMode } from '../../constants/enums'
import { testCaseColumns, testCaseFields } from '../../resourceSchemas'

const actions = [
  {
    label: '执行选中 Web 用例',
    path: '/web-testing/cases/run',
    selectedKey: 'case_ids',
    payload: { mode: ExecutionMode.LOCAL_HEADLESS }
  }
]

const rowActions = [
  {
    label: '执行',
    path: '/web-testing/cases/run',
    payload: { case_ids: ['$id'], project_id: '$project_id', mode: ExecutionMode.LOCAL_HEADLESS }
  }
]
</script>
