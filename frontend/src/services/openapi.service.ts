import { request } from '../api/client'
import type { OpenApiImportTask } from '../types/openapi'

export function importOpenApiFile(projectId: number, file: File, overwrite = true) {
  const formData = new FormData()
  formData.append('project_id', String(projectId))
  formData.append('overwrite', String(overwrite))
  formData.append('file', file)
  return request<OpenApiImportTask>({
    method: 'POST',
    url: '/api-testing/interfaces/import-file',
    data: formData
  })
}

export function importOpenApiUrl(projectId: number, url: string, overwrite = true) {
  return request<OpenApiImportTask>({
    method: 'POST',
    url: '/api-testing/interfaces/import-url',
    data: { project_id: projectId, url, overwrite }
  })
}

export function getOpenApiImportTask(taskId: number) {
  return request<OpenApiImportTask>({
    method: 'GET',
    url: `/api-testing/interfaces/import-tasks/${taskId}`
  })
}
