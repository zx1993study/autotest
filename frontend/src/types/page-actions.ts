export interface PageAction {
  label: string
  path: string
  type?: 'request' | 'custom' | 'route'
  name?: string
  payload?: Record<string, unknown>
  selectedKey?: string
  reload?: boolean
  feedback?: 'modal' | 'toast'
  successTitle?: string
  successMessage?: string
  awaitAgentTasks?: boolean
  pollTask?: {
    path: string
    idKey?: string
    intervalMs?: number
    timeoutMs?: number
  }
  enabledWhen?: {
    key: string
    value: unknown
  }
  disabledWhen?: {
    key: string
    value: unknown | unknown[]
  }
  activeWhen?: {
    key: string
    value: unknown | unknown[]
  }
}
