<template>
  <div v-if="visible" class="modal-backdrop" @click.self="close">
    <section class="modal-panel api-case-form-dialog" role="dialog" aria-modal="true" aria-labelledby="api-case-form-title">
      <header class="modal-header">
        <h3 id="api-case-form-title">{{ dialogTitle }}</h3>
        <button class="modal-close" type="button" aria-label="关闭" :disabled="saving" @click="close">×</button>
      </header>
      <form class="modal-form" @submit.prevent="save">
        <div class="request-identity"><b>{{ interfaceItem.data.method }}</b><code>{{ interfaceItem.data.path }}</code></div>
        <div class="form-grid">
          <label class="field full"><span>用例名称<b>*</b></span><input v-model.trim="form.name" required maxlength="128" autofocus /></label>
          <label class="field"><span>优先级</span><select v-model="form.priority" aria-label="优先级"><option v-for="value in ['P0', 'P1', 'P2', 'P3']" :key="value">{{ value }}</option></select></label>
          <label class="field"><span>状态</span><select v-model="form.status" aria-label="状态"><option value="active">启用</option><option value="disabled">停用</option></select></label>
          <label class="field"><span>认证方式</span><select v-model="form.authMode" aria-label="认证方式"><option value="inherit">继承接口认证</option><option value="token">指定 Token</option><option value="none">不使用认证</option></select></label>
          <label v-if="form.authMode === 'token'" class="field"><span>Token / 鉴权信息<b>*</b></span><select v-model="form.authId" required :disabled="authLoading" aria-label="Token / 鉴权信息"><option value="">{{ authLoading ? '加载中...' : '请选择项目 Token' }}</option><option v-for="option in authOptions" :key="option.id" :value="String(option.id)">{{ option.name || `认证 #${option.id}` }}</option><option v-if="form.authId && !authOptions.some(option => String(option.id) === form.authId)" :value="form.authId">认证 #{{ form.authId }}（不可用）</option></select></label>
          <div v-else-if="form.authMode === 'inherit'" class="field inherited-auth"><span>接口认证</span><strong>{{ inheritedAuthName }}</strong></div>
          <div v-if="authError" class="field full auth-error" role="alert"><span>{{ authError }}</span><button type="button" :disabled="authLoading" @click="loadAuthOptions">重试</button></div>
          <div class="field full"><span>请求参数 JSON</span><textarea v-model="form.params" class="json-input" rows="6" spellcheck="false" aria-label="请求参数 JSON"></textarea><DynamicValueTools v-model="form.params" label="请求参数" :variables="variableDefinitions" /></div>
        </div>
        <details class="request-options">
          <summary>请求配置</summary>
          <div class="form-grid">
            <label class="field full"><span>Content-Type</span><input v-model.trim="form.contentType" /></label>
            <div class="field"><span>请求头 JSON</span><textarea v-model="form.headers" class="json-input" rows="4" spellcheck="false" aria-label="请求头 JSON"></textarea><DynamicValueTools v-model="form.headers" label="请求头" :variables="variableDefinitions" /></div>
            <div class="field"><span>请求体 JSON</span><textarea v-model="form.body" class="json-input" rows="4" spellcheck="false" aria-label="请求体 JSON"></textarea><DynamicValueTools v-model="form.body" label="请求体" :variables="variableDefinitions" /></div>
          </div>
        </details>
        <details class="request-options">
          <summary>命名变量</summary>
          <label class="field"><span>变量定义 JSON</span><textarea v-model="form.variables" class="json-input" rows="4" spellcheck="false" aria-label="变量定义 JSON"></textarea></label>
        </details>
        <section class="assertion-section" aria-labelledby="case-assertion-title">
          <header><h4 id="case-assertion-title">响应断言</h4><button type="button" @click="assertions.push({ type: 'status', expected: '200' })">添加断言</button></header>
          <div v-for="(assertion, index) in assertions" :key="index" class="assertion-row">
            <select v-model="assertion.type" :aria-label="`断言 ${index + 1} 类型`">
              <option v-for="option in assertionOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
              <option v-if="!assertionOptions.some(option => option.value === assertion.type)" :value="assertion.type">{{ assertion.type }}</option>
            </select>
            <input v-model="assertion.expected" :aria-label="`断言 ${index + 1} 预期值`" :placeholder="assertionPlaceholder(assertion.type)" :required="!assertion.original || assertion.original.expected != null" />
            <button type="button" class="remove-assertion" :aria-label="`删除断言 ${index + 1}`" title="删除断言" @click="assertions.splice(index, 1)">×</button>
          </div>
        </section>
        <label class="field"><span>说明</span><textarea v-model.trim="form.description" rows="2" maxlength="2000"></textarea></label>
        <p v-if="error" class="form-error" role="alert">{{ error }}</p>
        <footer class="modal-actions">
          <button type="button" :disabled="saving" @click="close">取消</button>
          <button type="submit" :disabled="saving">{{ saving ? '保存中...' : copying ? '保存为新用例' : '保存用例' }}</button>
        </footer>
      </form>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import DynamicValueTools from '../common/DynamicValueTools.vue'
