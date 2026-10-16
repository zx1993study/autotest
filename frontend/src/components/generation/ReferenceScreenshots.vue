<template>
  <section>
    <input type="file" accept="image/png" multiple aria-label="上传参考截图" @change="upload" />
    <p v-if="error" role="alert">{{ error }}</p>
    <ol>
      <li v-for="(item, index) in modelValue" :key="index">
        <img :src="`data:image/png;base64,${item.image_base64}`" :alt="`参考截图 ${index + 1}`" />
        <label>截图 {{ index + 1 }} 操作描述<textarea :value="item.description" rows="3" @input="describe(index, ($event.target as HTMLTextAreaElement).value)" /></label>
        <div>
          <button type="button" title="向前移动" aria-label="向前移动" :disabled="index === 0" @click="move(index)"><ArrowUp :size="16" /></button>
          <button type="button" title="删除截图" aria-label="删除截图" @click="remove(index)"><Trash2 :size="16" /></button>
        </div>
      </li>
    </ol>
  </section>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { ArrowUp, Trash2 } from 'lucide-vue-next'
import type { ReferenceImage } from '../../services/business-generation.service'
const props = defineProps<{ modelValue: ReferenceImage[] }>()
const emit = defineEmits<{ 'update:modelValue': [ReferenceImage[]] }>()
const error = ref('')
async function upload(event: Event) {
  error.value = ''
  const input = event.target as HTMLInputElement
  const items = [...props.modelValue]
  for (const file of Array.from(input.files || [])) {
    if (file.type !== 'image/png' || file.size > 4 * 1024 * 1024 || items.length >= 6) {
      error.value = '最多 6 张 PNG，每张不超过 4MB'
      break
    }
    const image_base64 = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => resolve(String(reader.result).split(',')[1])
      reader.onerror = reject
      reader.readAsDataURL(file)
    })
    items.push({ image_base64, description: '' })
  }
  emit('update:modelValue', items)
  input.value = ''
}
function describe(index: number, description: string) { emit('update:modelValue', props.modelValue.map((v, i) => i === index ? { ...v, description } : v)) }
function remove(index: number) { emit('update:modelValue', props.modelValue.filter((_, i) => i !== index)) }
function move(index: number) {
  const items = [...props.modelValue]
  ;[items[index - 1], items[index]] = [items[index], items[index - 1]]
  emit('update:modelValue', items)
}
</script>
<style scoped>
ol { padding: 0; list-style: none; }
li { display: grid; grid-template-columns: 100px minmax(0, 1fr) 34px; gap: 12px; padding: 12px 0; border-bottom: 1px solid #e3e8ed; }
img { width: 100px; height: 100px; object-fit: contain; background: #f4f6f8; }
label { display: grid; gap: 6px; } textarea { width: 100%; min-width: 0; } button { width: 32px; height: 32px; padding: 6px; } p { color: #b42318; }
</style>
