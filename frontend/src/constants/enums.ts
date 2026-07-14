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
  LOCAL_HEADLESS: 'local_headless',
  LOCAL_HEADED: 'local_headed',
  LOCAL_APPIUM: 'local_appium',
  REMOTE_NODE: 'remote_node'
} as const

export type ResourceStatusValue = (typeof ResourceStatus)[keyof typeof ResourceStatus]
export type CaseDraftStatusValue = (typeof CaseDraftStatus)[keyof typeof CaseDraftStatus]
export type CaseTypeValue = (typeof CaseType)[keyof typeof CaseType]
export type ExecutionModeValue = (typeof ExecutionMode)[keyof typeof ExecutionMode]

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
