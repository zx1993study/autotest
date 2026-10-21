const sensitiveKey = /authorization|cookie|password|passwd|pwd|secret|token|api[-_]?key|storage[-_]?state|client[-_]?key/i
const fieldAssignment = /(["']?(?:authorization|cookie|set-cookie|password|passwd|pwd|[\w-]*token|[\w-]*secret|api[_-]?key)["']?\s*[:=]\s*)("[^"\n]*(?:"|$)|'[^'\n]*(?:'|$)|[^\s,};&]+)/gi

export function isEvidenceObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

export function parseEvidence(value: unknown): unknown {
  let current = value
  for (let index = 0; index < 3 && typeof current === 'string'; index += 1) {
    try { current = JSON.parse(current) as unknown } catch { break }
  }
  return current
}

export function redactEvidence(value: unknown, depth = 0): unknown {
  if (depth > 30) return '[内容过深]'
  if (typeof value === 'string') {
    const parsed = parseEvidence(value)
    return parsed !== value ? redactEvidence(parsed, depth + 1) : redactText(value)
  }
  if (Array.isArray(value)) return value.map(item => redactEvidence(item, depth + 1))
  if (!isEvidenceObject(value)) return value
  const field = [value.field, value.path, value.selector, value.locator, value.input_type].join(' ')
  return Object.fromEntries(Object.entries(value).map(([key, item]) => [
    key,
    sensitiveKey.test(key) || (sensitiveKey.test(field) && ['value', 'expected', 'actual'].includes(key))
      ? '***' : redactEvidence(item, depth + 1)
  ]))
}

function redactText(value: string): string {
  return value.replace(/https?:\/\/[^\s"'<>]+/g, raw => {
    try {
      const url = new URL(raw)
      if (url.username) url.username = '***'
      if (url.password) url.password = '***'
      for (const key of [...url.searchParams.keys()]) {
        if (sensitiveKey.test(key)) url.searchParams.set(key, '***')
      }
      return url.toString()
    } catch { return raw }
  }).replace(/\bBearer\s+[^\s"',}]+/gi, 'Bearer ***').replace(fieldAssignment, '$1***')
}
