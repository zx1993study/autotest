import { request } from '../api/client'
import type { PageResult } from '../types/api'
import type { ResourceItem } from '../types/resource'
import type {
  WebPageFeature,
  WebPageGroup,
  WebPageGroupPayload,
  WebPageInterface
} from '../types/web-page'

const PAGE_GROUP_PATH = '/web-testing/page-groups'

export function listWebPageGroups(params: {
  project_id: number
  keyword?: string
  status?: string
  page: number
  pageSize: number
}, signal?: AbortSignal) {
  return request<PageResult<WebPageGroup>>({ method: 'GET', url: PAGE_GROUP_PATH, params, signal })
}

export function getWebPageGroup(groupId: number) {
  return request<WebPageGroup>({ method: 'GET', url: `${PAGE_GROUP_PATH}/${groupId}` })
}

export function createWebPageGroup(payload: WebPageGroupPayload) {
  return request<WebPageGroup>({ method: 'POST', url: PAGE_GROUP_PATH, data: payload })
}

export function updateWebPageGroup(groupId: number, payload: Partial<WebPageGroupPayload>) {
  return request<WebPageGroup>({ method: 'PUT', url: `${PAGE_GROUP_PATH}/${groupId}`, data: payload })
}

export function listWebPageFeatures(groupId: number, params: {
  keyword?: string
  status?: string
  feature_type?: string
  script_status?: string
  page: number
  pageSize: number
}, signal?: AbortSignal) {
  return request<PageResult<WebPageFeature>>({
    method: 'GET',
    url: `${PAGE_GROUP_PATH}/${groupId}/features`,
    signal,
    params
  })
}

export function listWebPageInterfaces(groupId: number, params: {
  feature_id?: number
  keyword?: string
  method?: string
  page: number
  pageSize: number
}) {
  return request<PageResult<WebPageInterface>>({
    method: 'GET',
    url: `${PAGE_GROUP_PATH}/${groupId}/interfaces`,
    params
  })
}

export function createWebPageInterfaceRelations(
  groupId: number,
  interfaceIds: number[],
  featureId?: number,
  source = 'manual'
) {
  return request<{ created_count: number; skipped_count: number; items: ResourceItem[] }>({
    method: 'POST',
    url: `${PAGE_GROUP_PATH}/${groupId}/interface-relations`,
    data: { interface_ids: interfaceIds, feature_id: featureId || null, source }
  })
}

export function deleteWebPageInterfaceRelation(groupId: number, relationId: number) {
  return request<boolean>({
    method: 'DELETE',
    url: `${PAGE_GROUP_PATH}/${groupId}/interface-relations/${relationId}`
  })
}
