import { request } from '../api/client'
import type { PageResult } from '../types/api'
import type { ResourceItem, ResourcePayload, SelectOptionRecord } from '../types/resource'

export function listResources(path: string, params: Record<string, unknown> = {}) {
  return request<PageResult<ResourceItem>>({ method: 'GET', url: path, params })
}

export function getResource(path: string, id: number) {
  return request<ResourceItem>({ method: 'GET', url: `${path}/${id}` })
}

export function createResource(path: string, payload: ResourcePayload) {
  return request<ResourceItem>({ method: 'POST', url: path, data: payload })
}

export function batchCreateResources(path: string, items: ResourcePayload[]) {
  return request<ResourceItem[]>({ method: 'POST', url: `${path}/batch-create`, data: { items } })
}

export function updateResource(path: string, id: number, payload: Partial<ResourcePayload>) {
  return request<ResourceItem>({ method: 'PUT', url: `${path}/${id}`, data: payload })
}

export function deleteResource(path: string, id: number) {
  return request<boolean>({ method: 'DELETE', url: `${path}/${id}` })
}

export function batchDeleteResources(path: string, ids: number[]) {
  return request<{ deleted_count: number }>({
    method: 'POST',
    url: `${path}/batch-delete`,
    data: { ids }
  })
}

export function postAction<T = unknown>(path: string, payload: Record<string, unknown>) {
  return request<T>({ method: 'POST', url: path, data: payload })
}

export function listRemoteOptions(path: string, params: Record<string, unknown> = {}) {
  return request<SelectOptionRecord[]>({ method: 'GET', url: path, params })
}

const remoteOptionsCache = new Map<string, SelectOptionRecord[]>()

export function remoteOptionsCacheKey(path: string, params: Record<string, unknown> = {}) {
  const normalizedParams = Object.entries(params)
    .filter(([, value]) => value != null && value !== '')
    .sort(([left], [right]) => left.localeCompare(right))
  return `${path}?${JSON.stringify(normalizedParams)}`
}

export async function listRemoteOptionsCached(
  path: string,
  params: Record<string, unknown> = {}
) {
  const key = remoteOptionsCacheKey(path, params)
  const cached = remoteOptionsCache.get(key)
  if (cached) {
    return cached
  }
  const rows = await listRemoteOptions(path, params)
  remoteOptionsCache.set(key, rows)
  return rows
}

export function clearRemoteOptionsCache(path?: string) {
  if (!path) {
    remoteOptionsCache.clear()
    return
  }
  for (const key of remoteOptionsCache.keys()) {
    if (key.startsWith(`${path}?`)) {
      remoteOptionsCache.delete(key)
    }
  }
}