import { previewDynamicValue } from '../../services/dynamic-value.service'
import { createResource, listRemoteOptions, updateResource } from '../../services/resource.service'
import type { ResourceItem, ResourcePayload, SelectOptionRecord } from '../../types/resource'

const props = withDefaults(defineProps<{ visible: boolean; interfaceItem: ResourceItem; fields: ResourceItem[]; item?: ResourceItem | null; copying?: boolean }>(), { copying: false })
const emit = defineEmits<{ close: []; saved: [item: ResourceItem] }>()
const dialogTitle = computed(() => props.copying ? '复制正式用例' : props.item ? '编辑正式用例' : '新增正式用例')
const saving = ref(false)
const error = ref('')
const authOptions = ref<SelectOptionRecord[]>([])
const authLoading = ref(false)
const authError = ref('')
let authRequestId = 0
const form = reactive({ name: '', priority: 'P2', status: 'active', authMode: 'inherit', authId: '', params: '{}', headers: '{}', body: '', variables: '{}', contentType: '', description: '' })
const inheritedAuthName = computed(() => {
  const id = props.interfaceItem.data.auth_id
  if (!id) return '未配置'
  return authOptions.value.find(option => String(option.id) === String(id))?.name || `认证 #${id}`
})
const variableDefinitions = computed<Record<string, unknown>>(() => { try { return objectJson(form.variables, '变量定义') } catch { return {} } })
const assertions = ref<Array<{ type: string; expected: string; original?: Record<string, unknown> }>>([])
const assertionOptions = [
  { value: 'status', label: 'HTTP 状态码' },
  { value: 'status_in', label: 'HTTP 状态码集合' },
  { value: 'body_contains', label: '响应包含文本' },
  { value: 'response_time', label: '最大耗时 (ms)' },
  { value: 'content_type_in', label: '响应内容类型' }
]

watch(() => props.visible, visible => {
  if (!visible) return
  const original = props.item?.data || {}
  const legacy = original.request && typeof original.request === 'object' && !Array.isArray(original.request) ? original.request : {}
  const data = { ...legacy, ...original }
  const defaults: Record<string, unknown> = {}
  for (const field of props.fields) {
    if (field.status === 'disabled') continue
    const value = field.data.example ?? field.data.default_value
    if (value != null && value !== '') defaults[String(field.data.name || field.name)] = typedValue(value, field.data.field_type || field.data.type)
  }
  const suffix = ' - 副本'
  form.name = props.copying && props.item ? `${props.item.name.slice(0, 128 - suffix.length)}${suffix}` : props.item?.name || ''
  form.priority = String(data.priority || 'P2')
  form.status = props.item?.status || 'active'
  form.authMode = data.skip_auth ? 'none' : data.auth_id ? 'token' : 'inherit'
  form.authId = data.auth_id ? String(data.auth_id) : ''
  form.params = stringify(data.params ?? defaults)
  form.variables = stringify(data.variables ?? {})
  form.headers = stringify(data.headers ?? {})
  form.body = data.body == null ? '' : stringify(data.body)
  form.contentType = String(data.content_type || props.interfaceItem.data.content_type || '')
  form.description = props.item?.description || ''
  const savedAssertions = Array.isArray(props.item?.assertions) ? props.item.assertions : null
  assertions.value = savedAssertions ? savedAssertions.map(row => {
    const assertion = row as Record<string, unknown>
    return { type: String(assertion.type || 'status'), expected: typeof assertion.expected === 'string' ? assertion.expected : JSON.stringify(assertion.expected ?? ''), original: assertion }
  }) : [{ type: 'status', expected: '200' }]
  error.value = ''
  void loadAuthOptions()
}, { immediate: true })

watch(() => props.interfaceItem.project_id, () => { if (props.visible) void loadAuthOptions() })

async function loadAuthOptions() {
  const requestId = ++authRequestId
  authLoading.value = true
  authError.value = ''
  authOptions.value = []
  try {
    const options = await listRemoteOptions('/project-auth/options', { project_id: props.interfaceItem.project_id, login_case_type: 'API' })
    if (requestId === authRequestId) authOptions.value = options
  } catch (cause) {
    if (requestId === authRequestId) authError.value = cause instanceof Error ? cause.message : '项目认证加载失败'
  } finally {
    if (requestId === authRequestId) authLoading.value = false
  }
}

function typedValue(value: unknown, type: unknown) {
  if (typeof value !== 'string' || type === 'string') return value
  try { return JSON.parse(value) } catch { return value }
}

function stringify(value: unknown) { return JSON.stringify(value, null, 2) }

function objectJson(value: string, label: string): Record<string, unknown> {
  let result: unknown
  try { result = JSON.parse(value) } catch { throw new Error(`${label}不是有效的 JSON`) }
  if (!result || typeof result !== 'object' || Array.isArray(result)) throw new Error(`${label}必须是 JSON 对象`)
  return result as Record<string, unknown>
}

function assertionPlaceholder(type: string) {
  return ({ status: '200', status_in: '[200, 201, "2XX"]', body_contains: '预期文本', response_time: '3000', content_type_in: '["application/json"]' } as Record<string, string>)[type] || '预期值'
}

