export interface CaseExecutionSummary {
  record_id: number
  status: 'success' | 'failed' | 'exception' | 'queued' | 'running' | 'cancelled' | 'skipped'
  response_code: unknown
  http_status: number | null
  executed_at: string | null
  error: string | null
}

export interface ApiCaseRunRequest {
  project_id?: number
  env_id?: number | null
  auth_id?: number | null
  mode?: string
  node_id?: string | null
  case_ids: number[]
  config?: Record<string, unknown> & { concurrency?: number; timeout?: number }
}
