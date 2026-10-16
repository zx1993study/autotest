import { request } from '../api/client'
import type { PageResult } from '../types/api'
import type { ResourceItem, ResourcePayload, SelectOptionRecord } from '../types/resource'

export function listResources(path: string, params: Record<string, unknown> = {}, signal?: AbortSignal) {
  return request<PageResult<ResourceItem>>({ method: 'GET', url: path, params, signal })
}

export function getResource(path: string, id: number) {
  return request<ResourceItem>({ method: 'GET', url: `${path}/${id}` })
}

export function createResource(path: string, payload: ResourcePayload) {
  return mutateResource<ResourceItem>('POST', path, payload)
}

export function batchCreateResources(path: string, items: ResourcePayload[]) {
  return mutateResource<ResourceItem[]>('POST', `${path}/batch-create`, { items })
}

export function updateResource(path: string, id: number, payload: Partial<ResourcePayload>) {
  return mutateResource<ResourceItem>('PUT', `${path}/${id}`, payload)
}

export function deleteResource(path: string, id: number) {
  return mutateResource<boolean>('DELETE', `${path}/${id}`)
}

export function batchDeleteResources(path: string, ids: number[]) {
  return mutateResource<{ deleted_count: number }>('POST', `${path}/batch-delete`, { ids })
}

async function mutateResource<T>(method: 'POST' | 'PUT' | 'DELETE', url: string, data?: unknown) {
  const result = await request<T>({ method, url, data })
  clearRemoteOptionsCache()
  return result
}

export function postAction<T = unknown>(path: string, payload: Record<string, unknown>) {
  return request<T>({ method: 'POST', url: path, data: payload })
}

export function listRemoteOptions(path: string, params: Record<string, unknown> = {}) {
  return request<SelectOptionRecord[]>({ method: 'GET', url: path, params })
}

interface OptionsCacheEntry { promise: Promise<SelectOptionRecord[]>; expiresAt: number }
const remoteOptionsCache = new Map<string, OptionsCacheEntry>()
const OPTIONS_CACHE_TTL = 30_000
const OPTIONS_CACHE_LIMIT = 128

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
  if (cached && cached.expiresAt > Date.now()) {
    return cached.promise
  }
  const entry: OptionsCacheEntry = { expiresAt: Infinity, promise: Promise.resolve([]) }
  entry.promise = listRemoteOptions(path, params).then(rows => {
    entry.expiresAt = Date.now() + OPTIONS_CACHE_TTL
    return rows
  }).catch(error => {
    if (remoteOptionsCache.get(key) === entry) remoteOptionsCache.delete(key)
    throw error
  })
  remoteOptionsCache.set(key, entry)
  while (remoteOptionsCache.size > OPTIONS_CACHE_LIMIT) {
    remoteOptionsCache.delete(remoteOptionsCache.keys().next().value!)
  }
  return entry.promise
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
