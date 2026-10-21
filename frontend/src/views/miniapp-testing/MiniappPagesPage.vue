<template>
  <ResourcePage
    title="小程序页面功能"
    description=""
    api-path="/miniapp-testing/pages"
    :fields="miniappPageFields"
    :columns="miniappPageColumns"
  />
</template>

<script setup lang="ts">
import ResourcePage from '../../components/ResourcePage.vue'
import { miniappPageColumns, miniappPageFields } from '../../resourceSchemas'

</script>
