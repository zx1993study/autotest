<template>
  <ResourcePage
    title="执行流程"
    description="编排 API、Web、App 用例流程和变量传递。"
    api-path="/execution/flows"
    :fields="executionFlowFields"
    :columns="executionFlowColumns"
    :row-actions="rowActions"
  />
</template>

<script setup lang="ts">
import ResourcePage from '../../components/ResourcePage.vue'
import { executionFlowColumns, executionFlowFields } from '../../resourceSchemas'
import type { PageAction } from '../../types/page-actions'

const rowActions: PageAction[] = [
  {
    label: '详情',
    path: '/execution/flows/{id}',
    type: 'route'
  }
]
</script>
