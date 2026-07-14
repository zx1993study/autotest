<template>
  <ResourcePage
    title="Web 元素信息"
    description="维护输入框、按钮、下拉框、弹窗、表格等页面元素。"
    api-path="/web-testing/elements"
    :fields="webElementFields"
    :columns="webElementColumns"
    :initial-params="initialParams"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import ResourcePage from '../../components/ResourcePage.vue'
import { webElementColumns, webElementFields } from '../../resourceSchemas'

const route = useRoute()

const initialParams = computed(() => {
  const params: Record<string, string> = {}
  const pageId = firstValue(route.query.page_id)
  const projectId = firstValue(route.query.project_id)
  if (pageId) {
    params.page_id = pageId
  }
  if (projectId) {
    params.project_id = projectId
  }
  return params
})

function firstValue(value: unknown): string {
  if (Array.isArray(value)) {
    return String(value[0] || '')
  }
  return value == null ? '' : String(value)
}
</script>
