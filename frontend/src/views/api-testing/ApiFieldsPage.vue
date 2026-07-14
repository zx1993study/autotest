<template>
  <ResourcePage
    title="字段信息"
    description="维护 query、header、path、body 字段规则和示例值。"
    api-path="/api-testing/fields"
    :actions="actions"
    :fields="apiFieldFields"
    :columns="apiFieldColumns"
    :initial-params="initialParams"
    :default-values="defaultValues"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import ResourcePage from '../../components/ResourcePage.vue'
import { apiFieldColumns, apiFieldFields } from '../../resourceSchemas'
import type { PageAction } from '../../types/page-actions'

const route = useRoute()
const interfaceId = computed(() => normalizeQueryValue(route.query.interface_id))
const projectId = computed(() => normalizeQueryValue(route.query.project_id))
const initialParams = computed(() => ({
  interface_id: interfaceId.value || undefined,
  project_id: projectId.value || undefined
}))
const defaultValues = computed(() => ({
  'data.interface_id': interfaceId.value || '',
  project_id: projectId.value || ''
}))

const actions: PageAction[] = [
  {
    label: '同步选中接口字段',
    path: '/api-testing/fields/sync',
    selectedKey: 'interface_ids',
    payload: { project_id: 1 }
  }
]

function normalizeQueryValue(value: unknown) {
  return Array.isArray(value) ? value[0] || '' : String(value || '')
}
</script>
