import { request } from '../api/client'
import type { GenerationTask, GenerationDomain } from '../types/generation'
export type { GenerationDomain } from '../types/generation'

export interface ReferenceImage { image_base64: string; description: string }
export const generationPath = '/execution/generation-tasks'
export function submitGeneration(domain: GenerationDomain, data: Record<string, unknown>) {
  return request<{ task_id: number }>({ method: 'POST', url: `/${domain.toLowerCase()}-testing/generation`, data })
}
export function getGeneration(id: number) {
  return request<GenerationTask>({ method: 'GET', url: `${generationPath}/${id}` })
}
export function generationAction(id: number, action: string, data: Record<string, unknown>) {
  return request<Record<string, any>>({ method: 'POST', url: `${generationPath}/${id}/${action}`, data })
}
export function generationScript(id: number) {
  return request<{ filename: string; script: string; bundle_filename: string; bundle_base64: string }>({ method: 'GET', url: `${generationPath}/${id}/script` })
}
