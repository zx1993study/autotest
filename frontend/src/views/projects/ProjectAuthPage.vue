<template>
  <ResourcePage
    title="项目鉴权"
    description="管理 Token、Cookie、API Key、登录用例刷新等项目鉴权配置。"
    api-path="/project-auth"
    :fields="projectAuthFields"
    :columns="projectAuthColumns"
    :row-actions="rowActions"
  />
</template>

<script setup lang="ts">
import ResourcePage from '../../components/ResourcePage.vue'
import { projectAuthColumns, projectAuthFields } from '../../resourceSchemas'
import type { PageAction } from '../../types/page-actions'

const rowActions: PageAction[] = [
  {
    label: '刷新',
    path: '/project-auth/{id}/refresh',
    payload: {
      mode: 'local_headless'
    },
    disabledWhen: {
      key: 'status',
      value: ['disabled', 'archived']
    }
  }
]
</script>
