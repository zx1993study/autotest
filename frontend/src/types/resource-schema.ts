export type ResourceFieldType = 'text' | 'textarea' | 'number' | 'select' | 'multiselect' | 'checkbox' | 'json'

export interface ResourceOption {
  label: string
  value: string | number
  isDefault?: boolean
}

export interface RemoteOptionsConfig {
  path: string
  valueKey: string
  labelKeys: string[]
  params?: Record<string, string | number | boolean>
  dependsOn?: Record<string, string>
}

export interface ResourceVisibleCondition {
  key: string
  value: unknown | unknown[]
}

export interface ResourceField {
  key: string
  label: string
  type?: ResourceFieldType
  required?: boolean
  hidden?: boolean
  placeholder?: string
  options?: ResourceOption[]
  remoteOptions?: RemoteOptionsConfig
  defaultValue?: unknown
  visibleWhen?: ResourceVisibleCondition | { all: ResourceVisibleCondition[] }
  full?: boolean
  rows?: number
}

export interface ResourceColumn {
  key: string
  label: string
  width?: string
}
