<template>
  <ResourcePage
    title="项目信息"
    description="管理项目基础信息、测试环境、负责人和项目状态。"
    api-path="/projects"
    :fields="projectInfoFields"
    :columns="projectInfoColumns"
    :row-actions="rowActions"
  />
</template>

<script setup lang="ts">
import ResourcePage from '../../components/ResourcePage.vue'
import { projectInfoColumns, projectInfoFields } from '../../resourceSchemas'
import type { PageAction } from '../../types/page-actions'

const rowActions: PageAction[] = [
  {
    label: '默认',
    path: '/projects/{id}/set-default',
    feedback: 'toast',
    successTitle: '设置成功',
    successMessage: '默认项目已更新',
    activeWhen: {
      key: 'data.is_default',
      value: true
    }
  }
]
</script>
