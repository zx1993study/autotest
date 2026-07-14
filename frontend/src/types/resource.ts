export interface ResourceItem {
  id: number
  name: string
  project_id?: number | null
  description?: string | null
  status: string
  data: Record<string, unknown>
  created_at: string
  updated_at: string
  [key: string]: unknown
}

export interface ResourcePayload {
  name: string
  project_id?: number | null
  description?: string | null
  status?: string
  data?: Record<string, unknown>
  [key: string]: unknown
}

export interface ProjectOption {
  id: number
  name: string
  base_url: string
}

export interface SelectOptionRecord {
  id: number
  name?: string
  base_url?: string
  project_id?: number | null
  method?: string
  path?: string
  [key: string]: unknown
}
