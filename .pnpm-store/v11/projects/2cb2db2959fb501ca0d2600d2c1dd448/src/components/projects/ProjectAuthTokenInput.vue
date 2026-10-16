<template>
  <span>Token 信息</span>
  <div class="token-input-row">
    <input :value="modelValue || ''" :type="visible ? 'text' : 'password'" autocomplete="off" spellcheck="false" maxlength="16384" :placeholder="hasFile ? '留空保留原 Token，输入新值替换' : '输入 Token 或 Bearer Token'" aria-label="Token 信息" @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)" />
    <button type="button" :title="visible ? '隐藏 Token' : '显示 Token'" :aria-label="visible ? '隐藏 Token' : '显示 Token'" @click="visible = !visible"><EyeOff v-if="visible" :size="16" /><Eye v-else :size="16" /></button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Eye, EyeOff } from 'lucide-vue-next'
defineProps<{ modelValue: string | number | null; hasFile: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
const visible = ref(false)
</script>

<style scoped>
.token-input-row{display:flex;gap:8px;min-width:0}.token-input-row input{flex:1;min-width:0}.token-input-row button{width:36px;height:40px;flex:0 0 36px;display:grid;place-items:center;padding:0}
.token-input-row input::-ms-reveal{display:none}
</style>
