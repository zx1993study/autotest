export interface ApiReportRow {
  key: string
  kind: 'api' | 'flow'
  record_id: number
  project_id: number | null
  flow_id: number | null
  case_id?: number | null
  scenario_id: number | null
  source_name: string
  method: string
  field_or_scene: string
  test_point: string
  status: string
  passed: boolean | null
  executed_at: string
}

export interface ApiReportQuery {
  project_id?: number
  kind?: 'api' | 'flow'
  status?: string
  keyword?: string
  page: number
  pageSize: number
}
