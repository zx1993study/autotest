<template>
  <ResourcePage
    title="App 页面功能"
    description="维护 App 页面、包名、Activity、设备和业务功能，支持设备页面采集。"
    api-path="/app-testing/pages"
    :actions="actions"
    :fields="appPageFields"
    :columns="appPageColumns"
  />
</template>

<script setup lang="ts">
import ResourcePage from '../../components/ResourcePage.vue'
import { appPageColumns, appPageFields } from '../../resourceSchemas'

const actions = [
  {
    label: '采集登录页面元素',
    path: '/app-testing/pages/scan',
    payload: {
      project_id: 1,
      feature: '登录',
      source: {}
    }
  }
]
</script>
