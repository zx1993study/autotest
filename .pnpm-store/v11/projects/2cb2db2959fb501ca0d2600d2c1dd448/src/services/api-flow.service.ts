import { request } from '../api/client'
import type { ApiFlow, ApiFlowRun, ApiFlowRunRequest, ApiFlowScenario, FlowDefinition } from '../types/api-flow'
import type { ResourceItem, ResourcePayload } from '../types/resource'

const flowPath = (id: number) => `/execution/flows/${id}`
export const getFlowCase = (id: number) => request<ResourceItem>({ url: `/api-testing/cases/${id}` })
export const getApiFlow = (id: number) => request<ApiFlow>({ url: flowPath(id) })
export const saveApiFlowTemplate = (id: number, data: FlowDefinition) => request<ApiFlow>({ method: 'PUT', url: flowPath(id), data: { data } })
export const listFlowScenarios = (id: number) => request<ApiFlowScenario[]>({ url: `${flowPath(id)}/scenarios` })
export const saveFlowScenario = (flowId: number, payload: ResourcePayload, sceneId?: number) => request<ApiFlowScenario>({
  method: sceneId ? 'PUT' : 'POST', url: `${flowPath(flowId)}/scenarios${sceneId ? `/${sceneId}` : ''}`, data: payload
})
export const deleteFlowScenario = (flowId: number, sceneId: number) => request<boolean>({ method: 'DELETE', url: `${flowPath(flowId)}/scenarios/${sceneId}` })
export const copyFlowScenario = (flowId: number, sceneId: number) => request<ApiFlowScenario>({ method: 'POST', url: `${flowPath(flowId)}/scenarios/${sceneId}/copy` })
export const syncFlowScenario = (flowId: number, sceneId: number) => request<ApiFlowScenario>({ method: 'POST', url: `${flowPath(flowId)}/scenarios/${sceneId}/sync` })
export const listFlowRuns = (flowId: number) => request<ApiFlowRun[]>({ url: `${flowPath(flowId)}/runs` })
export const createFlowRun = (flowId: number, payload: ApiFlowRunRequest) => request<ApiFlowRun>({ method: 'POST', url: `${flowPath(flowId)}/runs`, data: payload })
export const getFlowRun = (flowId: number, runId: number) => request<ApiFlowRun>({ url: `${flowPath(flowId)}/runs/${runId}` })
export const cancelFlowRun = (flowId: number, runId: number) => request<{message: string}>({ method: 'POST', url: `${flowPath(flowId)}/runs/${runId}/cancel` })
