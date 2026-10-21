<template>
  <div ref="area" class="viewport-scroll-area" role="region" :aria-label="label" tabindex="0"
    :data-orientation="horizontal ? 'horizontal' : 'vertical'" :style="{ maxHeight: horizontal ? undefined : `${availableHeight}px` }">
    <slot />
  </div>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = withDefaults(defineProps<{
  label: string
  activeKey?: string
  bottomGap?: number
  horizontalBelow?: number
}>(), { activeKey: '', bottomGap: 16, horizontalBelow: 0 })
const area = ref<HTMLElement | null>(null)
const availableHeight = ref(400)
const horizontal = ref(false)
let observer: ResizeObserver | undefined
let frame = 0
let revealPending = true

function revealActive(focus = false) {
  const container = area.value
  const item = Array.from(container?.querySelectorAll<HTMLElement>('[data-scroll-key]') || [])
    .find(element => element.dataset.scrollKey === props.activeKey)
  if (!container || !item || !container.getClientRects().length) return
  revealPending = false
  if (focus) item.querySelector<HTMLElement>('[data-scroll-focus]')?.focus({ preventScroll: true })
  const bounds = container.getBoundingClientRect()
  const itemBounds = item.getBoundingClientRect()
  if (horizontal.value) {
    if (itemBounds.width > container.clientWidth - 8 || itemBounds.left < bounds.left + 4) container.scrollLeft += itemBounds.left - bounds.left - 4
    else if (itemBounds.right > bounds.right - 4) container.scrollLeft += itemBounds.right - bounds.right + 4
  } else {
    if (itemBounds.height > container.clientHeight - 8 || itemBounds.top < bounds.top + 4) container.scrollTop += itemBounds.top - bounds.top - 4
    else if (itemBounds.bottom > bounds.bottom - 4) container.scrollTop += itemBounds.bottom - bounds.bottom + 4
  }
}

function measure() {
  frame = 0
  const element = area.value
  if (!element?.getClientRects().length) return
  const nextHorizontal = props.horizontalBelow > 0 && window.innerWidth <= props.horizontalBelow
  const nextHeight = Math.max(144, window.innerHeight - Math.max(0, element.getBoundingClientRect().top) - props.bottomGap)
  if (nextHorizontal !== horizontal.value || nextHeight < availableHeight.value) revealPending = true
  horizontal.value = nextHorizontal
  availableHeight.value = nextHeight
  if (revealPending) void nextTick(() => revealActive())
}

function scheduleMeasure(event?: Event) {
  if (event?.target instanceof Node && area.value?.contains(event.target)) return
  if (event?.type === 'resize') revealPending = true
  if (!frame) frame = window.requestAnimationFrame(measure)
}

watch(() => props.activeKey, () => { revealPending = true; void nextTick(() => revealActive()) })
watch(() => [props.bottomGap, props.horizontalBelow], () => scheduleMeasure())
onMounted(() => {
  observer = new ResizeObserver(() => scheduleMeasure())
  let element: HTMLElement | null = area.value
  while (element) { observer.observe(element); element = element.parentElement }
  window.addEventListener('resize', scheduleMeasure)
  window.addEventListener('scroll', scheduleMeasure, true)
  scheduleMeasure()
})
onBeforeUnmount(() => {
  observer?.disconnect()
  window.cancelAnimationFrame(frame)
  window.removeEventListener('resize', scheduleMeasure)
  window.removeEventListener('scroll', scheduleMeasure, true)
})

defineExpose({ revealActive })
</script>

<style scoped>
.viewport-scroll-area {
  min-width: 0;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
  scrollbar-width: thin;
  scrollbar-color: #aebbd0 #e9eef6;
  scroll-padding: 4px;
}
.viewport-scroll-area::-webkit-scrollbar { width: 8px; height: 8px; }
.viewport-scroll-area::-webkit-scrollbar-track { background: #e9eef6; }
.viewport-scroll-area::-webkit-scrollbar-thumb { background: #aebbd0; border: 2px solid #e9eef6; border-radius: 4px; }
.viewport-scroll-area::-webkit-scrollbar-thumb:hover { background: #7f91ad; }
.viewport-scroll-area[data-orientation="horizontal"] { overflow-x: auto; overflow-y: hidden; scrollbar-gutter: auto; }
.viewport-scroll-area:focus-visible { outline: 2px solid #9dbbf5; outline-offset: 2px; }
</style>
