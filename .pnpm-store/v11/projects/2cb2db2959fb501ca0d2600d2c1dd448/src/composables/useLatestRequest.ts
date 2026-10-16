import { onBeforeUnmount, ref } from 'vue'

export function useLatestRequest(fallbackMessage = '加载失败') {
  const loading = ref(false)
  const error = ref('')
  let sequence = 0
  let disposed = false
  let controller: AbortController | undefined

  function cancel() {
    sequence += 1
    controller?.abort()
    controller = undefined
    loading.value = false
    error.value = ''
  }

  async function run<T>(fetcher: (signal: AbortSignal) => Promise<T>, apply: (result: T) => void) {
    if (disposed) return
    controller?.abort()
    const current = ++sequence
    const request = new AbortController()
    controller = request
    loading.value = true
    error.value = ''
    try {
      const result = await fetcher(request.signal)
      if (current === sequence && !request.signal.aborted) apply(result)
    } catch (cause) {
      if (current === sequence && !request.signal.aborted) {
        error.value = cause instanceof Error ? cause.message : fallbackMessage
      }
    } finally {
      if (current === sequence) {
        loading.value = false
        controller = undefined
      }
    }
  }

  onBeforeUnmount(() => { disposed = true; cancel() })
  return { loading, error, run, cancel }
}
