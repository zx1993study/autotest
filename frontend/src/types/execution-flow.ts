import type { ResourceItem } from './resource'

export type FlowStep = {
  api_id: number
  api_label: string
  auth_id: number | null
  token_label: string
  case_id: number
  case_label: string
  case_json: Record<string, unknown>
}

export type ExecutionRecord = ResourceItem & {
  data: Record<string, unknown>
}

export type ExecutionSummary = {
  total: number
  success_count: number
  failed_count: number
  queued_count: number
  records: ExecutionRecord[]
}

export type StepDraft = FlowStep & {
  uid: string
  persistedIndex: number | null
  selectedApiId: number
  selectedAuthId: number
  selectedCaseId: number
  caseTitle: string
  caseJsonText: string
  apiKeyword: string
  formError: string
  saving: boolean
  executing: boolean
  executionSummary: ExecutionSummary | null
}
