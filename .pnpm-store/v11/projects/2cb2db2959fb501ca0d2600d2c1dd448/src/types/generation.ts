import type { ResourceItem } from './resource'

export type GenerationDomain = 'API' | 'WEB' | 'APP'
export interface GenerationMessage { role: 'user' | 'assistant'; content: string; task_id?: number }
export interface GenerationStage { code: string; label: string; status: 'running' | 'success' | 'failed'; started_at: string; ended_at?: string }
export interface GenerationTask extends ResourceItem {
  data: {
    [key: string]: unknown
    domain: GenerationDomain
    source_id: number
    task_type: string
    progress?: string
    error?: string
    model_http_calls?: number
    conversation?: GenerationMessage[]
    stages?: GenerationStage[]
    parent_task_id?: number
    repair_changes?: { step: number; before: Record<string, unknown>; after: Record<string, unknown> }[]
    saved_resource?: { id: number; domain: GenerationDomain }
    result?: { candidate: Record<string, any>; questions: string[]; warnings: string[] }
    verification?: { status: string; phase: string; error?: string; result?: { records: any[] } }
  }
}
