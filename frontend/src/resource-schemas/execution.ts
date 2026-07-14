import type { ResourceColumn, ResourceField } from '../types/resource-schema'
import { caseTypeOptions, descriptionField, projectIdField, statusField } from './shared'

export const executionFlowFields: ResourceField[] = [
  projectIdField,
  { key: 'name', label: '流程名称', required: true, placeholder: '请输入执行流程名称' },
  { key: 'description', label: '备注', type: 'textarea', full: true, rows: 3 }
]

export const executionFlowColumns: ResourceColumn[] = [
  { key: 'name', label: '流程名称' },
  { key: 'project_id', label: '项目 ID', width: '90px' },
  { key: 'description', label: '备注' },
  { key: 'updated_at', label: '更新时间', width: '180px' }
]

export const executionPlanFields: ResourceField[] = [
  { key: 'name', label: '计划名称', required: true },
  projectIdField,
  { key: 'data.flow_id', label: '流程 ID', type: 'number' },
  {
    key: 'data.run_mode',
    label: '执行方式',
    type: 'select',
    defaultValue: 'once',
    options: [
      { label: '单次执行', value: 'once' },
      { label: '定时执行', value: 'scheduled' },
      { label: 'Cron 周期', value: 'cron' }
    ]
  },
  { key: 'data.cron', label: 'Cron 表达式' },
  { key: 'data.executor_node', label: '执行节点' },
  { key: 'data.headless', label: '无头执行', type: 'checkbox', defaultValue: true },
  { key: 'data.retry_count', label: '失败重试次数', type: 'number', defaultValue: 0 },
  statusField,
  descriptionField
]

export const executionPlanColumns: ResourceColumn[] = [
  { key: 'name', label: '计划名称' },
  { key: 'data.flow_id', label: '流程 ID', width: '90px' },
  { key: 'data.run_mode', label: '执行方式' },
  { key: 'data.executor_node', label: '执行节点' },
  { key: 'data.headless', label: '无头' },
  { key: 'status', label: '状态', width: '90px' }
]

export const reportRecordFields: ResourceField[] = [
  { key: 'name', label: '记录名称', required: true },
  projectIdField,
  { key: 'data.plan_id', label: '计划 ID', type: 'number' },
  { key: 'data.case_id', label: '用例 ID', type: 'number' },
  { key: 'data.case_type', label: '用例类型', type: 'select', options: caseTypeOptions },
  {
    key: 'status',
    label: '执行状态',
    type: 'select',
    defaultValue: 'queued',
    options: [
      { label: '排队中', value: 'queued' },
      { label: '执行中', value: 'running' },
      { label: '成功', value: 'success' },
      { label: '失败', value: 'failed' }
    ]
  },
  { key: 'data.duration_ms', label: '耗时(ms)', type: 'number' },
  { key: 'data.screenshot_path', label: '截图路径' },
  { key: 'data.log_path', label: '日志路径' },
  descriptionField
]

export const reportRecordColumns: ResourceColumn[] = [
  { key: 'name', label: '记录名称' },
  { key: 'data.plan_id', label: '计划 ID', width: '90px' },
  { key: 'data.case_id', label: '用例 ID', width: '90px' },
  { key: 'data.case_type', label: '类型' },
  { key: 'status', label: '状态', width: '90px' },
  { key: 'data.duration_ms', label: '耗时(ms)' }
]

export const reportStatisticsFields: ResourceField[] = [
  { key: 'name', label: '统计名称', required: true },
  projectIdField,
  { key: 'data.metric_type', label: '统计类型', placeholder: '通过率/失败趋势/模块质量' },
  { key: 'data.total_count', label: '总数', type: 'number', defaultValue: 0 },
  { key: 'data.success_count', label: '成功数', type: 'number', defaultValue: 0 },
  { key: 'data.failed_count', label: '失败数', type: 'number', defaultValue: 0 },
  { key: 'data.pass_rate', label: '通过率', placeholder: '例如：96.5%' },
  statusField,
  descriptionField
]

export const reportStatisticsColumns = [
  { key: 'name', label: '统计名称' },
  { key: 'data.metric_type', label: '统计类型' },
  { key: 'data.total_count', label: '总数' },
  { key: 'data.success_count', label: '成功数' },
  { key: 'data.failed_count', label: '失败数' },
  { key: 'data.pass_rate', label: '通过率' }
]

