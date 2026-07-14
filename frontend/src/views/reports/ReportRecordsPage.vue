<template>
  <ResourcePage
    title="执行记录"
    description="查看执行任务、步骤日志、截图、错误和附件。"
    api-path="/reports/records"
    :fields="reportRecordFields"
    :columns="reportRecordColumns"
  />
</template>

<script setup lang="ts">
import ResourcePage from '../../components/ResourcePage.vue'
import { reportRecordColumns, reportRecordFields } from '../../resourceSchemas'
</script>
