import type { ResourceItem } from './resource'

export interface KnowledgePrincipleItem extends ResourceItem {
  data: ResourceItem['data'] & {
    knowledge_key?: string
    principle_code?: string
    kind?: string
    content?: string
  }
}

export interface KnowledgePlanGenerationPayload {
  project_id: number
  plan_name: string
  requirement_title: string
  requirement_document: string
  principle_ids: number[]
  test_rounds: number
}

export interface KnowledgePlanGenerationResult {
  plan_id: number
  generated_case_count: number
}

export interface KnowledgeSeedResult {
  inserted_count: number
  updated_count: number
  skipped_count: number
  deleted_count: number
  total_count: number
}
