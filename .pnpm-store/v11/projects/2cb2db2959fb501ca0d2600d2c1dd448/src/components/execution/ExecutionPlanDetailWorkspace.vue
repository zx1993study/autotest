<template>
  <section class="plan-detail-workspace">
    <header class="page-header">
      <div>
        <button type="button" class="back-button" @click="emit('back')">返回</button>
        <h2>{{ detail?.plan.name || '执行计划详情' }}</h2>
        <p>{{ subtitle }}</p>
      </div>
      <button type="button" class="primary" :disabled="loading || generating || !detail" @click="generate">
        {{ generating ? '生成中...' : '生成执行计划' }}
      </button>
    </header>

    <div v-if="toastVisible" class="operation-toast" role="status" aria-live="polite">
      <strong>操作成功</strong><span>{{ toastMessage }}</span>
    </div>
    <p v-if="errorMessage" class="form-error">{{ errorMessage }}</p>
    <p v-if="loading" class="empty-state">正在加载执行计划详情...</p>

    <template v-if="detail && !loading">
      <ExecutionPlanRequirementPanel
        :requirement-title="detail.plan.requirement_title"
        :requirement-document="detail.plan.requirement_document"
      />
      <nav class="feature-tabs" aria-label="测试内容">
        <button v-for="tab in tabs" :key="tab.value" type="button" :class="{ active: activeType === tab.value }" @click="activeType = tab.value">
          {{ tab.label }} <span>{{ tab.count }}</span>
        </button>
      </nav>
      <section class="tab-toolbar">
        <div><strong>{{ activeLabel }}</strong><span>{{ activeGroup.features.length }} 个功能点，{{ activeCaseCount }} 条用例</span></div>
        <div>
          <button v-if="activeType === 'API' || activeType === 'WEB'" type="button" @click="openFeature(activeType)">
            {{ activeType === 'API' ? '批量添加 API 信息' : '批量添加 Web 功能' }}
          </button>
          <button v-if="activeType === 'MANUAL'" type="button" @click="manualDialogOpen = true">添加手动测试功能点</button>
          <button type="button" class="primary" :disabled="!canRun" @click="run">
            {{ executing ? '执行中...' : '一键执行' }}
          </button>
        </div>
      </section>
      <ExecutionPlanFeatureList :group="activeGroup" />
    </template>

    <ExecutionPlanFeatureDialog
      :open="featureDialogOpen"
      :initial-type="featureDialogType"
      :plan-id="planId"
      :project-id="detail?.plan.project_id || 0"
      @close="featureDialogOpen = false"
      @saved="handleSaved"
    />
    <ExecutionPlanManualDialog
      :open="manualDialogOpen"
      :plan-id="planId"
      @close="manualDialogOpen = false"
      @saved="handleSaved"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import {
  generateExecutionPlan,
  getExecutionPlanDetail,
  runExecutionPlan
} from '../../services/execution-plan.service'
import type { ExecutionPlanDetail, ExecutionPlanGroup } from '../../types/execution-plan'
import ExecutionPlanFeatureDialog from './ExecutionPlanFeatureDialog.vue'
import ExecutionPlanFeatureList from './ExecutionPlanFeatureList.vue'
import ExecutionPlanManualDialog from './ExecutionPlanManualDialog.vue'
import ExecutionPlanRequirementPanel from './ExecutionPlanRequirementPanel.vue'

type FeatureType = 'API' | 'WEB'
type DetailType = FeatureType | 'MANUAL' | 'APP'
const props = defineProps<{ planId: number }>()
const emit = defineEmits<{ back: [] }>()
const detail = ref<ExecutionPlanDetail | null>(null)
const loading = ref(false)
const generating = ref(false)
const executing = ref(false)
const errorMessage = ref('')
const activeType = ref<DetailType>('API')
const featureDialogOpen = ref(false)
const featureDialogType = ref<FeatureType>('API')
const manualDialogOpen = ref(false)
const toastVisible = ref(false)
const toastMessage = ref('')
let toastTimer: ReturnType<typeof window.setTimeout> | undefined

const subtitle = computed(() => detail.value
  ? `${detail.value.plan.api_count} 个 API，${detail.value.plan.web_feature_count} 个 Web 功能，${detail.value.summary.case_count} 条测试项`
  : '根据知识库、API 字段模板和 Web 元素生成测试内容。')
const tabs = computed(() => {
  const values: Array<{ value: DetailType; label: string; count: number }> = [
    { value: 'API', label: 'API 信息', count: caseCount(group('API')) },
    { value: 'WEB', label: 'Web 功能', count: caseCount(group('WEB')) },
    { value: 'MANUAL', label: '手动功能', count: caseCount(group('MANUAL')) }
  ]
  if (group('APP').features.length) values.splice(2, 0, { value: 'APP', label: 'App 功能', count: caseCount(group('APP')) })
  return values
})
const activeGroup = computed(() => group(activeType.value))
const activeLabel = computed(() => tabs.value.find(item => item.value === activeType.value)?.label || '测试内容')
const activeCaseCount = computed(() => caseCount(activeGroup.value))
const canRun = computed(() => {
  const value = detail.value
  return Boolean(value && value.summary.case_count && value.plan.status !== 'done' && value.summary.run_count < value.plan.test_rounds && !executing.value)
})

onMounted(load)
onBeforeUnmount(() => { if (toastTimer) window.clearTimeout(toastTimer) })

async function load() {
  if (!props.planId) {
    errorMessage.value = '执行计划 ID 不合法'
    return
  }
  loading.value = true
  errorMessage.value = ''
  try {
    detail.value = await getExecutionPlanDetail(props.planId)
    selectAvailableTab()
  } catch (error) {
    errorMessage.value = errorText(error, '执行计划详情加载失败')
  } finally {
    loading.value = false
  }
}

async function generate() {
  generating.value = true
  errorMessage.value = ''
  try {
    const result = await generateExecutionPlan(props.planId)
    detail.value = result.detail
    selectAvailableTab()
    showToast(`已生成 ${result.generated_case_count} 条测试用例`)
  } catch (error) {
    errorMessage.value = errorText(error, '执行计划生成失败')
  } finally {
    generating.value = false
  }
}

async function run() {
  executing.value = true
  errorMessage.value = ''
  try {
    detail.value = await runExecutionPlan(props.planId)
    showToast('一键执行已完成，结果已更新')
  } catch (error) {
    errorMessage.value = errorText(error, '一键执行失败')
  } finally {
    executing.value = false
  }
}

function openFeature(type: FeatureType) {
  featureDialogType.value = type
  featureDialogOpen.value = true
}

function handleSaved(value: ExecutionPlanDetail, message: string) {
  detail.value = value
  featureDialogOpen.value = false
  manualDialogOpen.value = false
  showToast(message)
}

function group(caseType: string): ExecutionPlanGroup {
  return detail.value?.groups.find(item => item.case_type === caseType) || { case_type: caseType, label: caseType, features: [] }
}

function caseCount(value: ExecutionPlanGroup) {
  return value.features.reduce((total, feature) => total + feature.cases.length, 0)
}

function selectAvailableTab() {
  if (!caseCount(group(activeType.value))) {
    activeType.value = detail.value?.plan.api_ids.length ? 'API' : 'WEB'
  }
}

function showToast(message: string) {
  toastMessage.value = message
  toastVisible.value = true
  if (toastTimer) window.clearTimeout(toastTimer)
  toastTimer = window.setTimeout(() => { toastVisible.value = false }, 3000)
}

function errorText(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback
}
</script>

<style scoped src="./execution-plan-detail-workspace.css"></style>
