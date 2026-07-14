<template>
  <article class="step-card">
    <header class="step-card-header">
      <div>
        <h3>步骤 {{ index + 1 }}</h3>
        <p>{{ title || '选择 API 用例并调整本次执行参数。' }}</p>
      </div>
      <button class="danger" type="button" @click="$emit('remove', index)">删除</button>
    </header>

    <form class="step-form" @submit.prevent="$emit('save', index)">
      <div class="field-grid">
        <label class="field">
          <span>API<b>*</b></span>
          <input
            v-model.trim="draft.apiKeyword"
            class="filter-input"
            :list="`execution-flow-api-options-${draft.uid}`"
            type="search"
            placeholder="输入接口名称、方法或路径选择 API"
            :disabled="loadingOptions"
            @change="$emit('api-change', draft)"
            @input="$emit('api-change', draft)"
          />
          <datalist :id="`execution-flow-api-options-${draft.uid}`">
            <option v-for="api in apiOptions" :key="api.id" :value="apiOptionLabel(api)" />
          </datalist>
        </label>

        <label class="field">
          <span>Token</span>
          <select v-model.number="draft.selectedAuthId" :disabled="loadingOptions">
            <option :value="0">不使用鉴权</option>
            <option v-for="auth in authOptions" :key="auth.id" :value="auth.id">
              {{ auth.name || `#${auth.id}` }}
            </option>
          </select>
        </label>

        <label class="field full">
          <span>用例<b>*</b></span>
          <select
            v-model.number="draft.selectedCaseId"
            :disabled="loadingOptions"
            @change="$emit('case-change', draft)"
          >
            <option :value="0">请选择 API 用例</option>
            <option v-for="item in caseOptions" :key="item.id" :value="item.id">
              {{ caseOptionLabel(item) }}
            </option>
          </select>
        </label>
      </div>

      <label class="field full">
        <span>用例 JSON</span>
        <textarea
          v-model="draft.caseJsonText"
          class="json-editor"
          rows="14"
          spellcheck="false"
        ></textarea>
      </label>

      <p v-if="draft.formError" class="form-error">{{ draft.formError }}</p>

      <footer class="form-actions">
        <button type="submit" :disabled="draft.saving || !canSave">
          {{ draft.saving ? '保存中...' : '保存步骤' }}
        </button>
        <button class="primary" type="button" :disabled="draft.executing || !canSave" @click="$emit('run', draft)">
          {{ draft.executing ? '运行中...' : '运行' }}
        </button>
      </footer>
    </form>

    <section class="execution-result">
      <header>
        <h3>API 执行返回信息</h3>
        <span class="status-pill" :class="resultStatusClass">{{ resultStatusText }}</span>
      </header>

      <div v-if="activeRecord" class="result-content">
        <dl class="result-meta">
          <div>
            <dt>记录 ID</dt>
            <dd>#{{ activeRecord.id }}</dd>
          </div>
          <div>
            <dt>HTTP 状态</dt>
            <dd>{{ recordData.response_status ?? '-' }}</dd>
          </div>
          <div>
            <dt>耗时</dt>
            <dd>{{ formatDuration(recordData.duration_ms) }}</dd>
          </div>
          <div>
            <dt>错误</dt>
            <dd>{{ recordData.error || '-' }}</dd>
          </div>
        </dl>

        <details open class="result-block">
          <summary>响应体</summary>
          <pre>{{ responseBodyText }}</pre>
        </details>

        <details class="result-block">
          <summary>请求信息</summary>
          <pre>{{ stringifyJson(recordData.request || {}) }}</pre>
        </details>
      </div>

      <p v-else class="empty-text">运行步骤后，API 返回信息会显示在这里。</p>
    </section>
  </article>
</template>

<script setup lang="ts">
import type { ResourceItem, SelectOptionRecord } from '../../api/http'
import type { ExecutionRecord, StepDraft } from '../../types/execution-flow'

