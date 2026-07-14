<template>
  <ResourcePage
    title="AI Prompt 模板"
    description="维护可复用的提示词模板，生成时由平台注入脱敏上下文和补充需求。"
    api-path="/ai/prompt-templates"
    :fields="aiPromptTemplateFields"
    :columns="aiPromptTemplateColumns"
  />
</template>

<script setup lang="ts">
import ResourcePage from '../../components/ResourcePage.vue'
import { aiPromptTemplateColumns, aiPromptTemplateFields } from '../../resourceSchemas'
</script>
