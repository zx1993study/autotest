import type { ResourceField } from '../types/resource-schema'
import { baseColumns, descriptionField, projectIdField, statusField } from './shared'

export const defaultFields: ResourceField[] = [
  { key: 'name', label: '名称', required: true },
  projectIdField,
  statusField,
  descriptionField
]

export const defaultColumns = baseColumns