function assertionPayload(row: { type: string; expected: string; original?: Record<string, unknown> }, index: number) {
  const raw = row.expected.trim()
  if (!raw && row.original && row.original.expected == null) return { ...row.original, type: row.type }
  if (!raw) throw new Error(`请填写断言 ${index + 1} 的预期值`)
  let expected: unknown = raw
  if (row.type === 'status' || row.type === 'response_time') {
    expected = Number(raw)
    if (!Number.isInteger(expected) || Number(expected) < (row.type === 'status' ? 100 : 1) || (row.type === 'status' && Number(expected) > 599)) throw new Error(`断言 ${index + 1} 的预期值不合法`)
  } else if (row.type === 'status_in' || row.type === 'content_type_in') {
    try { expected = JSON.parse(raw) } catch { throw new Error(`断言 ${index + 1} 的预期值必须是 JSON 数组`) }
    if (!Array.isArray(expected) || !expected.length) throw new Error(`断言 ${index + 1} 的预期值必须是非空数组`)
  }
  return { ...row.original, type: row.type, expected }
}

function initialPayloadData(): Record<string, unknown> {
  const data = { ...props.item?.data }
  if (!props.copying) return data
  const metadataKeys = ['openapi_generation', 'generated_plan_id', 'ai_task_id', 'project_name', 'api_method', 'api_path']
  for (const key of metadataKeys) delete data[key]
  if (data.request && typeof data.request === 'object' && !Array.isArray(data.request)) {
    const request = { ...data.request } as Record<string, unknown>
    for (const key of metadataKeys) delete request[key]
    data.request = request
  }
  return data
}

async function save() {
  if (saving.value) return
  error.value = ''
  try {
    if (!form.name) throw new Error('请填写用例名称')
    if (!assertions.value.length) throw new Error('请添加至少一条响应断言')
    if (form.authMode === 'token' && (authLoading.value || !authOptions.value.some(option => String(option.id) === form.authId))) throw new Error('请选择有效的项目 Token')
    const data: Record<string, unknown> = {
      ...initialPayloadData(),
      case_type: 'API', priority: form.priority, category: props.item?.data.category || 'normal',
      method: props.interfaceItem.data.method, path: props.interfaceItem.data.path,
      auth_id: form.authMode === 'token' ? Number(form.authId) : null, skip_auth: form.authMode === 'none',
      content_type: form.contentType, params: objectJson(form.params, '请求参数'), headers: objectJson(form.headers, '请求头'), variables: objectJson(form.variables, '变量定义')
    }
    if (form.body.trim()) {
      try { data.body = JSON.parse(form.body) } catch { throw new Error('请求体不是有效的 JSON') }
    } else {
      delete data.body
    }
    const payload: ResourcePayload = {
      name: form.name, project_id: props.interfaceItem.project_id, source_id: props.interfaceItem.id,
      status: form.status, description: form.description || null, data,
      assertions: assertions.value.map(assertionPayload), steps: props.item?.steps || [], strategy_ids: props.item?.strategy_ids || []
    }
    saving.value = true
    await previewDynamicValue({ params: data.params, headers: data.headers, body: data.body }, data.variables as Record<string, unknown>)
    const saved = props.item && !props.copying
      ? await updateResource('/api-testing/cases', props.item.id, payload)
      : await createResource('/api-testing/cases', payload)
    emit('saved', saved)
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '用例保存失败'
  } finally {
    saving.value = false
  }
}

function close() { if (!saving.value) emit('close') }
</script>

<style scoped>
.modal-backdrop { z-index: 60; }
.api-case-form-dialog { width: min(780px, calc(100vw - 32px)); max-height: calc(100dvh - 32px); overflow-y: auto; }
.request-identity { display: flex; flex-wrap: wrap; gap: 10px; min-width: 0; color: #0f6073; font-size: 13px; }
.request-identity code { overflow-wrap: anywhere; }
.json-input { font-family: Consolas, monospace; resize: vertical; }
.inherited-auth strong { display: flex; align-items: center; min-height: 38px; font-size: 13px; font-weight: 500; }
.auth-error { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; color: #b42318; }
.request-options summary { cursor: pointer; color: #39465e; font-size: 14px; }
.request-options .form-grid { margin-top: 12px; }
.assertion-section { display: grid; gap: 10px; }
.assertion-section header { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 10px; }
.assertion-section h4 { margin: 0; font-size: 14px; }
.assertion-row { display: grid; grid-template-columns: 180px minmax(0, 1fr) 34px; gap: 8px; }
.assertion-row input, .assertion-row select { width: 100%; min-width: 0; }
.remove-assertion { height: 38px; padding: 0; font-size: 22px; }
.modal-actions { padding: 12px 0 0; }
@media (max-width: 600px) {
  .form-grid { grid-template-columns: minmax(0, 1fr); }
  .assertion-row { grid-template-columns: minmax(0, 1fr) 34px; }
  .assertion-row select { grid-column: 1 / -1; }
}
</style>
