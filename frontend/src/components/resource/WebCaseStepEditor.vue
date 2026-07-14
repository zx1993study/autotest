<template>
  <section class="case-step-panel">
    <div class="case-step-header">
      <strong>步骤列表</strong>
      <small>按元素 ID 正序展示，点击“是否截图 / 是否跳过”会同步保存到用例草稿。</small>
    </div>
    <div class="case-step-table-wrap">
      <table class="case-step-table">
        <thead>
          <tr>
            <th class="step-drag-column">拖拽</th>
            <th>步骤顺序</th>
            <th>元素 ID</th>
            <th>元素名称</th>
            <th>交互</th>
            <th>元素默认值</th>
            <th>是否截图</th>
            <th>是否跳过</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(step, index) in steps"
            :key="stepKey(step, index)"
            class="case-step-row"
            :class="{
              dragging: draggingStepIndex === index,
              'drag-over': dragOverStepIndex === index && draggingStepIndex !== index
            }"
            @dragenter.prevent="setStepDragOverIndex(index)"
            @dragover.prevent="setStepDragOverIndex(index)"
            @drop.prevent="dropStep(index)"
          >
            <td class="step-drag-cell">
              <button
                type="button"
                class="step-drag-handle"
                draggable="true"
                :aria-label="`拖拽调整第 ${index + 1} 步顺序`"
                title="拖拽排序"
                @dragstart.stop="startStepDrag(index, $event)"
                @dragend="finishStepDrag"
              >
                ↕
              </button>
            </td>
            <td>{{ formatStepValue(stepOrder(step, index)) }}</td>
            <td>{{ formatStepValue(stepElementId(step)) }}</td>
            <td>{{ formatStepValue(stepLabel(step)) }}</td>
            <td>{{ formatStepValue(stepAction(step)) }}</td>
            <td>
              <input
                class="step-value-input"
                :value="stepInputValue(step)"
                placeholder="请输入默认值"
                @input="updateStepDefaultValue(index, inputEventValue($event))"
              />
            </td>
            <td>
              <button type="button" class="toggle-pill" :class="{ active: stepScreenshot(step) }" @click="toggleStepScreenshot(index)">
                {{ stepScreenshot(step) ? '是' : '否' }}
              </button>
            </td>
            <td>
              <button type="button" class="toggle-pill" :class="{ active: stepSkip(step) }" @click="toggleStepSkip(index)">
                {{ stepSkip(step) ? '是' : '否' }}
              </button>
            </td>
          </tr>
          <tr v-if="!steps.length">
            <td colspan="8" class="empty-cell">暂无步骤</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  steps: Record<string, unknown>[]
}>()

const emit = defineEmits<{
  'update:steps': [steps: Record<string, unknown>[]]
}>()

const draggingStepIndex = ref<number | null>(null)
const dragOverStepIndex = ref<number | null>(null)

function startStepDrag(index: number, event: DragEvent) {
  draggingStepIndex.value = index
  dragOverStepIndex.value = index
  event.dataTransfer?.setData('text/plain', String(index))
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
  }
}

function setStepDragOverIndex(index: number) {
  if (draggingStepIndex.value != null) {
    dragOverStepIndex.value = index
  }
}

function dropStep(targetIndex: number) {
  if (draggingStepIndex.value == null) {
    finishStepDrag()
    return
  }
  const sourceIndex = draggingStepIndex.value
  if (sourceIndex !== targetIndex) {
    const nextSteps = [...props.steps]
    const [movedStep] = nextSteps.splice(sourceIndex, 1)
    if (movedStep) {
      nextSteps.splice(targetIndex, 0, movedStep)
      emit('update:steps', reindexCaseSteps(nextSteps))
    }
  }
  finishStepDrag()
}

function finishStepDrag() {
  draggingStepIndex.value = null
  dragOverStepIndex.value = null
}

function updateStepDefaultValue(index: number, value: string) {
  const nextSteps = [...props.steps]
  const step = nextSteps[index]
  if (!step) {
    return
  }
  step['元素值'] = value
  step.value = value
  step.default_value = value
  emit('update:steps', [...nextSteps])
}

function toggleStepScreenshot(index: number) {
  const nextSteps = [...props.steps]
  const step = nextSteps[index]
  if (!step) {
    return
  }
  const nextValue = !stepScreenshot(step)
  step['是否截图'] = nextValue
  step.take_screenshot = nextValue
  emit('update:steps', [...nextSteps])
}

function toggleStepSkip(index: number) {
  const nextSteps = [...props.steps]
  const step = nextSteps[index]
  if (!step) {
    return
  }
  const nextValue = !stepSkip(step)
  step['是否跳过'] = nextValue
  step.skip = nextValue
  emit('update:steps', [...nextSteps])
}

function reindexCaseSteps(steps: Record<string, unknown>[]) {
  return steps.map((step, index) => {
    const order = index + 1
    const nextStep = { ...step }
    if (Object.prototype.hasOwnProperty.call(nextStep, '步骤标识') || !hasStepOrderField(nextStep)) {
      nextStep['步骤标识'] = order
    }
    nextStep.sort_order = order
    if (Object.prototype.hasOwnProperty.call(nextStep, 'step_id')) {
      nextStep.step_id = order
    }
    if (Object.prototype.hasOwnProperty.call(nextStep, 'order')) {
      nextStep.order = order
    }
    if (Object.prototype.hasOwnProperty.call(nextStep, 'index')) {
      nextStep.index = order
    }
    return nextStep
  })
}

function hasStepOrderField(step: Record<string, unknown>) {
  return ['步骤标识', 'step_id', 'sort_order', 'order', 'index'].some(key => (
    Object.prototype.hasOwnProperty.call(step, key)
  ))
}

function stepKey(step: Record<string, unknown>, index: number) {
  return String(step.id || step.element_id || step['元素ID'] || `${index}:${stepLabel(step)}`)
}

function stepOrder(step: Record<string, unknown>, index: number) {
  return step['步骤标识'] ?? step.step_id ?? step.sort_order ?? step.order ?? step.index ?? index + 1
}

function stepElementId(step: Record<string, unknown>) {
  return step.element_id ?? step['元素ID'] ?? step['元素 ID']
}

function stepDefaultValue(step: Record<string, unknown>) {
  return step['元素值'] ?? step.value ?? step.default_value ?? ''
}

function stepInputValue(step: Record<string, unknown>) {
  const value = stepDefaultValue(step)
  return value == null ? '' : String(value)
}

function inputEventValue(event: Event) {
  return (event.target as HTMLInputElement).value
}

function stepScreenshot(step: Record<string, unknown>) {
  return Boolean(step['是否截图'] ?? step.take_screenshot ?? step.screenshot)
}

function stepSkip(step: Record<string, unknown>) {
  return Boolean(step['是否跳过'] ?? step.skip ?? step.skipped)
}

function formatStepValue(value: unknown) {
  if (value == null || value === '') {
    return '-'
  }
  if (typeof value === 'boolean') {
    return value ? '是' : '否'
  }
  if (typeof value === 'object') {
    return JSON.stringify(value)
  }
  return String(value)
}

function stepLabel(step: Record<string, unknown>) {
  return String(step['元素名称'] || step.element_name || step.name || step.label || step.locator || step.selector || '')
}

function stepAction(step: Record<string, unknown>) {
  return String(step['交互类型'] || step.action || step.type || step.operation || '')
}
</script>
