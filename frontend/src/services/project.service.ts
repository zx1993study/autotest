import { request } from '../api/client'
import type { ProjectOption } from '../types/resource'

export function listProjectOptions() {
  return request<ProjectOption[]>({ method: 'GET', url: '/projects/options' })
}

export function resolveDefaultProjectOption(projects: ProjectOption[]): ProjectOption | null {
  return projects.find(project => project.is_default) || projects[0] || null
}

export function resolveDefaultProjectId(projects: ProjectOption[]): number {
  return resolveDefaultProjectOption(projects)?.id || 0
}
