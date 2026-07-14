import { request } from '../api/client'
import type { ProjectOption } from '../types/resource'

export function listProjectOptions() {
  return request<ProjectOption[]>({ method: 'GET', url: '/projects/options' })
}
