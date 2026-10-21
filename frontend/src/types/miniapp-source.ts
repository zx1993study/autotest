import type { ResourceItem } from './resource'

export interface SourceDefinition {
  id: string
  category: string
  automation: string
  route: string
  preconditions: string[]
  steps: string[]
  expected: string[]
}

export interface SourceCase extends ResourceItem {
  data: Record<string, unknown> & {
    execution_engine?: string
    category?: string
    definition?: SourceDefinition
    api_business?: { flow_id: number; scenario_id: number }
  }
}

export interface SourceResult {
  case_id: number
  name: string
  status: string
  executed: boolean
  reason?: string
  duration_ms: number
}

export interface SourceRun extends ResourceItem {
  data: Record<string, unknown> & {
    platform: string
    case_count: number
    counts?: Record<string, number>
    results?: SourceResult[]
    error?: string
  }
}

export const sourceCategories: Record<string, string> = {
  render: '页面呈现', query: '条件查询', validation: '字段校验', client_guard: '客户端校验', business: '业务流程'
}
export const sourceStatuses: Record<string, string> = {
  queued: '排队中', running: '执行中', success: '通过', failed: '失败', blocked: '阻塞', interrupted: '中断'
}
