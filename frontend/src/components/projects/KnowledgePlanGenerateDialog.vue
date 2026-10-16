<template>
  <div v-if="open" class="modal-backdrop" @click.self="emitClose">
    <section class="modal-panel plan-generator-dialog" role="dialog" aria-modal="true">
      <header class="modal-header">
        <div>
          <h3>生成测试执行计划</h3>
          <p>页面需求文档</p>
        </div>
        <button class="modal-close" type="button" aria-label="关闭" @click="emitClose">×</button>
      </header>

      <form class="generator-form" @submit.prevent="submit">
        <div class="form-grid">
          <label>
            <span>项目</span>
            <ProjectFilterSelect v-model="localProjectId" :include-all="false" @ready="loadPrinciples" />
          </label>
          <label>
            <span>测试轮数</span>
            <input v-model.number="form.test_rounds" type="number" min="1" max="10000" required />
          </label>
          <label>
            <span>计划名称</span>
            <input v-model.trim="form.plan_name" maxlength="128" required placeholder="请输入测试计划名称" />
          </label>
          <label>
            <span>需求标题</span>
            <input v-model.trim="form.requirement_title" maxlength="128" required placeholder="请输入页面需求标题" />
          </label>
        </div>

        <label class="full-field">
          <span>页面需求文档</span>
          <textarea
            v-model.trim="form.requirement_document"
            rows="9"
            minlength="10"
            maxlength="30000"
            required
            placeholder="请输入需要测试的页面需求、字段规则、业务条件和预期结果"
          ></textarea>
        </label>

        <KnowledgePrincipleSelector
          v-model="form.principle_ids"
          :items="principles"
          :loading="loading"
        />

        <p v-if="errorMessage" class="form-error">{{ errorMessage }}</p>
        <footer class="modal-actions">
          <button type="button" :disabled="submitting" @click="emitClose">取消</button>
          <button type="submit" class="primary" :disabled="!canSubmit || submitting">
            {{ submitting ? '生成中...' : '生成计划' }}
          </button>
        </footer>
      </form>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'

import ProjectFilterSelect from '../filters/ProjectFilterSelect.vue'
import KnowledgePrincipleSelector from './KnowledgePrincipleSelector.vue'
import {
  generateKnowledgePlan,
  listKnowledgePrinciples
} from '../../services/knowledge.service'
import type {
  KnowledgePlanGenerationResult,
  KnowledgePrincipleItem
} from '../../types/knowledge'

const props = defineProps<{
  open: boolean
  projectId: number
}>()

const emit = defineEmits<{
  close: []
  generated: [result: KnowledgePlanGenerationResult]
}>()

const localProjectId = ref(props.projectId)
const principles = ref<KnowledgePrincipleItem[]>([])
const loading = ref(false)
const submitting = ref(false)
const errorMessage = ref('')
const form = reactive({
  plan_name: '',
  requirement_title: '',
  requirement_document: '',
  principle_ids: [] as number[],
  test_rounds: 1
})
let principleLoadVersion = 0

const canSubmit = computed(() => (
  localProjectId.value > 0
  && form.plan_name.length > 0
  && form.requirement_title.length > 0
  && form.requirement_document.length >= 10
  && form.principle_ids.length > 0
))

watch(() => props.open, visible => {
  if (!visible) return
  localProjectId.value = props.projectId
  resetForm()
  void loadPrinciples()
})

watch(localProjectId, () => {
  if (props.open) void loadPrinciples()
})

async function loadPrinciples() {
  if (!localProjectId.value) return
  const loadVersion = ++principleLoadVersion
  const requestedProjectId = localProjectId.value
  loading.value = true
  errorMessage.value = ''
  try {
    const rows = await listKnowledgePrinciples(requestedProjectId)
    if (loadVersion !== principleLoadVersion) return
    principles.value = rows
    form.principle_ids = principles.value.map(item => item.id)
  } catch (error) {
    if (loadVersion === principleLoadVersion) {
      errorMessage.value = getErrorMessage(error)
    }
  } finally {
    if (loadVersion === principleLoadVersion) {
      loading.value = false
    }
  }
}

async function submit() {
  if (!canSubmit.value || submitting.value) return
  submitting.value = true
  errorMessage.value = ''
  try {
    const result = await generateKnowledgePlan({
      project_id: localProjectId.value,
      plan_name: form.plan_name,
      requirement_title: form.requirement_title,
      requirement_document: form.requirement_document,
      principle_ids: [...form.principle_ids],
      test_rounds: form.test_rounds
    })
    emit('generated', result)
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    submitting.value = false
  }
}

function resetForm() {
  form.plan_name = ''
  form.requirement_title = ''
  form.requirement_document = ''
  form.principle_ids = []
  form.test_rounds = 1
  errorMessage.value = ''
}

function emitClose() {
  if (!submitting.value) emit('close')
}

function getErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : '测试执行计划生成失败'
}
</script>

<style scoped>
.plan-generator-dialog {
  width: min(860px, 100%);
  max-height: calc(100vh - 48px);
  overflow: auto;
}

.generator-form,
.generator-form label,
.principle-option > span {
  display: grid;
  gap: 8px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.generator-form label > span {
  color: #334155;
  font-weight: 700;
}

.generator-form input,
.generator-form textarea {
  width: 100%;
  border: 1px solid #cbd6e8;
  border-radius: 6px;
  padding: 9px 10px;
}

.generator-form textarea {
  resize: vertical;
}

.full-field {
  margin-top: 16px;
}

@media (max-width: 720px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
