<template>
  <ResourcePage
    title="字典信息"
    description="维护优先级、执行方式、元素类型、断言类型等公共字典。"
    api-path="/system/dictionaries"
    :fields="dictionaryFields"
    :columns="dictionaryColumns"
  />
</template>

<script setup lang="ts">
import ResourcePage from '../../components/ResourcePage.vue'
import { dictionaryColumns, dictionaryFields } from '../../resourceSchemas'
</script>
