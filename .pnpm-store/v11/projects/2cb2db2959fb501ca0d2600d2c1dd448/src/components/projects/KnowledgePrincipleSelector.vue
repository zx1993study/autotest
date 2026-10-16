<template>
  <fieldset class="principle-fieldset">
    <legend>测试原则</legend>
    <div class="principle-toolbar">
      <span>已选择 {{ modelValue.length }} / {{ items.length }} 项</span>
      <button type="button" @click="selectAll">全选</button>
    </div>
    <div v-if="loading" class="principle-state">正在加载测试原则...</div>
    <div v-else-if="!items.length" class="principle-state error-text">
      当前项目暂无测试原则，请先初始化测试原则。
    </div>
    <label v-for="item in items" v-else :key="item.id" class="principle-option">
      <input
        type="checkbox"
        :value="item.id"
        :checked="modelValue.includes(item.id)"
        @change="toggle(item.id)"
      />
      <span>
        <strong>{{ item.name }}</strong>
        <small>{{ item.data.content || item.description || '-' }}</small>
      </span>
    </label>
  </fieldset>
</template>

<script setup lang="ts">
import type { KnowledgePrincipleItem } from '../../types/knowledge'

const props = defineProps<{
  items: KnowledgePrincipleItem[]
  loading: boolean
  modelValue: number[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: number[]]
}>()

function selectAll() {
  emit('update:modelValue', props.items.map(item => item.id))
}

function toggle(itemId: number) {
  const nextValue = props.modelValue.includes(itemId)
    ? props.modelValue.filter(id => id !== itemId)
    : [...props.modelValue, itemId]
  emit('update:modelValue', nextValue)
}
</script>

<style scoped>
.principle-fieldset {
  display: grid;
  gap: 10px;
  margin-top: 16px;
  border: 1px solid #dbe3ef;
  border-radius: 6px;
  padding: 14px;
}

.principle-fieldset legend {
  color: #334155;
  font-weight: 700;
}

.principle-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: #64748b;
}

.principle-option {
  display: grid;
  grid-template-columns: 18px minmax(0, 1fr);
  align-items: start;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid #eef2f7;
}

.principle-option:last-child {
  border-bottom: 0;
}

.principle-option input {
  width: 16px;
  height: 16px;
  margin-top: 2px;
}

.principle-option > span {
  display: grid;
  gap: 8px;
}

.principle-option small,
.principle-state {
  color: #64748b;
  line-height: 1.55;
}

.error-text {
  color: #b42318;
}
</style>
