<template>
  <TestCasePage
    title="App 正式用例"
    description="管理可在本地或远程设备执行的 App 用例。"
    api-path="/app-testing/cases"
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
    label: '执行选中 App 用例',
    path: '/app-testing/cases/run',
    selectedKey: 'case_ids',
    payload: { mode: ExecutionMode.LOCAL_APPIUM }
  }
]

const rowActions = [
  {
    label: '执行',
    path: '/app-testing/cases/run',
    payload: { case_ids: ['$id'], project_id: '$project_id', mode: ExecutionMode.LOCAL_APPIUM }
  }
]
</script>
