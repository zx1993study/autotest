<template>
  <ResourcePage
    title="小程序页面功能"
    description="维护微信、企业微信、支付宝等小程序页面功能和 Appium WebView 执行配置。"
    api-path="/miniapp-testing/pages"
    :actions="actions"
    :fields="miniappPageFields"
    :columns="miniappPageColumns"
  />
</template>

<script setup lang="ts">
import ResourcePage from '../../components/ResourcePage.vue'
import { miniappPageColumns, miniappPageFields } from '../../resourceSchemas'

const actions = [
  {
    label: '采集登录页元素',
    path: '/miniapp-testing/pages/scan',
    payload: {
      project_id: 1,
      feature: '登录',
      source: {}
    }
  }
]
</script>
