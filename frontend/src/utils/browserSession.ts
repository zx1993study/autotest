const fallbackValues = new Map<string, string>()
const storageKey = (key: string) => `autotest.session.${import.meta.env.BASE_URL}${key}`

export function readSessionValue(key: string): string {
  if (fallbackValues.has(key)) return fallbackValues.get(key) || ''
  try { return typeof window === 'undefined' ? '' : window.sessionStorage.getItem(storageKey(key)) || '' } catch { return '' }
}

export function writeSessionValue(key: string, value: string): void {
  fallbackValues.set(key, value)
  try {
    if (typeof window === 'undefined') return
    window.sessionStorage.setItem(storageKey(key), value)
    fallbackValues.delete(key)
  } catch { /* Keep this window's session usable when WebView storage is unavailable. */ }
}

export function removeSessionValue(key: string): void {
  fallbackValues.set(key, '')
  try {
    if (typeof window === 'undefined') return
    window.sessionStorage.removeItem(storageKey(key))
    fallbackValues.delete(key)
  } catch { /* A failed removal must not expose a stale token in this window. */ }
}
