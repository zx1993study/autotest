<template>
  <section class="statistics-page">
    <header class="page-header">
      <div>
        <h2>测试统计看板</h2>
        <p>汇总正式用例规模、执行质量、异常结果和最近执行情况。</p>
      </div>
      <div class="header-actions">
        <ProjectFilterSelect v-model="selectedProjectId" @ready="handleProjectFilterReady" />
        <button type="button" :disabled="loading" @click="loadStatistics">
          {{ loading ? '刷新中...' : '刷新' }}
        </button>
      </div>
    </header>

    <p v-if="errorMessage" class="error-banner">{{ errorMessage }}</p>

    <section class="metric-grid" aria-label="核心测试指标">
      <article v-for="metric in metrics" :key="metric.key" class="metric-card" :class="metric.tone">
        <span>{{ metric.label }}</span>
        <strong>{{ metric.value }}</strong>
        <small>{{ metric.hint }}</small>
      </article>
    </section>

    <section class="dashboard-grid">
      <article class="panel quality-panel">
        <header class="panel-header">
          <h3>执行质量</h3>
          <span>{{ formatPercent(summary.pass_rate) }}</span>
        </header>
        <div class="rate-ring" :style="{ '--rate': `${Math.min(summary.pass_rate || 0, 100) * 3.6}deg` }">
          <strong>{{ formatPercent(summary.pass_rate) }}</strong>
          <small>通过率</small>
        </div>
        <div class="quality-meta">
          <span>通过 {{ summary.success_count }}</span>
          <span>异常 {{ summary.abnormal_count }}</span>
          <span>平均耗时 {{ formatDuration(summary.avg_duration_ms) }}</span>
        </div>
      </article>

      <article class="panel">
        <header class="panel-header">
          <h3>结果分布</h3>
          <span>{{ summary.execution_total }} 次执行</span>
        </header>
        <div class="bar-list">
          <div v-for="item in statistics.status_distribution" :key="item.status" class="bar-row">
            <div class="bar-row-title">
              <span>{{ item.label }}</span>
              <strong>{{ item.count }}</strong>
            </div>
            <div class="bar-track">
              <span class="bar-fill" :class="statusTone(item.status)" :style="{ width: `${item.percent}%` }"></span>
            </div>
          </div>
        </div>
      </article>
    </section>

    <section class="dashboard-grid wide">
      <article class="panel">
        <header class="panel-header">
          <h3>用例规模</h3>
          <span>{{ summary.case_total }} 条正式用例</span>
        </header>
        <div class="case-type-grid">
          <div v-for="item in statistics.case_groups" :key="item.type" class="case-type-row">
            <div>
              <strong>{{ item.label }}</strong>
              <small>启用 {{ item.active }}，停用 {{ item.inactive }}</small>
            </div>
            <span>{{ item.total }}</span>
          </div>
        </div>
      </article>

      <article class="panel">
        <header class="panel-header">
          <h3>类型通过率</h3>
          <span>按执行记录统计</span>
        </header>
        <div class="type-list">
          <div v-for="item in statistics.case_type_distribution" :key="item.type" class="type-row">
            <div>
              <b>{{ item.label }}</b>
              <small>执行 {{ item.total }}，异常 {{ item.abnormal }}</small>
            </div>
            <strong>{{ formatPercent(item.pass_rate) }}</strong>
          </div>
          <p v-if="!statistics.case_type_distribution.length" class="empty-text">暂无执行记录。</p>
        </div>
      </article>
    </section>

    <section class="panel">
      <header class="panel-header">
        <h3>近 7 天执行趋势</h3>
        <span>通过 / 异常</span>
      </header>
      <div class="trend-grid">
        <div v-for="item in statistics.trend" :key="item.date" class="trend-day">
          <div class="trend-bars">
            <span class="trend-success" :style="{ height: trendHeight(item.success, trendMax) }"></span>
            <span class="trend-failed" :style="{ height: trendHeight(item.abnormal, trendMax) }"></span>
          </div>
          <strong>{{ item.total }}</strong>
          <small>{{ shortDate(item.date) }}</small>
        </div>
      </div>
    </section>

    <section class="panel">
      <header class="panel-header">
        <h3>最近执行</h3>
        <span>展示最近 8 条记录</span>
      </header>
      <div class="recent-table-wrap">
        <table class="recent-table">
          <thead>
            <tr>
              <th>记录</th>
              <th>类型</th>
              <th>状态</th>
              <th>耗时</th>
              <th>异常信息</th>
              <th>更新时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="record in statistics.recent_records" :key="String(record.id)">
              <td>{{ record.name }}</td>
              <td>{{ record.case_type }}</td>
              <td><span class="status-pill" :class="statusTone(record.status)">{{ record.status_label }}</span></td>
              <td>{{ formatDuration(record.duration_ms) }}</td>
              <td class="error-cell">{{ record.error || '-' }}</td>
              <td>{{ formatDateTime(record.updated_at) }}</td>
            </tr>
            <tr v-if="!statistics.recent_records.length">
              <td colspan="6" class="empty-cell">暂无执行记录。</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { request } from '../../api/client'
