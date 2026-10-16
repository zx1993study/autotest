<template>
  <ResourcePage
    title="App 知识库"
    description="维护 App 自动化生成、执行和修复使用的项目知识。"
    api-path="/project-knowledge"
    :fields="appKnowledgeFields"
    :columns="appKnowledgeColumns"
    :search-params="searchParams"
    :default-values="defaultValues"
    :defer-load="!projectReady"
  >
    <template #search-before-button>
      <select v-model="kindFilter" class="knowledge-filter" aria-label="知识类型">
        <option value="">全部类型</option>
        <option v-for="option in kindOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
      </select>
      <ProjectFilterSelect
        v-model="projectId"
        :include-all="false"
        @ready="projectReady = true"
      />
    </template>
  </ResourcePage>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

import ResourcePage from '../../components/ResourcePage.vue'
import ProjectFilterSelect from '../../components/filters/ProjectFilterSelect.vue'
import { appKnowledgeColumns, appKnowledgeFields } from '../../resourceSchemas'

const projectId = ref(0)
const projectReady = ref(false)
const kindFilter = ref('')

const kindOptions = [
  { label: '失败经验', value: 'app_failure_lesson' },
  { label: '定位策略', value: 'locator_strategy' },
  { label: '弹窗处理', value: 'popup_handling' },
  { label: '等待策略', value: 'wait_strategy' },
  { label: '输入规则', value: 'input_rule' },
  { label: '业务规则', value: 'business_rule' },
  { label: '设备特征', value: 'device_trait' }
]

const searchParams = computed(() => ({
  project_id: projectId.value || undefined,
  domain: 'APP',
  kind: kindFilter.value || undefined
}))

const defaultValues = computed(() => ({
  project_id: projectId.value || undefined,
  data: {
    domain: 'APP',
    kind: kindFilter.value || 'app_failure_lesson'
  }
}))
</script>

<style scoped>
.knowledge-filter {
  flex: 0 0 156px;
  min-width: 156px;
}
</style>
