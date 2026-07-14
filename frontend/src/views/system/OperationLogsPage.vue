<template>
  <ResourcePage
    title="用户操作日志"
    description="查看登录、导入、扫描、执行、删除等用户操作记录。"
    api-path="/system/operation-logs"
    :fields="operationLogFields"
    :columns="operationLogColumns"
  />
</template>

<script setup lang="ts">
import ResourcePage from '../../components/ResourcePage.vue'
import { operationLogColumns, operationLogFields } from '../../resourceSchemas'
</script>
