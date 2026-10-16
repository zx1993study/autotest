<template>
  <section class="conversation">
    <div ref="history" class="messages" role="log" aria-label="生成对话" aria-live="polite">
      <article v-for="(message,index) in messages" :key="`${message.task_id || ''}:${index}`" :class="message.role">
        <span class="speaker"><User v-if="message.role === 'user'" :size="16" /><Bot v-else :size="16" />{{ message.role === 'user' ? '你' : 'AI' }}</span>
        <div class="message-content">{{ message.content }}</div>
      </article>
      <p v-if="busy" class="working"><LoaderCircle :size="15" />{{ progress || '处理中' }}</p>
    </div>
    <form class="composer" @submit.prevent="$emit('send')">
      <label class="composer-label" for="generation-message">{{ messages.length ? '回复追问或补充下一步操作' : '操作描述' }}</label>
      <textarea id="generation-message" :value="modelValue" :disabled="disabled" rows="3" maxlength="12000" aria-label="对话消息" @input="$emit('update:modelValue', ($event.target as HTMLTextAreaElement).value)" />
      <div class="send-row"><p v-if="error" class="error" role="alert">{{ error }}</p><button type="submit" title="发送消息" aria-label="发送消息" :disabled="busy || disabled || !modelValue.trim()"><Send :size="18" /></button></div>
    </form>
  </section>
</template>
<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { Bot, User, Send, LoaderCircle } from 'lucide-vue-next'
import type { GenerationMessage } from '../../types/generation'
const props = defineProps<{ modelValue: string; messages: GenerationMessage[]; busy: boolean; disabled?: boolean; progress?: string; error?: string }>()
defineEmits<{ 'update:modelValue':[value:string]; send:[] }>()
const history = ref<HTMLElement>()
watch(() => [props.messages.length, props.busy], async () => { await nextTick(); if (history.value) history.value.scrollTop = history.value.scrollHeight })
</script>
<style scoped>
.conversation { display:flex; flex-direction:column; flex:1; min-height:0; } .messages { flex:1; min-height:90px; overflow:auto; padding:12px 0; }
article { margin:0 0 22px; min-width:0; } .speaker { display:flex; align-items:center; gap:7px; font-size:12px; color:#667085; margin-bottom:7px; }
.message-content { white-space:pre-wrap; overflow-wrap:anywhere; font-size:14px; line-height:1.7; } .user .message-content { background:#f3f5f7; padding:10px 12px; border-radius:6px; }
.assistant .speaker { color:#087f8c; } .composer { border-top:1px solid #e3e8ed; padding-top:14px; } .composer-label { font-size:13px; display:block; margin-bottom:7px; }
textarea { width:100%; min-height:86px; max-height:180px; resize:vertical; } .send-row { display:flex; justify-content:flex-end; align-items:center; gap:12px; min-height:40px; margin-top:6px; }
.send-row button { flex-shrink:0; width:38px; height:36px; padding:7px; display:grid; place-items:center; } .error { color:#b42318; flex:1; margin:0; overflow-wrap:anywhere; font-size:13px; }
.working { color:#667085; display:flex; gap:8px; align-items:center; font-size:13px; }
</style>
