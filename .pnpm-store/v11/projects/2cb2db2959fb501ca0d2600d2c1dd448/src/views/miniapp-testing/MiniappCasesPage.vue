<template>
  <TestCasePage
    title="小程序正式用例"
    description="管理可通过 Appium 宿主应用和 WebView 上下文执行的小程序正式用例。"
    api-path="/miniapp-testing/cases"
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
    label: '执行选中小程序用例',
    path: '/miniapp-testing/cases/run',
    selectedKey: 'case_ids',
    payload: { mode: ExecutionMode.LOCAL_APPIUM }
  }
]

const rowActions = [
  {
    label: '执行',
    path: '/miniapp-testing/cases/run',
    payload: { case_ids: ['$id'], project_id: '$project_id', mode: ExecutionMode.LOCAL_APPIUM }
  }
]
</script>
