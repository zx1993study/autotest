import type { ResourceItem } from './resource'

export type ValueOperator = 'eq' | 'ne' | 'gt' | 'ge' | 'lt' | 'le' | 'contains' | 'exists'
export interface FlowCondition { source: string; name: string; operator: ValueOperator; value: unknown }
export interface FlowBinding { source: string; name: string; target: 'auto' | 'params' | 'headers' | 'query' | 'body'; path: string; target_name?: string; prefix: string }
export interface FlowExtract { name: string; source: 'body' | 'header' | 'status'; path: string; mode?: 'single' | 'array'; paths?: string[]; required: boolean; sensitive: boolean }
export interface FlowRoute { source: 'body' | 'header' | 'status'; path: string; operator: ValueOperator; value: unknown; target: string }
export interface FlowRequestOverride {
  params: Record<string, unknown>; request: Record<string, unknown>; request_removals?: string[]
}
export interface FlowNode {
  key: string; name: string; api_id: number; case_id: number | null; auth_id: number | null
  params: Record<string, unknown>; request: Record<string, unknown>
  request_removals?: string[]
  bindings: FlowBinding[]; extracts: FlowExtract[]; routes: FlowRoute[]; next: string
}
export interface FlowDefinition extends Record<string, unknown> {
  version: number; inputs: Record<string, unknown>; nodes: FlowNode[]
}
export interface ApiFlow extends ResourceItem { data: FlowDefinition }
export interface ScenarioNode {
  case_id: number | null; mode: 'always' | 'skip' | 'condition'; condition: FlowCondition | null
  params: Record<string, unknown>; request: Record<string, unknown>
  request_removals?: string[]
  assertions: Record<string, unknown>[] | null; bindings: FlowBinding[] | null; extracts: FlowExtract[] | null
}
export interface ScenarioDefinition extends Record<string, unknown> {
  flow_id: number; template_version: number; inputs: Record<string, unknown>; nodes: Record<string, ScenarioNode>
  failure_policy: 'stop' | 'continue'; expected_end: string; latest_status?: string
}
export interface ApiFlowScenario extends ResourceItem { data: ScenarioDefinition }
export interface FlowNodeEvidence extends Record<string, unknown> {
  key: string; name: string; status: string; reason?: string; error?: string
  duration_ms?: number; response_status?: number; request?: Record<string, unknown>
  response_headers?: Record<string, string>; response_body?: string; assertions?: Record<string, unknown>[]
  outputs?: Record<string, unknown>; next?: string
}
export interface FlowScenarioResult {
  scenario_id: number; name: string; status: string; nodes: FlowNodeEvidence[]; path?: string[]
  duration_ms?: number; error?: string; expected_end?: string; end_passed?: boolean
}
export interface ApiFlowRun extends ResourceItem {
  data: { flow_id: number; template_version: number; mode: string; concurrency: number; results: FlowScenarioResult[] }
}
export interface ApiFlowRunRequest { scenario_ids: number[]; mode: 'serial' | 'parallel'; concurrency: number; inputs: Record<string, unknown> }

export const flowStatusLabels: Record<string, string> = {
  active: '启用', disabled: '停用', queued: '排队中', running: '执行中', success: '通过',
  failed: '失败', skipped: '跳过', cancelled: '已取消', interrupted: '已中断'
}
export const operatorOptions = [
  { value: 'eq', label: '等于' }, { value: 'ne', label: '不等于' }, { value: 'exists', label: '存在' },
  { value: 'gt', label: '大于' }, { value: 'ge', label: '大于等于' }, { value: 'lt', label: '小于' },
  { value: 'le', label: '小于等于' }, { value: 'contains', label: '包含' }
]
export function cloneFlowValue<T>(value: T): T { return JSON.parse(JSON.stringify(value)) as T }
export function newScenarioNode(): ScenarioNode {
  return { case_id: null, mode: 'always', condition: null, params: {}, request: {}, assertions: null, bindings: null, extracts: null }
}
