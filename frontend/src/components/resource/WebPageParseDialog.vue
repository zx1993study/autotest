<template>
  <div v-if="visible" class="modal-backdrop" @click.self="$emit('close')">
    <section class="modal-panel case-modal" role="dialog" aria-modal="true">
      <header class="modal-header">
        <h3>解析 Playwright 脚本</h3>
        <button class="modal-close" type="button" aria-label="关闭" @click="$emit('close')">×</button>
      </header>

      <form class="modal-form" @submit.prevent="$emit('submit')">
        <div v-if="selectedPage" class="result-panel">
          <h4>{{ selectedPage.name }}</h4>
          <div class="result-grid">
            <span>页面 ID</span>
            <strong>{{ selectedPage.id }}</strong>
            <span>项目 ID</span>
            <strong>{{ selectedPage.project_id || '-' }}</strong>
            <span>页面地址</span>
            <strong>{{ selectedPage.data.url || '-' }}</strong>
          </div>
        </div>

        <label class="field full">
          <span>解析方式<b>*</b></span>
          <select v-model="parseForm.sourceType">
            <option value="codegen">使用 codegen 录制解析脚本上传</option>
            <option value="file">上传脚本文件</option>
          </select>
        </label>

        <label class="field full">
          <span>已有元素处理<b>*</b></span>
          <select v-model="parseForm.existingElementStrategy">
            <option value="update">更新已有元素</option>
            <option value="skip">跳过保存</option>
          </select>
        </label>

        <section v-if="parseForm.sourceType === 'codegen'" class="result-panel">
          <h4>codegen 生成脚本</h4>
          <div class="result-list">
            <div class="result-row">
              <b>本地录制</b>
              <span>点击生成脚本后会打开 Playwright codegen，录制完成后关闭窗口。</span>
              <small>{{ codegenMessage || '生成的 py 脚本会自动回显到下方脚本内容。' }}</small>
            </div>
          </div>
          <div class="modal-actions inline-actions">
            <button type="button" :disabled="codegenRunning" @click="$emit('start-codegen')">
              {{ codegenRunning ? '录制中...' : '生成脚本' }}
            </button>
          </div>
        </section>

        <label class="field full">
          <span>脚本文件</span>
          <input type="file" accept=".py,.ts,.js,.txt" @change="$emit('file-change', $event)" />
        </label>

        <label class="field full">
          <span>脚本内容</span>
          <textarea v-model="parseForm.scriptText" class="json-editor" rows="12" spellcheck="false"></textarea>
        </label>

        <section v-if="parseResult" class="result-panel">
          <h4>解析结果</h4>
          <div class="result-grid">
            <span>页面 ID</span>
            <strong>{{ parseResult.page_id }}</strong>
            <span>保存元素</span>
            <strong>{{ parseResult.element_count }} 个</strong>
            <span>新增</span>
            <strong>{{ parseResult.created_count ?? 0 }} 个</strong>
            <span>更新</span>
            <strong>{{ parseResult.updated_count ?? 0 }} 个</strong>
            <span>跳过</span>
            <strong>{{ parseResult.skipped_count ?? 0 }} 个</strong>
          </div>
        </section>

        <p v-if="parseError" class="form-error">{{ parseError }}</p>

        <footer class="modal-actions">
          <button type="button" @click="$emit('close')">取消</button>
          <button type="submit" :disabled="parsing">{{ parsing ? '解析中...' : '解析并保存' }}</button>
        </footer>
      </form>
    </section>
  </div>
</template>

<script setup lang="ts">
import type { ResourceItem, WebScriptParseResult } from '../../api/http'
import type { WebPageParseForm } from '../../types/web-page-parse'

defineProps<{
  visible: boolean
  selectedPage: ResourceItem | null
  parseForm: WebPageParseForm
  parseResult: WebScriptParseResult | null
  parseError: string
  parsing: boolean
  codegenRunning: boolean
  codegenMessage: string
}>()

defineEmits<{
  close: []
  submit: []
  'file-change': [event: Event]
  'start-codegen': []
}>()
</script>
