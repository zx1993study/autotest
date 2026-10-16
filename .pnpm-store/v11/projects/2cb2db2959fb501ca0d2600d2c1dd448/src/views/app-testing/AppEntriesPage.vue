<template>
  <ResourcePage
    title="App 应用入口"
    description="配置设备里已有 App、当前前台 App 或小程序宿主入口，不要求上传安装包。"
    api-path="/app-testing/entries"
    :fields="appEntryFields"
    :columns="appEntryColumns"
  />
</template>

<script setup lang="ts">
import ResourcePage from '../../components/ResourcePage.vue'
import { appEntryColumns, appEntryFields } from '../../resourceSchemas'
</script>
