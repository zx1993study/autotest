import { request } from '../api/client'
import type { PageResult } from '../types/api'
import type { ApiAuthOption, ApiModuleOption, ApiModulePayload, ApiModuleSummary } from '../types/api-interface'
import type { ResourceItem } from '../types/resource'

export function listApiModules(params: {
  project_id: number
  keyword?: string
  page: number
  pageSize: number
}, signal?: AbortSignal) {
  return request<PageResult<ApiModuleSummary>>({
    method: 'GET',
    url: '/api-testing/interfaces/modules',
    signal,
    params
  })
}

export function getApiModule(projectId: number, moduleId: number) {
  return request<ResourceItem>({
    method: 'GET',
    url: `/api-testing/interfaces/modules/${moduleId}`,
    params: { project_id: projectId }
  })
}

const modulePath = '/api-testing/interfaces/modules'

export function listApiAuthOptions(projectId: number) {
  return request<ApiAuthOption[]>({ method: 'GET', url: '/project-auth/options', params: { project_id: projectId, login_case_type: 'API' } })
}

export function listApiModuleOptions(projectId: number) {
  return request<ApiModuleOption[]>({ method: 'GET', url: `${modulePath}/options`, params: { project_id: projectId } })
}

export function createApiModule(payload: ApiModulePayload) {
  return request<ResourceItem>({ method: 'POST', url: modulePath, data: payload })
}

export function updateApiModule(id: number, payload: ApiModulePayload) {
  return request<ResourceItem>({ method: 'PUT', url: `${modulePath}/${id}`, data: payload })
}

export function deleteApiModule(projectId: number, id: number) {
  return request<boolean>({ method: 'DELETE', url: `${modulePath}/${id}`, params: { project_id: projectId } })
}
