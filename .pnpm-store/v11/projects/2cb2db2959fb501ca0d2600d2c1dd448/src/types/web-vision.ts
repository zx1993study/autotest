export interface WebVisionRequest {
  project_id: number
  page_id: number
  vision_model_id: number | null
  headless: boolean
  node_key?: string
  wait_for_login: boolean
  reuse_login: boolean
  max_functions: number
  include_destructive: boolean
  user_prompt?: string
}

export interface WebVisionSubmission {
  task_id: number
  agent_task_id?: number | null
  model_name?: string
  message?: string
}

export interface VisionModelCheck {
  model_id: number
  model_name: string
  healthy: boolean
  message: string
  model_http_calls: number
  elapsed_sec: number
}
