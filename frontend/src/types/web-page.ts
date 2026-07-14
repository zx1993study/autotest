import type { ResourceItem } from './resource'

export interface WebScriptParseResult {
  page_id: number
  element_count: number
  created_count?: number
  updated_count?: number
  skipped_count?: number
  existing_strategy?: string
  elements: ResourceItem[]
  skipped_elements?: Array<{ name: string; data?: Record<string, unknown> }>
}

export interface WebCodegenSession {
  session_id: string
  status: string
  script_path: string
  return_code?: number | null
  script_exists?: boolean
  script_text?: string
  browser_running?: boolean
  ended_by_browser_close?: boolean
  stopped_by_request?: boolean
  metadata?: Record<string, unknown>
}

export interface WebCodegenStartOptions {
  projectId?: number
  featureType?: string
  featureName?: string
}
