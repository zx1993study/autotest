<template>
  <section class="record-evidence">
    <header v-if="showExecution" class="record-summary">
      <div class="record-title"><strong>{{ record ? `#${record.id} ${safeName}` : '暂无执行记录' }}</strong><span class="record-status" :class="recordStatusClass">{{ recordStatus }}</span></div>
      <dl>
        <div><dt>类型</dt><dd>{{ record?.data?.case_type || '-' }}</dd></div>
        <div><dt>HTTP 状态</dt><dd>{{ evidence.httpStatus ?? '-' }}</dd></div>
        <div><dt>业务码</dt><dd>{{ evidence.businessCode ?? '-' }}</dd></div>
        <div><dt>耗时</dt><dd>{{ evidence.duration != null ? `${evidence.duration} ms` : '-' }}</dd></div>
        <div><dt>执行时间</dt><dd>{{ record?.created_at || '-' }}</dd></div>
      </dl>
      <p v-if="evidence.error" class="record-error">{{ evidence.error }}</p>
    </header>
    <div class="evidence-grid">
      <EvidenceCard title="请求参数" :value="evidence.request" empty-text="未记录请求参数" />
      <EvidenceCard title="返回结果" :value="evidence.response" empty-text="未记录返回结果" />
      <EvidenceCard title="断言" :value="evidence.assertions.length ? evidence.assertions.map(row => row.definition) : undefined">
        <AssertionResults :rows="evidence.assertions" />
      </EvidenceCard>
    </div>
    <div v-if="screenshots.length" class="record-screenshots"><a v-for="(shot, index) in screenshots" :key="index" :href="media(shot.screenshot_url)" target="_blank" rel="noopener noreferrer"><img :src="media(shot.screenshot_url)" :alt="shot.step_name || `执行截图 ${index + 1}`" loading="lazy" /><span>{{ shot.step_name || `执行截图 ${index + 1}` }}</span></a></div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ResourceItem } from '../../types/resource'
import { evidenceText, executionEvidence, executionStatus } from '../../utils/executionEvidence'
import AssertionResults from './AssertionResults.vue'
import EvidenceCard from './EvidenceCard.vue'
import { withScreenshotAccessToken as media } from '../../utils/screenshotUrl'

const props = withDefaults(defineProps<{
  record: ResourceItem | null
  fallbackRequest?: unknown
  fallbackAssertions?: unknown
  showExecution?: boolean
}>(), { showExecution: true })
const safeName = computed(() => evidenceText(props.record?.name))
const recordStatusClass = computed(() => {
  const record = props.record
  if (record?.data?.case_type !== 'WEB') return record?.status
  if (record.data.business_result === 'failed') return 'failed'
  if (record.status === 'success' && (record.data.business_result !== 'passed' || !record.data.assertion_count)) return 'unverified'
  return record.status
})
const recordStatus = computed(() => recordStatusClass.value === 'unverified' ? '未验证' : executionStatus(recordStatusClass.value))
const screenshots = computed(() => (Array.isArray(props.record?.data?.screenshots) ? props.record.data.screenshots : []).filter((shot: any) => shot && typeof shot.screenshot_url === 'string' && /^\/api\/v1\/screenshots\//.test(shot.screenshot_url)))
const evidence = computed(() => executionEvidence(props.showExecution ? props.record : null, {
  request: props.fallbackRequest, assertions: props.fallbackAssertions
}))
</script>

<style scoped>
.record-evidence { min-width: 0; display: grid; gap: 16px; }
.record-summary { display: grid; gap: 12px; }
.record-title { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; font-size: 14px; }
.record-title strong { min-width: 0; overflow-wrap: anywhere; }
.record-status { font-size: 13px; white-space: nowrap; color: #607087; }
.record-status.success, .record-status.passed { color: #157347; }
.record-status.failed, .record-status.error, .record-status.blocked { color: #b42318; }
dl { display: flex; flex-wrap: wrap; gap: 12px 28px; margin: 0; font-size: 13px; }
dl div { min-width: 90px; } dt { color: #738095; margin-bottom: 4px; } dd { margin: 0; overflow-wrap: anywhere; }
.record-error { margin: 0; border-left: 3px solid #d92d20; padding: 8px 12px; background: #fff4f2; color: #b42318; font-size: 13px; white-space: pre-wrap; overflow-wrap: anywhere; }
.evidence-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); align-items: start; gap: 14px; }
.record-screenshots { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(240px, 100%), 1fr)); gap: 12px; }
.record-screenshots a { min-width: 0; color: #496077; font-size: 12px; overflow-wrap: anywhere; }
.record-screenshots img { display: block; width: 100%; aspect-ratio: 16 / 9; object-fit: contain; border: 1px solid #dce3eb; margin-bottom: 5px; }
@media (max-width: 900px) { .evidence-grid { grid-template-columns: minmax(0, 1fr); } }
</style>
