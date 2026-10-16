<template>
  <div class="flow-value-input">
    <select :value="valueType" aria-label="值类型" @change="changeType(($event.target as HTMLSelectElement).value)">
      <option value="string">文本</option><option value="number">数字</option><option value="boolean">布尔</option><option value="null">空值</option>
    </select>
    <select v-if="valueType === 'boolean'" :value="String(modelValue)" aria-label="布尔值" @change="emit('update:modelValue', ($event.target as HTMLSelectElement).value === 'true')">
      <option value="true">true</option><option value="false">false</option>
    </select>
    <input v-else-if="valueType !== 'null'" :value="displayValue" :type="valueType === 'number' ? 'number' : 'text'" aria-label="参数值" @input="updateValue(($event.target as HTMLInputElement).value)" />
    <span v-else class="flow-muted">null</span>
  </div>
</template>
<script setup lang="ts">
import { computed } from 'vue'
const props = defineProps<{ modelValue: unknown }>()
const emit = defineEmits<{ (event: 'update:modelValue', value: unknown): void }>()
const valueType = computed(() => props.modelValue == null ? 'null' : typeof props.modelValue === 'boolean' ? 'boolean' : typeof props.modelValue === 'number' ? 'number' : 'string')
const displayValue = computed(() => typeof props.modelValue === 'object' ? JSON.stringify(props.modelValue) : String(props.modelValue ?? ''))
function changeType(type: string) { emit('update:modelValue', type === 'number' ? 0 : type === 'boolean' ? true : type === 'null' ? null : '') }
function updateValue(value: string) { emit('update:modelValue', valueType.value === 'number' ? Number(value) : value) }
</script>
