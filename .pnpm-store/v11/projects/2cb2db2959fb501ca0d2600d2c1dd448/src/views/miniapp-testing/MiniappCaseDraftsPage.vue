<template>
  <CaseDraftPage
    title="小程序用例草稿"
    description="审核由小程序页面功能和元素策略生成的用例草稿。"
    api-path="/miniapp-testing/case-drafts"
    :actions="actions"
    :row-actions="rowActions"
    :fields="caseDraftFields"
    :columns="caseDraftColumns"
  />
</template>

<script setup lang="ts">
import CaseDraftPage from '../../components/CaseDraftPage.vue'
import { caseDraftColumns, caseDraftFields } from '../../resourceSchemas'

const actions = [
  {
    label: '按选中页面生成草稿',
    path: '/miniapp-testing/case-drafts/generate',
    selectedKey: 'source_ids',
    payload: { project_id: 1, strategy: 'basic' }
  },
  {
    label: '采纳选中草稿',
    path: '/miniapp-testing/case-drafts/accept',
    selectedKey: 'ids'
  }
]

const rowActions = [
  {
    label: '采纳',
    path: '/miniapp-testing/case-drafts/{id}/accept',
    enabledWhen: { key: 'status', value: 'draft' }
  },
  {
    label: '驳回',
    path: '/miniapp-testing/case-drafts/{id}/reject',
    payload: { review_comment: '手动驳回' },
    enabledWhen: { key: 'status', value: 'draft' }
  }
]
</script>
