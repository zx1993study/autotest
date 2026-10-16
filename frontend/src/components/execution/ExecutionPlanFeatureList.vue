<template>
  <template v-if="group.features.length">
    <section class="feature-list">
      <article v-for="feature in pagedFeatures" :key="featureKey(feature)" class="feature-block">
        <header>
          <div>
            <h3>{{ feature.feature_name }}</h3>
            <span>{{ feature.cases.length }} 条测试用例</span>
          </div>
        </header>
        <div class="case-table-wrap">
          <table>
            <thead>
              <tr>
                <th>测试用例</th>
                <th>来源</th>
                <th>最近结果</th>
                <th>耗时</th>
                <th>异常/备注</th>
                <th>执行记录</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in feature.cases" :key="item.case_snapshot.id">
                <td>{{ item.case_snapshot.case_name }}</td>
                <td>{{ sourceText(item.case_snapshot) }}</td>
                <td><span :class="['status-pill', statusClass(item.latest_result?.status)]">{{ statusLabel(item.latest_result?.status) }}</span></td>
                <td>{{ formatDuration(item.latest_result?.duration_ms) }}</td>
                <td class="error-cell">{{ resultNote(item) }}</td>
                <td>{{ item.latest_result?.report_record_id ? `#${item.latest_result.report_record_id}` : '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </article>
    </section>
    <footer class="list-pager">
      <span>共 {{ featureCount }} 个功能点，{{ caseCount }} 条用例，第 {{ pageStart }}-{{ pageEnd }} 个功能点</span>
      <div>
        <button type="button" :disabled="page <= 1" @click="page = 1">首页</button>
        <button type="button" :disabled="page <= 1" @click="page--">上一页</button>
        <span>第 {{ page }} / {{ totalPages }} 页</span>
        <button type="button" :disabled="page >= totalPages" @click="page++">下一页</button>
        <button type="button" :disabled="page >= totalPages" @click="page = totalPages">末页</button>
      </div>
    </footer>
  </template>
  <p v-else class="empty-state">当前选项卡暂无内容。</p>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import type {
  ExecutionPlanCaseSnapshot,
  ExecutionPlanFeature,
  ExecutionPlanFeatureCase,
  ExecutionPlanGroup
} from '../../types/execution-plan'

const props = defineProps<{ group: ExecutionPlanGroup }>()
const PAGE_SIZE = 10
const page = ref(1)

const featureCount = computed(() => props.group.features.length)
const caseCount = computed(() => props.group.features.reduce((total, item) => total + item.cases.length, 0))
const totalPages = computed(() => Math.max(1, Math.ceil(featureCount.value / PAGE_SIZE)))
const pageStart = computed(() => featureCount.value ? (page.value - 1) * PAGE_SIZE + 1 : 0)
const pageEnd = computed(() => Math.min(featureCount.value, page.value * PAGE_SIZE))
const pagedFeatures = computed(() => props.group.features.slice((page.value - 1) * PAGE_SIZE, page.value * PAGE_SIZE))

watch(() => props.group.case_type, () => { page.value = 1 })
watch(totalPages, value => { page.value = Math.min(page.value, value) })

function featureKey(feature: ExecutionPlanFeature) {
  return `${props.group.case_type}:${feature.feature_id ?? 'none'}:${feature.feature_name}`
}

function sourceText(snapshot: ExecutionPlanCaseSnapshot) {
  if (snapshot.case_type !== 'MANUAL') return snapshot.feature_id ? `#${snapshot.feature_id}` : '-'
  return snapshot.snapshot.knowledge_name
    ? `知识库 #${snapshot.snapshot.knowledge_id || '-'}`
    : '手动'
}

function resultNote(item: ExecutionPlanFeatureCase) {
  return item.latest_result?.error_message || String(item.case_snapshot.snapshot.description || '') || '-'
}

function statusLabel(value: unknown) {
  const labels: Record<string, string> = {
    queued: '排队中', running: '执行中', success: '成功', failed: '失败',
    partial: '部分通过', skipped: '已跳过'
  }
  return labels[String(value || '')] || '未执行'
}

function statusClass(value: unknown) {
  const status = String(value || '')
  if (['success', 'failed', 'partial', 'running', 'queued', 'skipped'].includes(status)) {
    return status === 'queued' ? 'running' : status
  }
  return 'idle'
}

function formatDuration(value: unknown) {
  const duration = Number(value)
  if (!Number.isFinite(duration) || duration < 0) return '-'
  return duration < 1000 ? `${duration}ms` : `${(duration / 1000).toFixed(2)}s`
}
</script>

<style scoped src="./execution-plan-feature-list.css"></style>
