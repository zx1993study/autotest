<template>
  <ResourcePage
    title="小程序元素信息"
    description="维护小程序 WebView 和原生宿主中的元素定位、默认值和交互方式。"
    api-path="/miniapp-testing/elements"
    :fields="miniappElementFields"
    :columns="miniappElementColumns"
  />
</template>

<script setup lang="ts">
import ResourcePage from '../../components/ResourcePage.vue'
import { miniappElementColumns, miniappElementFields } from '../../resourceSchemas'
</script>
