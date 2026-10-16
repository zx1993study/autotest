import { request } from '../api/client'
import type { ResourceItem } from '../types/resource'
import type { WebFeatureDetail, WebFeaturePayload } from '../types/web-feature'

const root = '/web-testing/features'
export const getWebFeature = (id: number) => request<WebFeatureDetail>({ method: 'GET', url: `${root}/${id}` })
export const saveWebFeature = (groupId: number, value: WebFeaturePayload, id?: number) => request<ResourceItem>({ method: id ? 'PUT' : 'POST', url: `/web-testing/page-groups/${groupId}/features${id ? `/${id}` : ''}`, data: value })
export const deleteWebFeature = (id: number) => request<boolean>({ method: 'DELETE', url: `${root}/${id}` })
export const featureAction = <T = any>(id: number, action: string, data: Record<string, any> = {}) => request<T>({ method: 'POST', url: `${root}/${id}/${action}`, data })
export const saveWebInputCase = (id: number, value: Record<string, any>, caseId?: number) => request<ResourceItem>({ method: caseId ? 'PUT' : 'POST', url: `${root}/${id}/input-cases${caseId ? `/${caseId}` : ''}`, data: value })
export const deleteWebInputCase = (id: number, caseId: number) => request<boolean>({ method: 'DELETE', url: `${root}/${id}/input-cases/${caseId}` })
export const webOperationControl = (taskId: number, action: 'continue' | 'cancel' | 'stop', nonce = '') => request({ method: 'POST', url: `/agent/tasks/${taskId}/web-control`, data: { action, nonce } })
export const exportWebScript = (id: number, versionId?: number) => request<{ bundle_filename: string; bundle_base64: string }>({ method: 'GET', url: `${root}/${id}/script`, params: { version_id: versionId } })
