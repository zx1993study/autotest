import type { ResourceItem, SelectOptionRecord } from './resource'

export interface AppFeature extends ResourceItem {
  scenario_count?: number
  last_run_status?: string | null
  last_run_at?: string | null
}

export interface AppFeatureScenario extends ResourceItem {
  step_count?: number
  input_count?: number
  source_type?: string
  last_run_status?: string | null
  last_video_url?: string | null
}

export interface AppScenarioRun extends ResourceItem {}

export interface AppFeatureFilters {
  project_id?: number | string | null
  device_id?: number | string | null
  keyword?: string
  status?: string
  page?: number
  pageSize?: number
}

export interface AppScenarioFilters {
  device_id?: number | string | null
  keyword?: string
  status?: string
  source_type?: string
  page?: number
  pageSize?: number
}

export interface AppFeatureOptions {
  projects: SelectOptionRecord[]
  devices: SelectOptionRecord[]
}
