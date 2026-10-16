import type {
  AgentNodeStatusValue,
  AgentTaskStatusValue,
  AgentTaskTypeValue
} from '../constants/enums'
import type { ResourceItem } from './resource'

export interface AgentNodeData {
  node_key: string
  agent_status: AgentNodeStatusValue | string
  version?: string
  capabilities?: string[]
  system?: Record<string, unknown>
  last_seen_at?: string
  current_task_id?: number | string | null
  default_local_headed?: boolean
  has_agent_token?: boolean
  token_issued_at?: string
  token_last4?: string
  [key: string]: unknown
}

export interface AgentNode extends ResourceItem {
  data: AgentNodeData
}

export interface AgentTaskResult {
  total?: number
  success_count?: number
  failed_count?: number
  queued_count?: number
  records?: unknown[]
  [key: string]: unknown
}

export interface AgentTaskData {
  task_type: AgentTaskTypeValue | string
  node_key?: string
  payload?: Record<string, unknown>
  created_at?: string
  claimed_by?: string
  claimed_at?: string
  reported_by?: string
  finished_at?: string
  result?: AgentTaskResult
  saved_records?: unknown[]
  error?: string
  [key: string]: unknown
}

export interface AgentTask extends ResourceItem {
  status: AgentTaskStatusValue | string
  data: AgentTaskData
}

export interface AgentTaskRunResult {
  total: number
  success_count: number
  failed_count: number
  queued_count: number
  records: unknown[]
  agent_task?: AgentTask
}

export interface AgentListParams {
  page?: number
  pageSize?: number
  keyword?: string
}

export interface AgentTokenProvisionPayload {
  node_key: string
  name: string
  version?: string
  capabilities?: string[]
  system?: Record<string, unknown>
}

export interface AgentTokenProvisionResult {
  node: AgentNode
  agent_token: string
}
