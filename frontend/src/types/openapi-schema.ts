import type { ResourceItem } from './resource'

export type OpenApiGenerationStrategy = 'normal' | 'required' | 'boundary' | 'enum' | 'format' | 'type' | 'auth'
export type OpenApiGenerationAction = 'new' | 'update' | 'unchanged'

export interface OpenApiSchemaSnapshot extends ResourceItem {
  data: {
    schema_hash?: string
    openapi_version?: string
    operation_count?: number
    source_type?: string
    source?: string
    [key: string]: unknown
  }
}

export interface OpenApiCaseGenerationPayload {
  project_id: number
  snapshot_id?: number
  source_ids: number[]
  strategies: OpenApiGenerationStrategy[]
  strategy_ids: number[]
  selected_fingerprints?: string[]
  max_cases: number
}

export interface OpenApiCasePreviewItem {
  fingerprint: string
  generation_key: string
  source_id: number
  source_name: string
  name: string
  category: string
  strategy: OpenApiGenerationStrategy | 'knowledge'
  field?: string
  variant?: string
  method: string
  path: string
  assertions: Array<Record<string, unknown>>
  action: OpenApiGenerationAction
  existing_draft_id?: number
}

export interface OpenApiCasePreview {
  snapshot: {
    id: number
    name?: string
    schema_hash?: string
    openapi_version?: string
    operation_count?: number
    source_type?: string
    source?: string
  }
  total: number
  truncated: boolean
  summary: Record<OpenApiGenerationAction, number>
  items: OpenApiCasePreviewItem[]
}

export interface OpenApiCaseGenerationResult {
  snapshot: OpenApiCasePreview['snapshot']
  selected_count: number
  draft_count: number
  created_count: number
  updated_count: number
  skipped_count: number
  truncated: boolean
  draft_ids: number[]
}
