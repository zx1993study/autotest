import type { ResourceItem } from './resource'

export interface WebPageGroup extends ResourceItem {
  feature_count: number
  interface_count: number
}

export interface WebPageFeature extends ResourceItem {
  data: Record<string, any>
  element_count: number
  case_count: number
  parameter_count?: number
  script_status?: string
}

export interface WebPageInterface extends ResourceItem {
  relation_id: number
  relation_source: 'manual' | 'network' | 'ai' | string
  relation_feature_id?: number | null
  relation_feature_name?: string | null
}

export interface WebPageGroupPayload {
  name: string
  project_id: number
  route?: string
  url?: string
  auth_id?: number | null
  description?: string
  status?: string
}
