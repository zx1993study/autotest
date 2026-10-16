import { request } from '../api/client'
import type { PageResult } from '../types/api'
import type { AgentTask } from '../types/agent'
import type {
  AppFeature,
  AppFeatureFilters,
  AppFeatureScenario,
  AppScenarioFilters,
  AppScenarioRun
} from '../types/app-feature'
import type { ResourcePayload, SelectOptionRecord } from '../types/resource'

function cleanParams(params: object) {
  return Object.fromEntries(Object.entries(params).filter(([, value]) => value != null && value !== ''))
}

export function listAppFeatures(filters: AppFeatureFilters = {}, signal?: AbortSignal) {
  return request<PageResult<AppFeature>>({
    method: 'GET',
    url: '/app-testing/features',
    signal,
    params: cleanParams(filters)
  })
}

export function getAppFeature(featureId: number) {
  return request<AppFeature>({ method: 'GET', url: `/app-testing/features/${featureId}` })
}

export function createAppFeature(payload: ResourcePayload) {
  return request<AppFeature>({ method: 'POST', url: '/app-testing/features', data: payload })
}

export function updateAppFeature(featureId: number, payload: Partial<ResourcePayload>) {
  return request<AppFeature>({ method: 'PUT', url: `/app-testing/features/${featureId}`, data: payload })
}

export function deleteAppFeature(featureId: number) {
  return request<boolean>({ method: 'DELETE', url: `/app-testing/features/${featureId}` })
}

export function listAppFeatureScenarios(featureId: number, filters: AppScenarioFilters = {}) {
  return request<PageResult<AppFeatureScenario>>({
    method: 'GET',
    url: `/app-testing/features/${featureId}/scenarios`,
    params: cleanParams(filters)
  })
}

export function createAppFeatureScenario(featureId: number, payload: Record<string, unknown>) {
  return request<AppFeatureScenario>({
    method: 'POST',
    url: `/app-testing/features/${featureId}/scenarios`,
    data: payload
  })
}

export function generateAppScenarioFromText(featureId: number, payload: Record<string, unknown>) {
  return request<{ scenario?: AppFeatureScenario; scenario_preview?: Record<string, unknown>; generation: Record<string, unknown> }>({
    method: 'POST',
    url: `/app-testing/features/${featureId}/scenarios/generate-from-text`,
    data: payload
  })
}

export function generateAppScenarioFromRecording(featureId: number, payload: Record<string, unknown>) {
  return request<{ scenario: AppFeatureScenario; generation: Record<string, unknown> }>({
    method: 'POST',
    url: `/app-testing/features/${featureId}/scenarios/generate-from-recording`,
    data: payload
  })
}

export function getAppScenario(scenarioId: number) {
  return request<AppFeatureScenario>({ method: 'GET', url: `/app-testing/scenarios/${scenarioId}` })
}

export function updateAppScenario(scenarioId: number, payload: Record<string, unknown>) {
  return request<AppFeatureScenario>({ method: 'PUT', url: `/app-testing/scenarios/${scenarioId}`, data: payload })
}

export function updateAppScenarioInputInfo(scenarioId: number, inputInfo: Record<string, unknown>) {
  return request<AppFeatureScenario>({
    method: 'PUT',
    url: `/app-testing/scenarios/${scenarioId}/input-info`,
    data: { input_info: inputInfo }
  })
}

export function runAppScenario(scenarioId: number, payload: Record<string, unknown>) {
  return request<{ run: AppScenarioRun; execution_record: Record<string, unknown> | null; queued?: boolean; agent_task?: AgentTask }>({
    method: 'POST',
    url: `/app-testing/scenarios/${scenarioId}/run`,
    data: payload
  })
}

export function listAppScenarioRuns(scenarioId: number, page = 1, pageSize = 20) {
  return request<PageResult<AppScenarioRun>>({
    method: 'GET',
    url: `/app-testing/scenarios/${scenarioId}/runs`,
    params: { page, pageSize }
  })
}

export function listProjectOptions() {
  return request<SelectOptionRecord[]>({ method: 'GET', url: '/projects/options' })
}

export function listDeviceOptions(projectId?: number | string | null, signal?: AbortSignal) {
  return request<SelectOptionRecord[]>({
    method: 'GET',
    url: '/app-testing/devices/options',
    signal,
    params: cleanParams({ project_id: projectId, scope: 'pool' })
  })
}

export function listAiModelOptions() {
  return request<SelectOptionRecord[]>({ method: 'GET', url: '/system/model-configs/options' })
}
