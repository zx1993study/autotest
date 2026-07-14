<template>
  <ResourcePage
    :title="title"
    :description="description"
    :api-path="apiPath"
    :actions="actions"
    :row-actions="rowActions"
    :fields="fields"
    :columns="columns"
    :initial-params="initialParams"
    detail-mode="case-draft"
  >
    <template #toolbar-top>
      <slot name="search-before-button"></slot>
    </template>
    <template #search-actions>
      <slot name="search-actions"></slot>
    </template>
  </ResourcePage>
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
  initialParams?: Record<string, unknown>
}>()
</script>
