import type { ResourceOption } from '../types/resource-schema'

/** Values must stay synchronized with backend/app/enums/business.py. */
export const ResourceStatus = {
  ACTIVE: 'active',
  DRAFT: 'draft',
  DISABLED: 'disabled',
  ARCHIVED: 'archived'
} as const

export const CaseDraftStatus = {
  DRAFT: 'draft',
  ACCEPTED: 'accepted',
  REJECTED: 'rejected'
} as const

export const CaseType = {
  API: 'API',
  WEB: 'WEB',
  APP: 'APP',
  MINIAPP: 'MINIAPP'
} as const

export const ExecutionMode = {
  SERVER_HEADLESS: 'server_headless',
  LOCAL_HEADLESS: 'local_headless',
  LOCAL_HEADED: 'local_headed',
  LOCAL_APPIUM: 'local_appium',
  REMOTE_NODE: 'remote_node'
} as const

export const WebEngine = {
  PLAYWRIGHT: 'playwright',
  STAGEHAND: 'stagehand',
  HYBRID: 'hybrid'
} as const

export const ExecutionPlanStatus = {
  ACTIVE: 'active',
  DONE: 'done'
} as const

export const ExecutionPlanTestType = {
  WEB: 'WEB',
  API: 'API',
  APP: 'APP',
  ALL: 'ALL'
} as const

export const KnowledgePrinciple = {
  CONDITION_COVERAGE: 'condition_coverage',
  BOUNDARY_TESTING: 'boundary_testing',
  EXCEPTION_TESTING: 'exception_testing',
  SMOKE_TESTING: 'smoke_testing',
  BULK_INSERT: 'bulk_insert',
  INPUT_OVERWRITE: 'input_overwrite',
  TEXT_LENGTH_LIMIT: 'text_length_limit',
  NUMBER_RANGE_LIMIT: 'number_range_limit'
} as const

export const ExecutionRunStatus = {
  QUEUED: 'queued',
  RUNNING: 'running',
  SUCCESS: 'success',
  FAILED: 'failed',
  PARTIAL: 'partial'
} as const

export const ExecutionRunItemStatus = {
  QUEUED: 'queued',
  RUNNING: 'running',
  SUCCESS: 'success',
  FAILED: 'failed',
  SKIPPED: 'skipped'
} as const

export const AgentNodeStatus = {
  ONLINE: 'online',
  OFFLINE: 'offline',
  BUSY: 'busy',
  DISABLED: 'disabled'
} as const

export const AgentTaskStatus = {
  PENDING: 'pending',
  RUNNING: 'running',
  SUCCESS: 'success',
  FAILED: 'failed',
  CANCELED: 'canceled'
} as const

export const AgentTaskType = {
  CASE_EXECUTION: 'case_execution',
  DEVICE_DISCOVERY: 'device_discovery',
  WEB_VISION_DISCOVERY: 'web_vision_discovery'
} as const

export const AgentCapability = {
  CASE_EXECUTION: 'case_execution',
  APP_EXECUTION: 'app_execution',
  DEVICE_DISCOVERY: 'device_discovery',
  WEB_EXECUTION: 'web_execution',
  WEB_VISION_DISCOVERY: 'web_vision_discovery',
  STAGEHAND: 'stagehand'
} as const

export type ResourceStatusValue = (typeof ResourceStatus)[keyof typeof ResourceStatus]
export type CaseDraftStatusValue = (typeof CaseDraftStatus)[keyof typeof CaseDraftStatus]
export type CaseTypeValue = (typeof CaseType)[keyof typeof CaseType]
export type ExecutionModeValue = (typeof ExecutionMode)[keyof typeof ExecutionMode]
export type WebEngineValue = (typeof WebEngine)[keyof typeof WebEngine]
export type ExecutionPlanStatusValue = (typeof ExecutionPlanStatus)[keyof typeof ExecutionPlanStatus]
export type ExecutionPlanTestTypeValue = (typeof ExecutionPlanTestType)[keyof typeof ExecutionPlanTestType]
export type KnowledgePrincipleValue = (typeof KnowledgePrinciple)[keyof typeof KnowledgePrinciple]
export type ExecutionRunStatusValue = (typeof ExecutionRunStatus)[keyof typeof ExecutionRunStatus]
export type ExecutionRunItemStatusValue = (typeof ExecutionRunItemStatus)[keyof typeof ExecutionRunItemStatus]
export type AgentNodeStatusValue = (typeof AgentNodeStatus)[keyof typeof AgentNodeStatus]
export type AgentTaskStatusValue = (typeof AgentTaskStatus)[keyof typeof AgentTaskStatus]
export type AgentTaskTypeValue = (typeof AgentTaskType)[keyof typeof AgentTaskType]
export type AgentCapabilityValue = (typeof AgentCapability)[keyof typeof AgentCapability]

export const resourceStatusOptions: ResourceOption[] = [
  { label: '启用', value: ResourceStatus.ACTIVE },
  { label: '草稿', value: ResourceStatus.DRAFT },
  { label: '停用', value: ResourceStatus.DISABLED },
  { label: '归档', value: ResourceStatus.ARCHIVED }
]

export const caseDraftStatusOptions: ResourceOption[] = [
  { label: '待审核', value: CaseDraftStatus.DRAFT },
  { label: '已采纳', value: CaseDraftStatus.ACCEPTED },
  { label: '已驳回', value: CaseDraftStatus.REJECTED }
]

export const caseTypeOptions: ResourceOption[] = [
  { label: 'API', value: CaseType.API },
  { label: 'Web', value: CaseType.WEB },
  { label: 'App', value: CaseType.APP },
  { label: '小程序', value: CaseType.MINIAPP }
]

export const executionPlanStatusOptions: ResourceOption[] = [
  { label: '进行中', value: ExecutionPlanStatus.ACTIVE },
  { label: '已完成', value: ExecutionPlanStatus.DONE }
]

export const executionPlanTestTypeOptions: ResourceOption[] = [
  { label: 'Web', value: ExecutionPlanTestType.WEB },
  { label: 'API', value: ExecutionPlanTestType.API },
  { label: 'App', value: ExecutionPlanTestType.APP },
  { label: '全部', value: ExecutionPlanTestType.ALL }
]

export const knowledgePrincipleOptions: ResourceOption[] = [
  { label: '条件覆盖原则', value: KnowledgePrinciple.CONDITION_COVERAGE },
  { label: '边界测试', value: KnowledgePrinciple.BOUNDARY_TESTING },
  { label: '异常测试', value: KnowledgePrinciple.EXCEPTION_TESTING },
  { label: '冒烟测试', value: KnowledgePrinciple.SMOKE_TESTING },
  { label: '批量插入数据', value: KnowledgePrinciple.BULK_INSERT },
  { label: '输入框内容是否被覆盖', value: KnowledgePrinciple.INPUT_OVERWRITE },
  { label: '文本框输入超限', value: KnowledgePrinciple.TEXT_LENGTH_LIMIT },
  { label: '数字输入框超限', value: KnowledgePrinciple.NUMBER_RANGE_LIMIT }
]
