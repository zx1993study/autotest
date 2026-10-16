export interface ApiModuleSummary {
  id: number
  key: string
  name: string
  description?: string | null
  status: string
  interface_count: number
  method_counts: Record<string, number>
  deprecated_count: number
  disabled_count: number
  updated_at: string
}
export interface ApiModuleOption {
  id: number
  project_id: number
  name: string
  key: string
}

export interface ApiModuleChange {
  id: number
  name: string
  deleted: boolean
}

export interface ApiModulePayload {
  project_id: number
  name: string
  description: string | null
}

export interface ApiAuthOption {
  id: number
  name: string
}

