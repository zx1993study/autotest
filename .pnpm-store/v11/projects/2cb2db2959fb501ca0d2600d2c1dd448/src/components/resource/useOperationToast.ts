import { onUnmounted, ref } from 'vue'

export function useOperationToast() {
  const operationToastVisible = ref(false)
  const operationToastTitle = ref('')
  const operationToastMessage = ref('')
  let operationToastTimer: ReturnType<typeof window.setTimeout> | undefined

  function showOperationToast(title: string, text: string) {
    operationToastTitle.value = title
    operationToastMessage.value = text
    operationToastVisible.value = true
    if (operationToastTimer) {
      window.clearTimeout(operationToastTimer)
    }
    operationToastTimer = window.setTimeout(closeOperationToast, 3000)
  }

  function closeOperationToast() {
    if (operationToastTimer) {
      window.clearTimeout(operationToastTimer)
    }
    operationToastTimer = undefined
    operationToastVisible.value = false
  }

  onUnmounted(closeOperationToast)

  return {
    operationToastVisible,
    operationToastTitle,
    operationToastMessage,
    showOperationToast,
    closeOperationToast
  }
}
