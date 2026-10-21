import { onBeforeUnmount, ref, watch } from 'vue'

import { batchDeleteResources, deleteResource } from '../api/http'

interface DeletionOptions {
  path: () => string
  scope: () => string
  reload: (deletedCount: number) => Promise<void>
  success: (deletedCount: number) => void
}

export function useResourceDeletion(options: DeletionOptions) {
  const deleting = ref(false)
  const deleteError = ref('')
  let disposed = false
  onBeforeUnmount(() => { disposed = true })
  watch(options.scope, () => { deleteError.value = '' })

  async function removeResources(ids: number[], batch = true, afterReload?: () => Promise<void>) {
    if (deleting.value || !ids.length) return
    const uniqueIds = [...new Set(ids)]
    if (!window.confirm(`确认删除选中的 ${uniqueIds.length} 条数据吗？`)) return
    const path = options.path()
    const scope = options.scope()
    deleting.value = true
    deleteError.value = ''
    try {
      let count = 1
      if (batch) count = (await batchDeleteResources(path, uniqueIds)).deleted_count
      else await deleteResource(path, uniqueIds[0])
      if (disposed || options.scope() !== scope) return
      await options.reload(count)
      if (disposed || options.scope() !== scope) return
      options.success(count)
      await afterReload?.()
    } catch (error) {
      if (!disposed && options.scope() === scope) {
        deleteError.value = error instanceof Error ? error.message : '删除失败，请重试'
      }
    } finally {
      deleting.value = false
    }
  }

  return { deleting, deleteError, removeResources }
}
