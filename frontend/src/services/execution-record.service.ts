import { request } from '../api/client'
import type { ResourceItem } from '../types/resource'

export function getExecutionRecord(id: number, signal?: AbortSignal) {
  return request<ResourceItem>({ method: 'GET', url: `/reports/records/${id}`, signal })
}
