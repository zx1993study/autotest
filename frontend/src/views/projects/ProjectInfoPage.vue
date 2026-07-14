<template>
  <ResourcePage
    title="项目信息"
    description="管理项目基础信息、测试环境、负责人和项目状态。"
    api-path="/projects"
    :fields="projectInfoFields"
    :columns="projectInfoColumns"
  />
</template>

<script setup lang="ts">
import ResourcePage from '../../components/ResourcePage.vue'
import { projectInfoColumns, projectInfoFields } from '../../resourceSchemas'
</script>
