<template>
  <ResourcePage
    title="用例知识库"
    description="维护页面测试原则，并根据需求文档生成测试执行计划。"
    api-path="/project-knowledge"
    :fields="knowledgeFields"
    :columns="knowledgeColumns"
    :actions="actions"
    :search-params="searchParams"
    :defer-load="!projectReady"
    @custom-action="handleCustomAction"
  >
    <template #search-before-button>
      <select v-model="domainFilter" class="knowledge-domain-filter" aria-label="使用范围">
        <option value="">全部使用范围</option>
        <option v-for="option in domainOptions" :key="String(option.value)" :value="String(option.value)">
          {{ option.label }}
        </option>
      </select>
      <ProjectFilterSelect
        v-model="projectId"
        :include-all="false"
        @ready="projectReady = true"
      />
    </template>
  </ResourcePage>

  <KnowledgePlanGenerateDialog
    :open="generateDialogOpen"
    :project-id="projectId"
    @close="generateDialogOpen = false"
    @generated="handleGenerated"
  />
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import ResourcePage from '../../components/ResourcePage.vue'
import ProjectFilterSelect from '../../components/filters/ProjectFilterSelect.vue'
import KnowledgePlanGenerateDialog from '../../components/projects/KnowledgePlanGenerateDialog.vue'
import { knowledgeColumns, knowledgeFields } from '../../resourceSchemas'
import type { PageAction } from '../../types/page-actions'
import type { KnowledgePlanGenerationResult } from '../../types/knowledge'

const router = useRouter()
const projectId = ref(0)
const projectReady = ref(false)
const domainFilter = ref('')
const generateDialogOpen = ref(false)

const domainOptions = [
  { label: '通用', value: 'COMMON' },
  { label: 'Web', value: 'WEB' }
]

const searchParams = computed(() => ({
  project_id: projectId.value || undefined,
  domain: domainFilter.value || undefined
}))

const actions = computed<PageAction[]>(() => projectReady.value && projectId.value > 0 ? [
  {
    label: '初始化测试原则',
    path: '/project-knowledge/seed-defaults',
    payload: { project_id: projectId.value, overwrite: false },
    feedback: 'toast',
    successTitle: '初始化成功',
    successMessage: '八类测试原则已同步'
  },
  {
    label: '生成测试执行计划',
    name: 'generate-plan',
    path: '/project-knowledge/generate-plan',
    type: 'custom'
  }
] : [])

function handleCustomAction(action: PageAction) {
  if (action.name === 'generate-plan') {
    generateDialogOpen.value = true
  }
}

function handleGenerated(result: KnowledgePlanGenerationResult) {
  generateDialogOpen.value = false
  void router.push({
    path: `/execution/plans/${result.plan_id}`,
    query: { tab: 'MANUAL', generated: String(result.generated_case_count) }
  })
}
</script>

<style scoped>
.knowledge-domain-filter {
  flex: 0 0 132px;
  min-width: 132px;
}
</style>
