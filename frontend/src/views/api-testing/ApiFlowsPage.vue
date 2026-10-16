<template>
  <ResourcePage title="API 功能管理" description="" api-path="/execution/flows" :fields="executionFlowFields" :columns="columns" :row-actions="actions" :initial-params="params" :defer-load="!ready">
    <template #search-before-button><ProjectFilterSelect v-model="projectId" @ready="ready = true" /></template>
  </ResourcePage>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import ResourcePage from '../../components/ResourcePage.vue'
import ProjectFilterSelect from '../../components/filters/ProjectFilterSelect.vue'
import { executionFlowFields } from '../../resource-schemas/execution'
import type { ResourceColumn } from '../../types/resource-schema'
import type { PageAction } from '../../types/page-actions'
const projectId = ref(0)
const ready = ref(false)
const params = computed(() => projectId.value ? {project_id: projectId.value} : {})
const columns: ResourceColumn[] = [{key: 'name', label: '流程名称'}, {key: 'project_id', label: '项目 ID'}, {key: 'data.node_count', label: '节点数'}, {key: 'data.scenario_count', label: '场景数'}, {key: 'data.latest_status', label: '最近运行'}, {key: 'description', label: '备注'}, {key: 'updated_at', label: '更新时间'}]
const actions: PageAction[] = [{label: '详情', path: '/api/flows/{id}', type: 'route'}, {label: '复制', path: '/execution/flows/{id}/copy', type: 'request', reload: true, feedback: 'toast', successMessage: '流程已复制'}]
</script>
