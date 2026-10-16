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
    :defer-load="deferLoad"
    :allow-create="false"
    :allow-edit="true"
    detail-mode="test-case"
    @custom-action="forwardCustomAction"
  >
    <template #search-before-button>
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
import type { ResourceItem } from '../types/resource'
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
  deferLoad?: boolean
}>()

const emit = defineEmits<{
  (event: 'customAction', action: PageAction, item?: ResourceItem, payload?: Record<string, unknown>): void
}>()

function forwardCustomAction(action: PageAction, item?: ResourceItem, payload?: Record<string, unknown>) {
  emit('customAction', action, item, payload)
}
</script>
