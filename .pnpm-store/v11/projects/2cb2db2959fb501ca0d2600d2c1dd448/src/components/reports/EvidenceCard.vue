<template>
  <section class="evidence-card" :aria-label="title">
    <header>
      <h4>{{ title }}</h4>
      <button type="button" :disabled="value == null" :title="copyLabel" :aria-label="copyLabel" @click="copy"><Check v-if="copied" :size="15" /><Copy v-else :size="15" /></button>
    </header>
    <p v-if="copyError" class="copy-error" role="status">复制失败</p>
    <div class="evidence-card-content" tabindex="0" :aria-label="`${title}内容`">
      <slot><pre v-if="value != null">{{ text }}</pre><p v-else class="evidence-empty">{{ emptyText }}</p></slot>
    </div>
    <span class="copy-status" role="status">{{ copied ? '已复制' : '' }}</span>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Check, Copy } from 'lucide-vue-next'
import { evidenceText } from '../../utils/executionEvidence'

const props = withDefaults(defineProps<{ title: string; value?: unknown; emptyText?: string }>(), { emptyText: '未记录' })
const copied = ref(false)
const copyError = ref(false)
const text = computed(() => evidenceText(props.value))
const copyLabel = computed(() => copied.value ? `已复制${props.title}` : `复制${props.title}`)
watch(() => props.value, () => { copied.value = false; copyError.value = false })
async function copy() {
  copied.value = false
  copyError.value = false
  try { await navigator.clipboard.writeText(text.value); copied.value = true } catch { copyError.value = true }
}
</script>

<style scoped>
.evidence-card { min-width: 0; border: 1px solid #dce3eb; border-radius: 6px; background: #fff; overflow: hidden; position: relative; }
header { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 10px 12px; border-bottom: 1px solid #e7ecf2; background: #f8fafc; }
h4 { margin: 0; font-size: 14px; }
button { display: grid; place-items: center; width: 28px; height: 28px; padding: 0; flex: 0 0 28px; }
.evidence-card-content { height: min(480px, 58dvh); overflow: auto; padding: 12px; outline-offset: -2px; }
pre { margin: 0; font: 12px/1.65 Consolas, 'Courier New', monospace; white-space: pre-wrap; overflow-wrap: anywhere; }
.evidence-empty { margin: 0; color: #738095; font-size: 13px; }
.copy-error { margin: 0; padding: 4px 12px; color: #b42318; font-size: 12px; }
.copy-status { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); }
@media (max-width: 900px) { .evidence-card-content { height: auto; max-height: 380px; min-height: 90px; } }
</style>