defineProps<{
  draft: StepDraft
  index: number
  loadingOptions: boolean
  authOptions: SelectOptionRecord[]
  apiOptions: SelectOptionRecord[]
  caseOptions: ResourceItem[]
  canSave: boolean
  title: string
  activeRecord: ExecutionRecord | null
  recordData: Record<string, unknown>
  responseBodyText: string
  resultStatusText: string
  resultStatusClass: string
  apiOptionLabel: (api: SelectOptionRecord) => string
  caseOptionLabel: (item: ResourceItem) => string
  formatDuration: (value: unknown) => string
  stringifyJson: (value: unknown) => string
}>()

defineEmits<{
  remove: [index: number]
  save: [index: number]
  run: [draft: StepDraft]
  'api-change': [draft: StepDraft]
  'case-change': [draft: StepDraft]
}>()
</script>

<style scoped>
.step-card {
  display: flex;
  flex: 0 0 min(520px, calc(100vw - 64px));
  flex-direction: column;
  gap: 14px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  padding: 16px;
}

.step-card-header,
.execution-result header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.step-card-header h3,
.execution-result h3 {
  margin: 0;
  color: #111827;
  font-size: 17px;
}

.step-card-header p {
  margin: 4px 0 0;
  color: #6b7280;
  font-size: 13px;
}

button {
  height: 34px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  color: #374151;
  cursor: pointer;
  padding: 0 12px;
}

.primary {
  border-color: #2563eb;
  background: #2563eb;
  color: #fff;
}

.danger {
  border-color: #fecaca;
  color: #dc2626;
}

.step-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.field-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 7px;
  color: #374151;
  font-size: 13px;
  font-weight: 600;
}

.field.full {
  grid-column: 1 / -1;
}

.field b {
  margin-left: 3px;
  color: #dc2626;
}

.field select,
.filter-input,
.json-editor {
  width: 100%;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  color: #111827;
  font: inherit;
}

.field select,
.filter-input {
  height: 38px;
  padding: 0 10px;
}

.json-editor {
  min-height: 260px;
  padding: 12px;
  font-family: Consolas, Monaco, 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.55;
  resize: vertical;
}

.form-error {
  margin: 0;
  color: #dc2626;
  font-size: 13px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.form-actions button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.empty-text {
  color: #6b7280;
  font-size: 13px;
}

.execution-result {
  display: flex;
  flex-direction: column;
  gap: 14px;
  border-top: 1px solid #e5e7eb;
  padding-top: 16px;
}

.status-pill {
  display: inline-flex;
  min-width: 68px;
  justify-content: center;
  border-radius: 999px;
  padding: 5px 10px;
  font-size: 12px;
  font-weight: 700;
}

.status-pill.idle {
  background: #f3f4f6;
  color: #4b5563;
}

.status-pill.success {
  background: #dcfce7;
  color: #166534;
}

.status-pill.failed {
  background: #fee2e2;
  color: #991b1b;
}

.result-content {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.result-meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin: 0;
}

.result-meta div {
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 10px;
}

.result-meta dt {
  color: #6b7280;
  font-size: 12px;
}

.result-meta dd {
  margin: 5px 0 0;
  color: #111827;
  font-size: 14px;
  font-weight: 700;
  word-break: break-word;
}

.result-block {
  border: 1px solid #e5e7eb;
  border-radius: 6px;
}

.result-block summary {
  cursor: pointer;
  padding: 11px 12px;
  color: #111827;
  font-weight: 700;
}

.result-block pre {
  max-height: 360px;
  overflow: auto;
  margin: 0;
  border-top: 1px solid #e5e7eb;
  background: #0f172a;
  color: #e5e7eb;
  padding: 14px;
  font-size: 13px;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
}

@media (max-width: 640px) {
  .field-grid,
  .result-meta {
    grid-template-columns: 1fr;
  }

  .execution-result header {
    flex-direction: column;
  }
}
</style>
