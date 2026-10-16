import { request } from '../api/client'
import type { PageResult } from '../types/api'
import type {
  KnowledgePlanGenerationPayload,
  KnowledgePlanGenerationResult,
  KnowledgePrincipleItem,
  KnowledgeSeedResult
} from '../types/knowledge'

export async function listKnowledgePrinciples(projectId: number) {
  const result = await request<PageResult<KnowledgePrincipleItem>>({
    method: 'GET',
    url: '/project-knowledge',
    params: {
      project_id: projectId,
      domain: 'WEB',
      page: 1,
      pageSize: 200
    }
  })
  return result.items.filter(item => (
    item.status === 'active' && item.data.kind === 'test_principle'
  ))
}

export function seedKnowledgePrinciples(projectId: number, overwrite = false) {
  return request<KnowledgeSeedResult>({
    method: 'POST',
    url: '/project-knowledge/seed-defaults',
    data: { project_id: projectId, overwrite }
  })
}

export function generateKnowledgePlan(payload: KnowledgePlanGenerationPayload) {
  return request<KnowledgePlanGenerationResult>({
    method: 'POST',
    url: '/project-knowledge/generate-plan',
    data: payload
  })
}
