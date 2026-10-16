<template>
  <div ref="anchor" class="api-select" :class="{'is-disabled': disabled || loading}">
    <input ref="input" class="api-select-input" role="combobox" type="text" :value="open ? query : selectedLabel"
      :placeholder="loading ? '正在加载 API…' : placeholder" :title="selectedLabel" :aria-label="label" :aria-expanded="open" :aria-busy="loading" aria-autocomplete="list"
      :aria-controls="menuId" :aria-activedescendant="open && activeIndex >= 0 ? `${menuId}-${activeIndex}` : undefined"
      :disabled="disabled || loading" :required="required && !selectedId" autocomplete="off"
      @focus="openMenu" @click="openMenu" @input="search(($event.target as HTMLInputElement).value)" @keydown="keydown" @blur="blur" />
    <button v-if="clearable && selectedId" class="api-select-icon" type="button" tabindex="-1" :disabled="disabled || loading" :aria-label="`清除${label}`" title="清除选择" @mousedown.prevent @click="clear"><X :size="14" /></button>
    <button class="api-select-icon" type="button" tabindex="-1" :disabled="disabled || loading" :aria-label="`展开${label}`" title="展开选项" @mousedown.prevent @click="toggle"><ChevronDown :size="15" /></button>
    <Teleport to="body">
      <div v-if="open" ref="menu" class="api-select-menu" :style="position">
        <div :id="menuId" role="listbox" :aria-label="`${label}选项`" class="api-select-options">
          <button v-for="(option, index) in filtered" :id="`${menuId}-${index}`" :key="option.id" type="button" role="option" tabindex="-1"
            class="api-select-option" :class="{'is-active': activeIndex === index}" :aria-selected="Number(option.id) === selectedId"
            @mousedown.prevent @pointermove="activeIndex = index" @click="choose(Number(option.id))">
            <span>{{ apiOptionLabel(option) }}</span><small>#{{ option.id }}</small><Check v-if="Number(option.id) === selectedId" :size="14" />
          </button>
          <div v-if="!filtered.length" class="api-select-empty" role="status">{{ options.length ? '没有匹配的 API' : '暂无 API' }}</div>
        </div>
        <div v-if="filtered.length" class="api-select-count">{{ filtered.length }} 项</div>
      </div>
    </Teleport>
  </div>
</template>
<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, useId, watch } from 'vue'
import { Check, ChevronDown, X } from 'lucide-vue-next'
import type { SelectOptionRecord } from '../../types/resource'
import { apiOptionLabel, filterApiOptions } from '../../utils/apiOptions'

const props = withDefaults(defineProps<{
  modelValue: number | string | null | undefined; options: SelectOptionRecord[]; label?: string
  placeholder?: string; disabled?: boolean; loading?: boolean; clearable?: boolean; required?: boolean
}>(), {label: 'API', placeholder: '搜索 API 名称、方法、路径或 ID', disabled: false, loading: false, clearable: true, required: false})
const emit = defineEmits<{'update:modelValue': [value: number]; change: [value: number]}>()
const anchor = ref<HTMLElement | null>(null)
const input = ref<HTMLInputElement | null>(null)
const menu = ref<HTMLElement | null>(null)
const menuId = `api-select-${useId()}`
const open = ref(false)
const query = ref('')
const activeIndex = ref(-1)
const position = ref<Record<string, string>>({})
const selectedId = computed(() => Number(props.modelValue) || 0)
const selectedLabel = computed(() => {
  const selected = props.options.find(option => Number(option.id) === selectedId.value)
  return selected ? apiOptionLabel(selected) : selectedId.value ? `#${selectedId.value}（不可用）` : ''
})
const filtered = computed(() => filterApiOptions(props.options, query.value))

watch([selectedId, () => props.required, input], () => {
  input.value?.setCustomValidity(props.required && !selectedId.value ? '请选择 API' : '')
}, {immediate: true, flush: 'post'})
watch(() => props.modelValue, close)
watch(() => props.disabled || props.loading, blocked => { if (blocked) close() })
watch(filtered, () => {
  activeIndex.value = filtered.value.length ? query.value ? 0 : Math.max(0, filtered.value.findIndex(option => Number(option.id) === selectedId.value)) : -1
  void nextTick(updatePosition)
})
watch(open, visible => {
  if (visible) {
    document.addEventListener('pointerdown', outside)
    window.addEventListener('resize', updatePosition)
    window.addEventListener('scroll', updatePosition, true)
  } else removeListeners()
})
onBeforeUnmount(removeListeners)

