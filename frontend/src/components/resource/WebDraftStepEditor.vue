<template>
  <section class="case-step-panel draft-step-panel">
    <div class="case-step-header">
      <strong>元素步骤列表</strong>
      <span>共 {{ stepRows.length }} 步</span>
    </div>
    <table class="case-step-table web-step-table">
      <thead>
        <tr>
          <th class="step-drag-column"></th>
          <th>顺序</th>
          <th>元素名称</th>
          <th>交互</th>
          <th>默认值</th>
          <th>截图</th>
          <th>跳过</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(step, stepIndex) in stepRows"
          :key="stepKey(step, stepIndex)"
          class="case-step-row"
          :class="{ dragging: draggingIndex === stepIndex, 'drag-over': dragOverIndex === stepIndex }"
          @dragover.prevent="setDragOver(stepIndex)"
          @dragleave="clearDragOver(stepIndex)"
          @drop.prevent="dropStep(stepIndex)"
        >
          <td class="step-drag-cell">
            <button
              type="button"
              class="step-drag-handle"
              draggable="true"
              title="拖拽调整顺序"
              @dragstart="startDrag(stepIndex, $event)"
              @dragend="endDrag"
            >
              ☰
            </button>
          </td>
          <td>{{ stepOrder(step, stepIndex) }}</td>
          <td>{{ stepLabel(step) }}</td>
          <td>{{ stepAction(step) }}</td>
          <td>
            <input
              class="step-inline-input"
              :value="stepInputValue(step)"
              @input="updateStepDefaultValue(stepIndex, inputEventValue($event))"
            />
          </td>
          <td>
            <button type="button" class="tiny-toggle" :class="{ active: stepScreenshot(step) }" @click="toggleStepScreenshot(stepIndex)">
              {{ stepScreenshot(step) ? '是' : '否' }}
            </button>
          </td>
          <td>
            <button type="button" class="tiny-toggle" :class="{ active: stepSkip(step) }" @click="toggleStepSkip(stepIndex)">
              {{ stepSkip(step) ? '是' : '否' }}
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

const props = defineProps<{ modelValue: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

const draggingIndex = ref<number | null>(null)
const dragOverIndex = ref<number | null>(null)

const stepRows = computed<Record<string, unknown>[]>(() => {
  const caseJson = parseCaseJsonText(props.modelValue)
  if (!isRecord(caseJson)) return []
  return normalizeStepRows(caseSteps(caseJson))
})

function parseCaseJsonText(value: string): unknown {
  if (!value.trim()) return {}
  try { return JSON.parse(value) as unknown } catch { return {} }
}
function caseSteps(caseJson: Record<string, unknown>) {
  if (Array.isArray(caseJson.steps)) return caseJson.steps
  return isRecord(caseJson.request) && Array.isArray(caseJson.request.steps) ? caseJson.request.steps : []
}
function setCaseSteps(caseJson: Record<string, unknown>, steps: Record<string, unknown>[]) {
  if (Array.isArray(caseJson.steps)) caseJson.steps = steps
  else if (isRecord(caseJson.request)) caseJson.request.steps = steps
  else caseJson.steps = steps
}
function normalizeStepRows(steps: unknown[]) {
  return steps.filter(isRecord).map(step => ({ ...step })).sort((left, right) => Number(stepOrder(left, 0)) - Number(stepOrder(right, 0)))
}
function mutateStep(index: number, updater: (step: Record<string, unknown>) => void) {
  const caseJson = parseCaseJsonText(props.modelValue)
  if (!isRecord(caseJson)) return
  const steps = normalizeStepRows(caseSteps(caseJson))
  const step = steps[index]
  if (!step) return
  updater(step)
  setCaseSteps(caseJson, steps)
  emit('update:modelValue', stringifyJson(caseJson))
}
function startDrag(index: number, event: DragEvent) {
  draggingIndex.value = index
  dragOverIndex.value = index
  event.dataTransfer?.setData('text/plain', String(index))
  if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move'
}
function setDragOver(index: number) { if (draggingIndex.value !== null) dragOverIndex.value = index }
function clearDragOver(index: number) { if (dragOverIndex.value === index) dragOverIndex.value = null }
function endDrag() { draggingIndex.value = null; dragOverIndex.value = null }
function dropStep(targetIndex: number) {
  const sourceIndex = draggingIndex.value
  if (sourceIndex === null || sourceIndex === targetIndex) { endDrag(); return }
  const caseJson = parseCaseJsonText(props.modelValue)
  if (!isRecord(caseJson)) { endDrag(); return }
  const steps = normalizeStepRows(caseSteps(caseJson))
  const [movedStep] = steps.splice(sourceIndex, 1)
  if (!movedStep) { endDrag(); return }
  steps.splice(targetIndex, 0, movedStep)
  steps.forEach((step, index) => updateStepOrderFields(step, index + 1))
  setCaseSteps(caseJson, steps)
  emit('update:modelValue', stringifyJson(caseJson))
  endDrag()
}
function updateStepOrderFields(step: Record<string, unknown>, order: number) {
  step.sort_order = order
  if ('order' in step) step.order = order
  if ('index' in step) step.index = order
}
function updateStepDefaultValue(index: number, value: string) { mutateStep(index, step => { step['元素值'] = value; step.value = value }) }
function toggleStepScreenshot(index: number) { mutateStep(index, step => { const nextValue = !stepScreenshot(step); step['是否截图'] = nextValue; step.take_screenshot = nextValue }) }
function toggleStepSkip(index: number) { mutateStep(index, step => { const nextValue = !stepSkip(step); step['是否跳过'] = nextValue; step.skip = nextValue }) }
function stepKey(step: Record<string, unknown>, index: number) { return String(readStepValue(step, ['步骤标识', 'id', 'step_id', 'sort_order', 'order']) ?? index) }
function stepOrder(step: Record<string, unknown>, index: number) { return readStepValue(step, ['sort_order', 'order', 'index', '步骤标识']) ?? index + 1 }
function stepLabel(step: Record<string, unknown>) { return formatValue(readStepValue(step, ['元素名称', 'element_name', 'name', 'locator', 'selector'])) }
function stepAction(step: Record<string, unknown>) { return formatValue(readStepValue(step, ['交互类型', 'action', 'type', 'operation'])) }
function stepInputValue(step: Record<string, unknown>) { const value = readStepValue(step, ['元素值', 'value', 'default_value', 'input']); return value == null ? '' : String(value) }
function stepScreenshot(step: Record<string, unknown>) { return Boolean(readStepValue(step, ['是否截图', 'take_screenshot', 'screenshot'])) }
function stepSkip(step: Record<string, unknown>) { return Boolean(readStepValue(step, ['是否跳过', 'skip', 'skipped'])) }
function inputEventValue(event: Event) { return (event.target as HTMLInputElement).value }
function readStepValue(step: Record<string, unknown>, keys: string[]) { for (const key of keys) if (step[key] !== undefined && step[key] !== '') return step[key]; return undefined }
function stringifyJson(value: unknown) { return JSON.stringify(value ?? {}, null, 2) }
function formatValue(value: unknown): string { if (value == null || value === '') return '-'; if (typeof value === 'boolean') return value ? '是' : '否'; if (typeof value === 'object') return JSON.stringify(value); return String(value) }
function isRecord(value: unknown): value is Record<string, unknown> { return Boolean(value) && typeof value === 'object' && !Array.isArray(value) }
</script>
