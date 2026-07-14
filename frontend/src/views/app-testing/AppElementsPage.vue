<template>
  <ResourcePage
    title="App 元素"
    description="维护 resource-id、text、content-desc、XPath 和坐标信息。"
    api-path="/app-testing/elements"
    :fields="appElementFields"
    :columns="appElementColumns"
  />
</template>

<script setup lang="ts">
import ResourcePage from '../../components/ResourcePage.vue'
import { appElementColumns, appElementFields } from '../../resourceSchemas'
</script>
