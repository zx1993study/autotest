export interface ExecutionPlanInfo {
  id: number
  name: string
  project_id?: number | null
  test_rounds: number
  test_type: string
  api_ids: number[]
  web_feature_ids: number[]
  api_count: number
  web_feature_count: number
  description?: string | null
  requirement_title?: string | null
  requirement_document?: string | null
  generation: Record<string, unknown>
  status: string
  created_at: string
  updated_at: string
}

export interface ExecutionPlanSavePayload {
  name: string
  project_id: number
  api_ids: number[]
  web_feature_ids: number[]
  description?: string | null
}

export interface ExecutionPlanCaseSnapshot {
  id: number
  plan_id: number
  case_type: string
  feature_id?: number | null
  feature_name: string
  case_id: number
  case_name: string
  case_version?: string | null
  snapshot: Record<string, unknown>
  sort_order: number
  created_at: string
  updated_at: string
}

export interface ExecutionPlanRun {
  id: number
  plan_id: number
  round_no: number
  status: string
  total_count: number
  success_count: number
  failed_count: number
  pass_rate: number
  started_at?: string | null
  ended_at?: string | null
  created_at: string
  updated_at: string
}

export interface ExecutionPlanRunItem {
  id: number
  run_id: number
  plan_case_id: number
  case_type: string
  case_id: number
  status: string
  duration_ms?: number | null
  error_message?: string | null
  report_record_id?: number | null
  artifact: Record<string, unknown>
  executed_at?: string | null
  created_at: string
}

export interface ExecutionPlanFeatureCase {
  case_snapshot: ExecutionPlanCaseSnapshot
  latest_result?: ExecutionPlanRunItem | null
}

export interface ExecutionPlanFeature {
  feature_id?: number | null
  feature_name: string
  cases: ExecutionPlanFeatureCase[]
}

export interface ExecutionPlanGroup {
  case_type: string
  label: string
  features: ExecutionPlanFeature[]
}

export interface ExecutionPlanSummary {
  feature_count: number
  case_count: number
  run_count: number
  executed_count: number
  success_count: number
  failed_count: number
  pass_rate: number
}

export interface ExecutionPlanDetail {
  plan: ExecutionPlanInfo
  summary: ExecutionPlanSummary
  latest_run?: ExecutionPlanRun | null
  runs: ExecutionPlanRun[]
  groups: ExecutionPlanGroup[]
}

export interface ExecutionPlanGenerationResult {
  plan_id: number
  knowledge_count: number
  api_case_count: number
  web_case_count: number
  generated_case_count: number
  detail: ExecutionPlanDetail
}

export interface ExecutionPlanFeatureAddPayload {
  case_type: 'API' | 'WEB'
  feature_ids: number[]
}

export interface ExecutionPlanManualFeaturePayload {
  feature_name: string
  description?: string | null
}
