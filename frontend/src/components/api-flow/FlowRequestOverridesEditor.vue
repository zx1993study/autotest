<template>
  <section class="flow-request-overrides">
    <header class="flow-section-heading">
      <div><h4>{{ title }}</h4><small v-if="caseName" class="flow-muted">{{ caseName }}</small></div>
      <div class="flow-actions">
        <button type="button" title="格式化 JSON" aria-label="格式化请求 JSON" :disabled="loading || !!error" @click="format"><Braces :size="16" /></button>
        <button type="button" title="恢复继承" aria-label="恢复参数继承" :disabled="loading || !!loadError" @click="reset"><RotateCcw :size="16" /></button>
      </div>
    </header>
    <p v-if="loading" class="flow-muted" role="status">正在加载原用例 JSON…</p>
    <p v-if="loadError" class="flow-error" role="alert">{{ loadError }}<button type="button" aria-label="重新加载原用例" title="重试" @click="loadCase"><RefreshCw :size="14" /></button></p>
    <textarea v-else-if="!loading" :value="text" class="flow-request-json" aria-label="参数覆盖 JSON" :aria-invalid="!!error" :disabled="!caseId" spellcheck="false" @input="edit(($event.target as HTMLTextAreaElement).value)" />
    <p v-if="!caseId" class="flow-empty-small">尚未选择节点用例</p>
    <p v-if="error" class="flow-error" role="alert">{{ error }}</p>
    <details v-if="caseId && !loading && !loadError" class="flow-original-request"><summary>原用例 JSON</summary><pre>{{ JSON.stringify(original, null, 2) }}</pre></details>
  </section>
</template>
<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { Braces, RefreshCw, RotateCcw } from 'lucide-vue-next'
import { getFlowCase } from '../../services/api-flow.service'
import type { FlowRequestOverride } from '../../types/api-flow'
import { applyFlowRequestOverride, flowCaseRequest, flowRequestDifference, parseFlowRequest } from '../../utils/apiFlowRequest'

const props = withDefaults(defineProps<{nodeKey: string; caseId: number | null; value: FlowRequestOverride; inherited?: FlowRequestOverride; draft?: string; title?: string}>(), {title: '参数覆盖'})
const emit = defineEmits<{
  (event: 'change', value: FlowRequestOverride): void
  (event: 'draft', key: string, value: string | undefined): void
  (event: 'validity', key: string, valid: boolean): void
}>()
const original = ref<Record<string, unknown>>({})
const caseName = ref('')
const text = ref('{}')
const error = ref('')
const loadError = ref('')
const loading = ref(false)
const baseline = computed(() => applyFlowRequestOverride(original.value, props.inherited))
let generation = 0
onBeforeUnmount(() => { generation++ })

watch(() => props.caseId, (id, previous) => {
  if (previous !== undefined && id !== previous) emit('draft', props.nodeKey, undefined)
  void loadCase()
}, {immediate: true})
watch(() => [JSON.stringify(baseline.value), JSON.stringify(props.value), props.draft], refreshText)

async function loadCase() {
  const current = ++generation
  const id = props.caseId
  original.value = {}; caseName.value = ''; loadError.value = ''; error.value = ''
  if (!id) { loading.value = false; refreshText(); return }
  loading.value = true; emit('validity', props.nodeKey, false)
  try {
    const item = await getFlowCase(id)
    if (current !== generation) return
    original.value = flowCaseRequest(item); caseName.value = item.name
  } catch (err) {
    if (current === generation) loadError.value = err instanceof Error ? err.message : '原用例加载失败'
  } finally {
    if (current === generation) { loading.value = false; refreshText() }
  }
}
function refreshText() {
  if (loading.value) return
  if (loadError.value) { emit('validity', props.nodeKey, false); return }
  text.value = props.draft ?? JSON.stringify(applyFlowRequestOverride(baseline.value, props.value), null, 2)
  validate(false)
}
function validate(publish: boolean) {
  try {
    const value = parseFlowRequest(text.value)
    error.value = ''; emit('validity', props.nodeKey, true)
    if (publish) emit('change', flowRequestDifference(baseline.value, value))
  } catch (err) {
    error.value = err instanceof SyntaxError ? 'JSON 格式不正确，请检查逗号、引号和括号' : err instanceof Error ? err.message : 'JSON 格式不正确'
    emit('validity', props.nodeKey, false)
  }
}
function edit(value: string) { text.value = value; emit('draft', props.nodeKey, value); validate(true) }
function format() { edit(JSON.stringify(parseFlowRequest(text.value), null, 2)) }
function reset() {
  if (!window.confirm('清除当前节点的参数覆盖，恢复继承？')) return
  emit('change', {params: {}, request: {}, request_removals: []}); emit('draft', props.nodeKey, undefined)
}
</script>
