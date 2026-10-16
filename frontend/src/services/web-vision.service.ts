import { request } from '../api/client'
import type { ResourceItem } from '../types/resource'
import type { VisionModelCheck, WebVisionRequest, WebVisionSubmission } from '../types/web-vision'

const path = '/web-testing/vision-discovery'

export function submitWebVision(payload: WebVisionRequest) {
  return request<WebVisionSubmission>({ method: 'POST', url: path, data: payload })
}

export function activeWebVision(projectId: number, pageId: number) {
  return request<WebVisionSubmission | null>({ method: 'GET', url: `${path}/active`, params: { project_id: projectId, page_id: pageId } })
}

export function getWebVisionTask(taskId: number) {
  return request<ResourceItem>({ method: 'GET', url: `/execution/generation-tasks/${taskId}` })
}

export function confirmWebVisionLogin(agentTaskId: number, action: 'continue' | 'cancel') {
  return request<{ accepted: boolean }>({ method: 'POST', url: `${path}/tasks/${agentTaskId}/login`, data: { action } })
}

export function cancelWebVision(taskId: number) {
  return request<{ accepted: boolean }>({ method: 'POST', url: `${path}/${taskId}/cancel` })
}

export function checkVisionModel(modelId: number | null) {
  return request<VisionModelCheck>({ method: 'POST', url: `${path}/model-check`, data: { model_id: modelId }, timeout: 45_000 })
}
