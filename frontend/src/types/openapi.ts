export interface OpenApiImportInterface {
  id: number
  method: string
  path: string
  name: string
  field_count: number
}

export interface OpenApiImportResult {
  project_id: number
  overwrite: boolean
  interface_count: number
  field_count: number
  interfaces: OpenApiImportInterface[]
}

export interface OpenApiImportTask {
  id: number
  project_id?: number | null
  status: 'queued' | 'running' | 'success' | 'failed' | string
  data: {
    source_type?: string
    source?: string
    overwrite?: boolean
    progress?: string
    result?: OpenApiImportResult | null
    error?: string | null
  }
}