import ProjectFilterSelect from '../../components/filters/ProjectFilterSelect.vue'
import { useLatestRequest } from '../../composables/useLatestRequest'

type Summary = {
  case_total: number
  active_case_total: number
  execution_total: number
  success_count: number
  abnormal_count: number
  queued_count: number
  running_count: number
  pass_rate: number
  avg_duration_ms: number
}

type CaseGroup = {
  type: string
  label: string
  total: number
  active: number
  inactive: number
}

type StatusDistribution = {
  status: string
  label: string
  count: number
  percent: number
}

type CaseTypeDistribution = {
  type: string
  label: string
  total: number
  success: number
  abnormal: number
  pass_rate: number
}

type TrendItem = {
  date: string
  success: number
  abnormal: number
  total: number
}

type RecentRecord = {
  id: number | string | null
  name: string
  status: string
  status_label: string
  case_type: string
  duration_ms: number
  error: string
  updated_at: string
}

type ReportStatistics = {
  summary: Summary
  case_groups: CaseGroup[]
  status_distribution: StatusDistribution[]
  case_type_distribution: CaseTypeDistribution[]
  trend: TrendItem[]
  recent_records: RecentRecord[]
}

const emptySummary: Summary = {
  case_total: 0,
  active_case_total: 0,
  execution_total: 0,
  success_count: 0,
  abnormal_count: 0,
  queued_count: 0,
  running_count: 0,
  pass_rate: 0,
  avg_duration_ms: 0
}

const statistics = ref<ReportStatistics>({
  summary: { ...emptySummary },
  case_groups: [],
  status_distribution: [],
  case_type_distribution: [],
  trend: [],
  recent_records: []
})
const { loading, error: errorMessage, run: loadRequest } = useLatestRequest('统计数据加载失败')
const selectedProjectId = ref(0)
const projectFilterReady = ref(false)

const summary = computed(() => statistics.value.summary)

const metrics = computed(() => [
  {
    key: 'cases',
    label: '正式用例数',
    value: formatNumber(summary.value.case_total),
    hint: `启用 ${formatNumber(summary.value.active_case_total)} 条`,
    tone: 'neutral'
  },
  {
    key: 'executions',
    label: '执行记录数',
    value: formatNumber(summary.value.execution_total),
    hint: `运行中 ${summary.value.running_count}，排队 ${summary.value.queued_count}`,
    tone: 'info'
  },
  {
    key: 'abnormal',
    label: '异常结果数',
    value: formatNumber(summary.value.abnormal_count),
    hint: '失败、错误均计入异常',
    tone: 'danger'
  },
  {
    key: 'rate',
    label: '通过率',
    value: formatPercent(summary.value.pass_rate),
    hint: `通过 ${formatNumber(summary.value.success_count)} 次`,
    tone: 'success'
  }
])

const trendMax = computed(() => Math.max(1, ...statistics.value.trend.map(item => Math.max(item.success, item.abnormal))))

async function loadStatistics() {
  await loadRequest(signal => request<ReportStatistics>({
      method: 'GET',
      url: '/reports/statistics',
      signal,
      params: selectedProjectId.value ? { project_id: selectedProjectId.value } : {}
    }), result => { statistics.value = result })
}

watch([selectedProjectId, projectFilterReady], () => {
  if (projectFilterReady.value) {
    statistics.value = {
      summary: { ...emptySummary }, case_groups: [], status_distribution: [],
      case_type_distribution: [], trend: [], recent_records: []
    }
    void loadStatistics()
  }
})

function handleProjectFilterReady() {
  projectFilterReady.value = true
}

function statusTone(status: string) {
  const value = status.toLowerCase()
  if (value === 'success') return 'success'
  if (value === 'failed' || value === 'error') return 'danger'
  if (value === 'running') return 'info'
  if (value === 'queued') return 'warning'
  return 'neutral'
}

function trendHeight(value: number, maxValue: number) {
  return `${Math.max(6, Math.round((value / Math.max(maxValue, 1)) * 86))}px`
}

function formatNumber(value: number) {
  return new Intl.NumberFormat('zh-CN').format(value || 0)
}

function formatPercent(value: number) {
  return `${Number(value || 0).toFixed(1)}%`
}

function formatDuration(value: number) {
  if (!value) return '-'
  if (value < 1000) return `${value}ms`
  return `${(value / 1000).toFixed(2)}s`
}

function shortDate(value: string) {
  return value.slice(5).replace('-', '/')
}

function formatDateTime(value: string) {
  if (!value) return '-'
  return value.replace('T', ' ').slice(0, 19)
}
</script>

<style scoped>
.statistics-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
}

.page-header h2 {
  margin: 0;
  color: #111827;
  font-size: 22px;
}

.page-header p {
  margin: 6px 0 0;
  color: #6b7280;
  font-size: 14px;
}

.page-header button {
  height: 36px;
  border: 1px solid #2563eb;
  border-radius: 6px;
  background: #2563eb;
  color: #fff;
  cursor: pointer;
  padding: 0 14px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.page-header button:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}