function openMenu() {
  if (props.disabled || props.loading || open.value) return
  query.value = ''; open.value = true
  activeIndex.value = Math.max(0, filtered.value.findIndex(option => Number(option.id) === selectedId.value))
  if (!filtered.value.length) activeIndex.value = -1
  void nextTick(() => { updatePosition(); scrollActive() })
}
function close() { open.value = false; query.value = '' }
function toggle() { if (open.value) close(); else { openMenu(); input.value?.focus() } }
function search(value: string) { if (!open.value) openMenu(); query.value = value }
function choose(id: number) {
  if (id !== selectedId.value) { emit('update:modelValue', id); emit('change', id) }
  close(); input.value?.focus()
}
function clear() { choose(0) }
function blur(event: FocusEvent) {
  if (!menu.value?.contains(event.relatedTarget as Node | null)) close()
}
function outside(event: PointerEvent) {
  const target = event.target as Node
  if (!anchor.value?.contains(target) && !menu.value?.contains(target)) close()
}
function removeListeners() {
  document.removeEventListener('pointerdown', outside)
  window.removeEventListener('resize', updatePosition)
  window.removeEventListener('scroll', updatePosition, true)
}
function updatePosition() {
  if (!open.value || !anchor.value) return
  const rect = anchor.value.getBoundingClientRect()
  if (rect.bottom < 0 || rect.top > window.innerHeight) { close(); return }
  const width = Math.min(Math.max(rect.width, 260), window.innerWidth - 16)
  const below = window.innerHeight - rect.bottom - 12
  const above = rect.top - 12
  const upwards = below < 220 && above > below
  const height = Math.min(340, Math.max(80, upwards ? above : below))
  position.value = {left: `${Math.max(8, Math.min(rect.left, window.innerWidth - width - 8))}px`, width: `${width}px`,
    maxHeight: `${height}px`, ...(upwards ? {bottom: `${window.innerHeight - rect.top + 4}px`} : {top: `${rect.bottom + 4}px`})}
}
function scrollActive() { document.getElementById(`${menuId}-${activeIndex.value}`)?.scrollIntoView({block: 'nearest'}) }
function keydown(event: KeyboardEvent) {
  if (event.key === 'Tab') { close(); return }
  if (event.key === 'Escape') { event.preventDefault(); close(); return }
  if (!['ArrowDown', 'ArrowUp', 'Enter', 'Home', 'End'].includes(event.key)) return
  if (!open.value && ['Home', 'End'].includes(event.key)) return
  event.preventDefault()
  if (!open.value) { openMenu(); return }
  if (event.key === 'Enter') { const option = filtered.value[activeIndex.value]; if (option) choose(Number(option.id)); return }
  const count = filtered.value.length
  if (!count) return
  activeIndex.value = event.key === 'Home' ? 0 : event.key === 'End' ? count - 1
    : (activeIndex.value + (event.key === 'ArrowUp' ? -1 : 1) + count) % count
  void nextTick(scrollActive)
}
</script>
<style scoped>
.api-select { display: flex; width: 100%; min-width: 0; min-height: 34px; align-items: center; border: 1px solid #d7deea; border-radius: 6px; background: #fff; }
.api-select:focus-within { outline: 2px solid #c4d8ff; outline-offset: 1px; }
.api-select.is-disabled { background: #f4f6f8; opacity: .65; }
.api-select .api-select-input { width: 100%; min-width: 0; flex: 1; min-height: 32px; padding: 6px 9px; border: 0; border-radius: 6px; outline: 0; box-shadow: none; color: #172033; background: transparent; font-size: 13px; text-overflow: ellipsis; }
.api-select .api-select-input:focus { outline: 0; }
.api-select .api-select-icon { display: grid; place-items: center; flex: 0 0 28px; width: 28px; min-height: 30px; padding: 0; border: 0; border-radius: 4px; background: transparent; color: #69758b; cursor: pointer; }
.api-select .api-select-icon:hover { background: #edf3ff; }
.api-select .api-select-icon:disabled { cursor: not-allowed; }
.api-select-menu { position: fixed; z-index: 10000; display: flex; flex-direction: column; min-width: 0; border: 1px solid #d7deea; border-radius: 6px; background: #fff; box-shadow: 0 6px 18px #17203320; color: #172033; font-size: 13px; letter-spacing: 0; box-sizing: border-box; overflow: hidden; }
.api-select-options { overflow-y: auto; overscroll-behavior: contain; min-height: 0; }
.api-select-option { display: flex; align-items: center; gap: 8px; width: 100%; min-height: 40px; padding: 9px 11px; border: 0; border-radius: 0; background: #fff; text-align: left; color: inherit; cursor: pointer; font: inherit; box-sizing: border-box; }
.api-select-option.is-active { background: #edf3ff; }
.api-select-option > span { flex: 1; min-width: 0; overflow-wrap: anywhere; }
.api-select-option > small { color: #7b8598; font-size: 11px; flex-shrink: 0; }
.api-select-option > svg { flex-shrink: 0; color: #245cc9; }
.api-select-empty { padding: 16px 12px; color: #69758b; }
.api-select-count { padding: 6px 11px; border-top: 1px solid #e5eaf2; color: #7b8598; font-size: 11px; flex-shrink: 0; }
</style>
