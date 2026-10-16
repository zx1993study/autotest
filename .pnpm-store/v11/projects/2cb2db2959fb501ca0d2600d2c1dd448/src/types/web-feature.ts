import type { ResourceItem } from './resource'
import type { WebPageFeature, WebPageGroup, WebPageInterface } from './web-page'

export interface WebParameter {
  key: string
  label: string
  type: 'text' | 'password' | 'textarea' | 'number' | 'select' | 'multiselect' | 'date' | 'datetime' | 'boolean' | 'json' | 'manual'
  required: boolean
  required_known?: boolean
  frame_selector?: string
  options: any[]
  default_value?: any
  condition: Record<string, any>
  validation: Record<string, any>
  locator_type: string
  locator: string
  confirmed: boolean
}
export interface WebFeatureDetail {
  feature: WebPageFeature
  page: WebPageGroup | null
  parameters: WebParameter[]
  candidate: Record<string, any> | null
  screenshots: string[]
  versions: WebFunctionVersion[]
  cases: WebInputCase[]
  legacy_drafts: ResourceItem[]
  interfaces: WebPageInterface[]
  api_candidates: any[]
}
export interface WebFunctionVersion extends ResourceItem {
  data: { feature_id: number; candidate: Record<string, any>; parameters: WebParameter[]; created_at: string }
}
export interface WebInputCase extends ResourceItem {
  data: Record<string, any>
}
export interface WebFeaturePayload {
  name: string
  feature_type: string
  description: string
  status: string
  auth_id?: number | null
  parameters: WebParameter[]
  candidate?: Record<string, any> | null
  expected_revision?: number
}
