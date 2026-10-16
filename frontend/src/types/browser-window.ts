export interface BrowserWindowInfo {
  task_id: number
  node_name: string
  node_key: string
  task_status: string
  headed: boolean
  supported: boolean
  online: boolean
  can_show: boolean
  window: {
    window_id?: string
    status?: 'opening' | 'open' | 'closed' | 'unavailable'
    browser_name?: string
    label?: string
    phase?: string
    focus?: 'idle' | 'active' | 'blocked' | 'failed'
  }
  command: { id?: string; status?: string; created_at?: string }
}
