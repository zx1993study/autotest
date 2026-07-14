<template>
  <ResourcePage
    :title="title"
    :description="description"
    :api-path="apiPath"
    :actions="actions"
    :row-actions="rowActions"
    :fields="fields"
    :columns="columns"
    :allow-create="false"
    :allow-edit="false"
    detail-mode="test-case"
  />
</template>

<script setup lang="ts">
import ResourcePage from './ResourcePage.vue'
import type { PageAction } from '../types/page-actions'
import type { ResourceColumn, ResourceField } from '../types/resource-schema'

defineProps<{
  title: string
  description: string
  apiPath: string
  actions?: PageAction[]
  rowActions?: PageAction[]
  fields?: ResourceField[]
  columns?: ResourceColumn[]
}>()
</script>
