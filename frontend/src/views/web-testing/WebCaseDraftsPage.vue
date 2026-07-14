<template>
  <CaseDraftPage
    title="Web 用例草稿"
    description="审核由页面功能和元素策略生成的 Web 用例。"
    api-path="/web-testing/case-drafts"
    :actions="actions"
    :row-actions="rowActions"
    :fields="caseDraftFields"
    :columns="caseDraftColumns"
    :initial-params="draftSearchParams"
  >
    <template #search-before-button>
      <div class="draft-status-tabs" role="tablist" aria-label="Web 用例草稿状态筛选">
        <button
          v-for="tab in draftStatusTabs"
          :key="tab.value || 'all'"
          type="button"
          role="tab"
          :aria-selected="activeStatus === tab.value"
          :class="{ active: activeStatus === tab.value }"
          @click="activeStatus = tab.value"
        >
          {{ tab.label }}
        </button>
      </div>
    </template>
  </CaseDraftPage>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import CaseDraftPage from '../../components/CaseDraftPage.vue'
import { CaseDraftStatus } from '../../constants/enums'
import { caseDraftColumns, caseDraftFields } from '../../resourceSchemas'

const draftStatusTabs = [
  { label: '待审核', value: CaseDraftStatus.DRAFT },
  { label: '已采纳', value: CaseDraftStatus.ACCEPTED },
  { label: '已废弃', value: CaseDraftStatus.REJECTED },
  { label: '全部', value: '' }
]

const activeStatus = ref<string>(CaseDraftStatus.DRAFT)
const draftSearchParams = computed<Record<string, unknown>>(() => (
  activeStatus.value ? { status: activeStatus.value } : {}
))

const actions = [
  {
    label: '按选中页面生成草稿',
    path: '/web-testing/case-drafts/generate',
    selectedKey: 'source_ids',
    payload: { project_id: 1, strategy: 'basic' }
  },
  {
    label: '采纳选中草稿',
    path: '/web-testing/case-drafts/accept',
    selectedKey: 'ids'
  }
]

const rowActions = [
  {
    label: '采纳',
    path: '/web-testing/case-drafts/{id}/accept',
    enabledWhen: { key: 'status', value: 'draft' }
  },
  {
    label: '驳回',
    path: '/web-testing/case-drafts/{id}/reject',
    payload: { review_comment: '手动驳回' },
    enabledWhen: { key: 'status', value: 'draft' }
  }
]
</script>

<style scoped>
.draft-status-tabs {
  display: inline-flex;
  flex: 0 0 auto;
  overflow: hidden;
  border: 1px solid #d8e0ef;
  border-radius: 8px;
  background: #f8fbff;
}

.draft-status-tabs button {
  height: 34px;
  border: 0;
  border-right: 1px solid #d8e0ef;
  background: transparent;
  color: #41506a;
  cursor: pointer;
  padding: 0 14px;
}

.draft-status-tabs button:last-child {
  border-right: 0;
}

.draft-status-tabs button.active {
  background: #2478ff;
  color: #fff;
}

@media (max-width: 720px) {
  .draft-status-tabs {
    width: 100%;
  }

  .draft-status-tabs button {
    flex: 1 1 0;
    padding: 0 8px;
  }
}
</style>
