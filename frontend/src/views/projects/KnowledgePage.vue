<template>
  <ResourcePage
    title="用例知识库"
    description="沉淀字段规则、异常场景、边界策略和流程模板。"
    api-path="/project-knowledge"
    :fields="knowledgeFields"
    :columns="knowledgeColumns"
    :actions="actions"
  />
</template>

<script setup lang="ts">
import ResourcePage from '../../components/ResourcePage.vue'
import { knowledgeColumns, knowledgeFields } from '../../resourceSchemas'

const actions = [
  {
    label: '初始化策略/模板',
    path: '/project-knowledge/seed-defaults',
    payload: { project_id: null, overwrite: false }
  }
]
</script>
