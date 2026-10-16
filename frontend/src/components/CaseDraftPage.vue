<template>
  <ResourcePage
    ref="resourcePage"
    :title="title"
    :description="description"
    :api-path="apiPath"
    :actions="actions"
    :row-actions="rowActions"
    :fields="fields"
    :columns="columns"
    :initial-params="initialParams"
    :defer-load="deferLoad"
    detail-mode="case-draft"
    @custom-action="handleCustomAction"
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
import { ref } from 'vue'

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
  customAction: [action: PageAction, item?: ResourceItem]
}>()

const resourcePage = ref<InstanceType<typeof ResourcePage> | null>(null)

function handleCustomAction(action: PageAction, item?: ResourceItem) {
  emit('customAction', action, item)
}

async function load() {
  await resourcePage.value?.load()
}

defineExpose({ load })
</script>
