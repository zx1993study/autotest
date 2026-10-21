<template>
  <Teleport to="body">
    <dialog ref="dialog" class="result-dialog" aria-modal="true" :aria-label="title" @cancel.prevent="emit('close')" @click="closeOnBackdrop">
      <header class="result-dialog-header">
        <h3>{{ title }}</h3>
        <button autofocus type="button" title="关闭详情" aria-label="关闭详情" @click="emit('close')"><X :size="18" /></button>
      </header>
      <div class="result-dialog-body"><slot /></div>
      <footer v-if="$slots.footer" class="result-dialog-footer"><slot name="footer" /></footer>
    </dialog>
  </Teleport>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { X } from 'lucide-vue-next'

defineProps<{ title: string }>()
const emit = defineEmits<{ close: [] }>()
const dialog = ref<HTMLDialogElement | null>(null)
function closeOnBackdrop(event: MouseEvent) {
  if (event.target !== dialog.value || !dialog.value) return
  const rect = dialog.value.getBoundingClientRect()
  if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) emit('close')
}
onMounted(() => dialog.value?.showModal())
onBeforeUnmount(() => dialog.value?.close())
</script>

<style scoped>
.result-dialog { width: min(1600px, calc(100vw - 32px)); max-width: none; max-height: calc(100dvh - 32px); padding: 0; margin: auto; border: 1px solid #dce3eb; border-radius: 8px; color: #172033; background: #fff; overflow: auto; }
.result-dialog::backdrop { background: rgba(10, 18, 32, .48); }
.result-dialog-header { position: sticky; top: 0; z-index: 2; display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 14px 18px; border-bottom: 1px solid #edf1f7; background: #fff; }
h3 { margin: 0; font-size: 17px; overflow-wrap: anywhere; }
.result-dialog-header button { display: grid; place-items: center; width: 32px; height: 32px; padding: 0; flex: 0 0 32px; }
.result-dialog-body { padding: 16px 18px; min-width: 0; }
.result-dialog-footer { display: flex; justify-content: flex-end; flex-wrap: wrap; gap: 10px; padding: 12px 18px; border-top: 1px solid #edf1f7; }
@media (max-width: 720px) { .result-dialog-body { padding: 12px; } }
</style>
