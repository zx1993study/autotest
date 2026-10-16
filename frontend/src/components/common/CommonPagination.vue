<template>
  <footer class="common-pagination" aria-label="分页">
    <div class="pagination-info">
      <span>共 {{ total }} 条</span>
      <span v-if="total">第 {{ pageStart }}-{{ pageEnd }} 条</span>
    </div>
    <div class="pagination-controls">
      <button type="button" :disabled="page <= 1 || loading" @click="navigate(1)">首页</button>
      <button type="button" :disabled="page <= 1 || loading" @click="navigate(page - 1)">上一页</button>
      <span class="page-number">第 {{ page }} / {{ totalPages }} 页</span>
      <button type="button" :disabled="page >= totalPages || loading" @click="navigate(page + 1)">下一页</button>
      <button type="button" :disabled="page >= totalPages || loading" @click="navigate(totalPages)">末页</button>
      <label>
        每页
        <select :value="pageSize" :disabled="loading" @change="changePageSize">
          <option v-for="size in pageSizeOptions" :key="size" :value="size">{{ size }}</option>
        </select>
        条
      </label>
      <label>
        跳至
        <input
          v-model.number="pageInput"
          type="number"
          min="1"
          :max="totalPages"
          :disabled="loading"
          @keyup.enter="jumpToPage"
        />
        页
      </label>
      <button type="button" :disabled="loading" @click="jumpToPage">跳转</button>
    </div>
    <span v-if="message" class="pagination-message">{{ message }}</span>
  </footer>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

const props = withDefaults(defineProps<{
  page: number
  pageSize: number
  total: number
  loading?: boolean
  message?: string
  pageSizeOptions?: number[]
}>(), {
  loading: false,
  message: '',
  pageSizeOptions: () => [10, 20, 50, 100]
})

const emit = defineEmits<{
  change: [page: number, pageSize: number]
}>()

const totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))
const pageStart = computed(() => props.total ? (props.page - 1) * props.pageSize + 1 : 0)
const pageEnd = computed(() => Math.min(props.total, props.page * props.pageSize))
const pageInput = ref(props.page)

watch(() => props.page, value => {
  pageInput.value = normalizePage(value)
})

watch(totalPages, () => {
  pageInput.value = normalizePage(pageInput.value)
})

function navigate(nextPage: number) {
  emit('change', normalizePage(nextPage), props.pageSize)
}

function changePageSize(event: Event) {
  const nextPageSize = Number((event.target as HTMLSelectElement).value)
  emit('change', 1, nextPageSize)
}

function jumpToPage() {
  navigate(Number(pageInput.value) || 1)
}

function normalizePage(value: number) {
  return Math.min(Math.max(Math.trunc(value), 1), totalPages.value)
}
</script>

<style scoped>
.common-pagination {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-top: 16px;
  color: #62708a;
  font-size: 13px;
}

.pagination-info,
.pagination-controls,
.pagination-controls label {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.pagination-controls button {
  min-width: 56px;
  height: 32px;
  padding: 0 10px;
}

.pagination-controls select,
.pagination-controls input {
  width: 72px;
  height: 32px;
  padding: 0 8px;
  border: 1px solid #d8e0ef;
  border-radius: 6px;
  background: #ffffff;
}

.page-number {
  min-width: 86px;
  text-align: center;
}

.pagination-message {
  flex-basis: 100%;
}

@media (max-width: 760px) {
  .common-pagination {
    align-items: stretch;
    flex-direction: column;
  }

  .pagination-controls {
    justify-content: flex-start;
  }
}
</style>
