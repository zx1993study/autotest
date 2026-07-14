<template>
  <ResourcePage
    title="执行计划"
    description="配置单次、定时、周期执行计划和执行节点。"
    api-path="/execution/plans"
    :fields="executionPlanFields"
    :columns="executionPlanColumns"
  />
</template>

<script setup lang="ts">
import ResourcePage from '../../components/ResourcePage.vue'
import { executionPlanColumns, executionPlanFields } from '../../resourceSchemas'
</script>