.error-banner {
  margin: 0;
  border: 1px solid #fecaca;
  border-radius: 6px;
  background: #fef2f2;
  color: #b91c1c;
  padding: 10px 12px;
}

.metric-grid,
.dashboard-grid {
  display: grid;
  gap: 14px;
}

.metric-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.dashboard-grid {
  grid-template-columns: minmax(280px, 0.85fr) minmax(0, 1.15fr);
}

.dashboard-grid.wide {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.metric-card,
.panel {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 10px 24px rgb(15 23 42 / 5%);
}

.metric-card {
  display: flex;
  min-height: 126px;
  flex-direction: column;
  justify-content: space-between;
  padding: 18px;
}

.metric-card span,
.metric-card small,
.panel-header span,
.case-type-row small,
.type-row small {
  color: #6b7280;
}

.metric-card strong {
  color: #111827;
  font-size: 30px;
  line-height: 1.1;
}

.metric-card.success {
  border-color: #bbf7d0;
}

.metric-card.danger {
  border-color: #fecaca;
}

.metric-card.info {
  border-color: #bfdbfe;
}

.panel {
  padding: 18px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.panel-header h3 {
  margin: 0;
  color: #111827;
  font-size: 17px;
}

.quality-panel {
  display: grid;
  place-items: center;
}

.quality-panel .panel-header {
  width: 100%;
}

.rate-ring {
  display: grid;
  width: 176px;
  height: 176px;
  place-items: center;
  border-radius: 50%;
  background:
    radial-gradient(circle at center, #fff 0 58%, transparent 59%),
    conic-gradient(#16a34a var(--rate), #e5e7eb 0deg);
}

.rate-ring strong,
.rate-ring small {
  grid-area: 1 / 1;
}

.rate-ring strong {
  transform: translateY(-8px);
  color: #111827;
  font-size: 30px;
}

.rate-ring small {
  transform: translateY(24px);
  color: #6b7280;
}

.quality-meta {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 10px;
  margin-top: 16px;
  color: #4b5563;
  font-size: 13px;
}

.bar-list,
.type-list,
.case-type-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.bar-row-title,
.case-type-row,
.type-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.bar-track {
  height: 10px;
  overflow: hidden;
  border-radius: 999px;
  background: #f3f4f6;
}

.bar-fill {
  display: block;
  height: 100%;
  border-radius: inherit;
}

.bar-fill.success,
.status-pill.success {
  background: #16a34a;
}

.bar-fill.danger,
.status-pill.danger {
  background: #dc2626;
}

.bar-fill.info,
.status-pill.info {
  background: #2563eb;
}

.bar-fill.warning,
.status-pill.warning {
  background: #d97706;
}

.bar-fill.neutral,
.status-pill.neutral {
  background: #6b7280;
}

.case-type-row,
.type-row {
  border-bottom: 1px solid #f3f4f6;
  padding-bottom: 12px;
}

.case-type-row:last-child,
.type-row:last-child {
  border-bottom: 0;
  padding-bottom: 0;
}

.case-type-row div,
.type-row div {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 4px;
}

.case-type-row span,
.type-row strong {
  color: #111827;
  font-size: 20px;
}

.trend-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 12px;
  align-items: end;
}

.trend-day {
  display: grid;
  gap: 8px;
  justify-items: center;
  color: #6b7280;
  font-size: 12px;
}

.trend-day strong {
  color: #111827;
}

.trend-bars {
  display: flex;
  height: 92px;
  align-items: end;
  gap: 5px;
}

.trend-bars span {
  width: 12px;
  border-radius: 999px 999px 2px 2px;
}

.trend-success {
  background: #16a34a;
}

.trend-failed {
  background: #dc2626;
}

.recent-table-wrap {
  overflow-x: auto;
}

.recent-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 760px;
}

.recent-table th,
.recent-table td {
  border-bottom: 1px solid #e5e7eb;
  padding: 12px 10px;
  text-align: left;
  vertical-align: top;
}

.recent-table th {
  color: #6b7280;
  font-size: 12px;
  font-weight: 700;
}

.recent-table td {
  color: #111827;
  font-size: 13px;
}

.status-pill {
  display: inline-flex;
  min-width: 52px;
  justify-content: center;
  border-radius: 999px;
  color: #fff;
  padding: 4px 9px;
  font-size: 12px;
  font-weight: 700;
}

.error-cell {
  max-width: 320px;
  color: #4b5563;
  word-break: break-word;
}

.empty-cell,
.empty-text {
  color: #6b7280;
  text-align: center;
}

@media (max-width: 1120px) {
  .metric-grid,
  .dashboard-grid,
  .dashboard-grid.wide {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .page-header {
    align-items: stretch;
    flex-direction: column;
  }

  .header-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .metric-grid,
  .dashboard-grid,
  .dashboard-grid.wide {
    grid-template-columns: 1fr;
  }

  .trend-grid {
    gap: 6px;
  }
}
</style>
