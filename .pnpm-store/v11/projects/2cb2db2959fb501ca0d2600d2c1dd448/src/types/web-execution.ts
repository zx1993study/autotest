export type WebExecutionScope = 'page' | 'feature' | 'case'
export type WebExecutionStatus = 'success' | 'failed' | 'not_run' | 'partial' | 'unverified' | 'running' | 'canceled' | 'empty'

export interface WebExecutionSummary {
  id: number
  status: WebExecutionStatus
  total_count: number
  success_count: number
  failed_count: number
  not_run_count: number
  unverified_count: number
  running_count: number
  canceled_count: number
  executed_at: string | null
  record_id: number | null
}
