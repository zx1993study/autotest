import { request } from '../api/client'
import type { PageResult } from '../types/api'
import type {
  AgentListParams,
  AgentNode,
  AgentTask,
  AgentTokenProvisionPayload,
  AgentTokenProvisionResult
} from '../types/agent'

export function listAgentNodes(params: AgentListParams = {}) {
  return request<PageResult<AgentNode>>({
    method: 'GET',
    url: '/agent/nodes',
    params: normalizePaginationParams(params)
  })
}

export function listAgentTasks(params: AgentListParams = {}) {
  return request<PageResult<AgentTask>>({
    method: 'GET',
    url: '/agent/tasks',
    params: normalizePaginationParams(params)
  })
}

export function getAgentTask(taskId: number) {
  return request<AgentTask>({ method: 'GET', url: `/agent/tasks/${taskId}` })
}

export async function waitForAgentTask(taskId: number) {
  for (let attempt = 0; attempt < 100; attempt++) {
    const task = await getAgentTask(taskId)
    if (task.status === 'success') return task.data.result || {}
    if (['failed', 'canceled'].includes(task.status)) throw new Error(String(task.data.error || '本地执行失败'))
    if (task.data.lease_expires_at && Date.parse(String(task.data.lease_expires_at)) < Date.now()) {
      throw new Error('执行节点连接中断，请先检查节点状态；不要重复提交任务')
    }
    await new Promise(resolve => setTimeout(resolve, 1200))
  }
  throw new Error('任务仍在排队或执行，请在执行节点页面查看状态')
}

export async function resolveAgentAction(result: unknown): Promise<unknown> {
  if (!result || typeof result !== 'object') return result
  const queued = result as { queued?: boolean; agent_task?: AgentTask; agent_tasks?: AgentTask[] }
  if (!queued.queued) return result
  const tasks = queued.agent_tasks || (queued.agent_task ? [queued.agent_task] : [])
  const results: unknown[] = []
  for (const task of tasks) results.push(await waitForAgentTask(task.id))
  return results.length === 1 ? results[0] : { results }
}

export function setDefaultLocalHeadedNode(nodeId: number) {
  return request<AgentNode>({
    method: 'POST',
    url: `/agent/nodes/${nodeId}/default-local-headed`,
    data: {}
  })
}

export function provisionAgentNodeToken(payload: AgentTokenProvisionPayload) {
  return request<AgentTokenProvisionResult>({
    method: 'POST',
    url: '/agent/nodes/provision-token',
    data: payload
  })
}

export function resetAgentNodeToken(nodeId: number) {
  return request<AgentTokenProvisionResult>({
    method: 'POST',
    url: `/agent/nodes/${nodeId}/token/reset`,
    data: {}
  })
}

function normalizePaginationParams(params: AgentListParams): Record<string, unknown> {
  return {
    page: params.page,
    page_size: params.pageSize,
    keyword: params.keyword
  }
}
