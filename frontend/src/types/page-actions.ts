export interface PageAction {
  label: string
  path: string
  type?: 'request' | 'custom' | 'route'
  name?: string
  payload?: Record<string, unknown>
  selectedKey?: string
  reload?: boolean
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
}
