<template>
  <section class="api-reports">
    <header class="report-header"><h2>API 报告</h2><button type="button" title="刷新报告" aria-label="刷新报告" :disabled="loading" @click="load"><RefreshCw :size="16" /></button></header>
    <form class="report-filters" @submit.prevent="search">
      <ProjectFilterSelect v-model="projectId" @ready="ready = true" />
      <select v-model="kind" aria-label="按报告类型筛选"><option value="">全部类型</option><option value="api">单接口</option><option value="flow">功能流程</option></select>
      <select v-model="status" aria-label="按报告状态筛选"><option value="">全部状态</option><option v-for="(label, value) in statuses" :key="value" :value="value">{{ label }}</option></select>
      <input v-model="keyword" type="search" aria-label="搜索 API 报告" placeholder="API 路径、流程、字段、场景或测试点" />
      <button type="submit"><Search :size="15" />查询</button>
    </form>
    <p v-if="error" class="report-error" role="alert">{{ evidenceText(error) }} <button type="button" @click="load">重试</button></p>
    <div class="report-table-wrap" :aria-busy="loading">
      <table><thead><tr><th>API 路径 / 流程名称</th><th>字段 / 场景</th><th>测试点</th><th>是否通过</th><th>操作</th></tr></thead><tbody>
        <tr v-for="row in rows" :key="row.key">
          <td><strong :class="{ 'api-path': row.kind === 'api' }">{{ row.kind === 'api' ? `${row.method} ` : '' }}{{ evidenceText(row.source_name) }}</strong><small>{{ row.kind === 'api' ? '单接口' : '功能流程' }} · #{{ row.record_id }} · {{ formatTime(row.executed_at) }}</small></td>
          <td>{{ evidenceText(row.field_or_scene) }}</td><td>{{ evidenceText(row.test_point) }}</td>
          <td><span class="report-status" :class="row.status"><component :is="row.passed === true ? CircleCheck : row.passed === false ? CircleX : Clock3" :size="14" />{{ resultLabel(row) }}</span></td>
          <td><button type="button" @click="selected = row"><Eye :size="14" />查看结果</button></td>
        </tr>
        <tr v-if="!rows.length"><td colspan="5" class="report-empty">{{ loading ? '加载中...' : error ? '报告加载失败' : '暂无报告' }}</td></tr>
      </tbody></table>
    </div>
    <CommonPagination :page="page" :page-size="pageSize" :total="total" :loading="loading" @change="paginate" />
    <ApiReportResultDialog v-if="selected" :row="selected" @close="selected = null" />
  </section>
</template>

<script setup lang="ts">
import { CircleCheck, CircleX, Clock3, Eye, RefreshCw, Search } from 'lucide-vue-next'
import ProjectFilterSelect from '../filters/ProjectFilterSelect.vue'
import CommonPagination from '../common/CommonPagination.vue'
import ApiReportResultDialog from './ApiReportResultDialog.vue'
import { useApiReports } from '../../composables/useApiReports'
import type { ApiReportRow } from '../../types/api-report'
import { evidenceText, executionStatus } from '../../utils/executionEvidence'
import '../../styles/api-flow.css'

const { projectId, ready, kind, status, keyword, page, pageSize, total, rows, selected, loading, error, load, search, paginate } = useApiReports()
const statuses = { success: '通过', failed: '未通过', queued: '排队中', running: '执行中', blocked: '阻塞', interrupted: '中断', cancelled: '已取消', skipped: '已跳过' }
const formatTime = (value: string) => value ? value.replace('T', ' ').slice(0, 19) : '-'
const resultLabel = (row: ApiReportRow) => row.passed === true ? '通过' : row.passed === false ? '未通过' : executionStatus(row.status)
</script>

<style scoped>
.api-reports { padding: 22px; color: #172033; background: #fff; min-width: 0; }
.report-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 18px; }
h2 { margin: 0; font-size: 20px; }
button { display: inline-flex; align-items: center; justify-content: center; gap: 6px; white-space: nowrap; }
.report-header button { width: 34px; height: 34px; padding: 0; }
.report-filters { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; margin-bottom: 16px; }
.report-filters select, .report-filters input { height: 34px; min-width: 0; }
.report-filters select { width: 140px; } .report-filters input { flex: 1 1 280px; max-width: 540px; }
.report-table-wrap { overflow: auto; border-top: 1px solid #dce3eb; }
table { width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 13px; }
th { background: #f4f7fb; color: #52627a; text-align: left; font-weight: 500; }
th, td { padding: 13px 12px; border-bottom: 1px solid #e7ecf2; vertical-align: top; overflow-wrap: anywhere; }
th:first-child { width: 29%; } th:nth-child(2) { width: 19%; } th:nth-child(3) { width: 28%; } th:nth-child(4) { width: 11%; } th:last-child { width: 120px; }
strong { font-weight: 600; } .api-path { font-family: Consolas, monospace; }
small { display: block; color: #738095; margin-top: 6px; font-size: 11px; }
.report-status { display: inline-flex; gap: 5px; align-items: center; color: #607087; }
.report-status svg { flex-shrink: 0; } .report-status.success { color: #157347; } .report-status.failed, .report-status.blocked { color: #b42318; }
.report-empty { padding: 30px; text-align: center; color: #738095; } .report-error { color: #b42318; overflow-wrap: anywhere; }
@media (max-width: 900px) { table { min-width: 850px; } }
@media (max-width: 720px) { .api-reports { padding: 16px 12px; } .report-filters input { max-width: none; flex-basis: 100%; } .report-filters select { flex: 1; } }
</style>
