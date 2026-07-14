import { computed, readonly, ref } from 'vue'

const activeRequests = ref(0)
const lastError = ref<string | null>(null)

function startRequest() {
  activeRequests.value += 1
}

function finishRequest() {
  activeRequests.value = Math.max(0, activeRequests.value - 1)
}

function setLastError(message: string | null) {
  lastError.value = message
}

/** Global request state used by loading indicators and error notifications. */
export const requestStore = {
  activeRequests: readonly(activeRequests),
  isLoading: computed(() => activeRequests.value > 0),
  lastError: readonly(lastError),
  startRequest,
  finishRequest,
  setLastError
}
