import type { ResourceColumn, ResourceField } from '../types/resource-schema'
import { descriptionField, statusField, statusOptions } from './shared'

export const modelConfigFields: ResourceField[] = [
  { key: 'name', label: '模型名称', required: true, placeholder: '例如：OpenAI GPT-4.1 Mini' },
  {
    key: 'data.provider',
    label: '模型厂商',
    type: 'select',
    defaultValue: 'openai_compatible',
    options: [
      { label: 'OpenAI兼容', value: 'openai_compatible' },
      { label: 'OpenAI', value: 'openai' },
      { label: '通义千问', value: 'dashscope' },
      { label: 'DeepSeek', value: 'deepseek' },
      { label: '本地模型', value: 'local' }
    ]
  },
  { key: 'data.base_url', label: '接口地址', placeholder: '例如：https://api.openai.com/v1' },
  {
    key: 'data.api_protocol', label: '调用协议', type: 'select', defaultValue: 'chat_completions',
    options: [
      { label: 'Chat Completions', value: 'chat_completions' },
      { label: 'Responses', value: 'responses' }
    ]
  },
  { key: 'data.model', label: '模型标识', required: true, placeholder: '例如：gpt-4.1-mini' },
  { key: 'data.api_key', label: 'API Key', placeholder: '仅新建或替换时填写，平台会保存到文件' },
  { key: 'data.api_key_file', label: '密钥文件名', placeholder: '自动生成，只保存文件名' },
  { key: 'data.is_current', label: '设为当前模型', type: 'checkbox', defaultValue: false },
  { key: 'data.supports_vision', label: '支持视觉(图片输入)', type: 'checkbox', defaultValue: false },
  { key: 'data.temperature', label: '温度', type: 'number', defaultValue: 0.2 },
  {
    key: 'data.reasoning_effort', label: '推理强度', type: 'select',
    visibleWhen: { key: 'data.api_protocol', value: 'responses' },
    options: [
      { label: '默认', value: '' }, { label: '低', value: 'low' },
      { label: '中', value: 'medium' }, { label: '高', value: 'high' }
    ]
  },
  { key: 'data.timeout_sec', label: '超时秒数', type: 'number', defaultValue: 60 },
  statusField,
  descriptionField
]

export const modelConfigColumns: ResourceColumn[] = [
  { key: 'name', label: '模型名称' },
  { key: 'data.provider', label: '厂商' },
  { key: 'data.model', label: '模型' },
  { key: 'data.api_protocol', label: '协议', width: '160px' },
  { key: 'data.base_url', label: '接口地址' },
  { key: 'data.api_key_file', label: '密钥文件' },
  { key: 'data.supports_vision', label: '视觉', width: '70px' },
  { key: 'data.is_current', label: '当前模型', width: '90px' },
  { key: 'status', label: '状态', width: '90px' }
]
