type JsonParseResult = {
  matched: boolean
  value: unknown
}

type JsonSegment = {
  start: number
  end: number
  text: string
}

/**
 * Formats API response bodies for result panes.
 *
 * The executor stores response bodies as text, and long responses may be
 * truncated before display. This formatter first tries strict JSON parsing,
 * then falls back to balanced JSON extraction and finally to a defensive
 * pretty-printer so truncated JSON still remains readable.
 */
export function formatJsonLikeText(value: unknown, emptyText = '-'): string {
  if (value == null || value === '') {
    return emptyText
  }
  if (typeof value !== 'string') {
    return stringifyJson(value)
  }

  const raw = stripBom(value).trim()
  if (!raw) {
    return emptyText
  }

  const parsed = parseJsonLikeText(raw)
  if (parsed.matched) {
    return stringifyJson(parsed.value)
  }

  const segment = extractFirstBalancedJson(raw)
  if (segment) {
    const segmentParsed = parseJsonLikeText(segment.text)
    if (segmentParsed.matched) {
      return [
        raw.slice(0, segment.start).trim(),
        stringifyJson(segmentParsed.value),
        raw.slice(segment.end + 1).trim()
      ].filter(Boolean).join('\n')
    }
  }

  return looksJsonish(raw) ? prettyPrintJsonLike(raw) : raw
}

function stringifyJson(value: unknown): string {
  return JSON.stringify(value ?? {}, null, 2)
}

function parseJsonLikeText(value: string): JsonParseResult {
  let current: unknown = value
  let matched = false
  for (let index = 0; index < 3; index += 1) {
    if (typeof current !== 'string') {
      return { matched: true, value: current }
    }
    const trimmed = stripBom(current).trim()
    if (!looksLikeJsonText(trimmed)) {
      return { matched, value: current }
    }
    try {
      current = JSON.parse(trimmed) as unknown
      matched = true
    } catch {
      return { matched, value: current }
    }
  }
  return { matched, value: current }
}

function looksLikeJsonText(value: string): boolean {
  const first = firstNonWhitespace(value)
  if (!first) {
    return false
  }
  if (first === '"') {
    return value.endsWith('"')
  }
  return first === '{' || first === '['
}

function looksJsonish(value: string): boolean {
  const first = firstNonWhitespace(value)
  return first === '{' || first === '[' || value.includes('":') || value.includes(':{')
}

function extractFirstBalancedJson(value: string): JsonSegment | null {
  const starts = [value.indexOf('{'), value.indexOf('[')]
    .filter(index => index >= 0)
    .sort((left, right) => left - right)

  for (const start of starts) {
    const end = findBalancedJsonEnd(value, start)
    if (end != null) {
      return { start, end, text: value.slice(start, end + 1) }
    }
  }
  return null
}

function findBalancedJsonEnd(value: string, start: number): number | null {
  const stack: string[] = []
  let inString = false
  let escaped = false

  for (let index = start; index < value.length; index += 1) {
    const char = value[index]
    if (inString) {
      if (escaped) {
        escaped = false
      } else if (char === '\\') {
        escaped = true
      } else if (char === '"') {
        inString = false
      }
      continue
    }

    if (char === '"') {
      inString = true
      continue
    }
    if (char === '{' || char === '[') {
      stack.push(char)
      continue
    }
    if (char === '}' || char === ']') {
      const open = stack.pop()
      if (!open || !isMatchingPair(open, char)) {
        return null
      }
      if (stack.length === 0) {
        return index
      }
    }
  }
  return null
}

function prettyPrintJsonLike(value: string): string {
  let result = ''
  let indent = 0
  let inString = false
  let escaped = false

  for (let index = 0; index < value.length; index += 1) {
    const char = value[index]

    if (inString) {
      result += char
      if (escaped) {
        escaped = false
      } else if (char === '\\') {
        escaped = true
      } else if (char === '"') {
        inString = false
      }
      continue
    }

    if (char === '"') {
      inString = true
      result += char
      continue
    }

    if (char === '{' || char === '[') {
      result += char
      indent += 1
      if (!isClosingChar(nextNonWhitespace(value, index + 1))) {
        result = appendNewline(result, indent)
      }
      continue
    }

    if (char === '}' || char === ']') {
      indent = Math.max(indent - 1, 0)
      if (!isOpeningChar(previousNonWhitespace(result))) {
        result = appendNewline(result, indent)
      }
      result += char
      continue
    }

    if (char === ',') {
      result += char
      result = appendNewline(result, indent)
      continue
    }

    if (char === ':') {
      result += ': '
      continue
    }

    result += char
  }

  return result.replace(/[ \t]+\n/g, '\n').trim()
}

function appendNewline(value: string, indent: number): string {
  return `${value.trimEnd()}\n${'  '.repeat(Math.max(indent, 0))}`
}

function stripBom(value: string): string {
  return value.replace(/^\uFEFF/, '')
}

function firstNonWhitespace(value: string): string {
  return value.trimStart().charAt(0)
}

function nextNonWhitespace(value: string, start: number): string {
  for (let index = start; index < value.length; index += 1) {
    const char = value[index]
    if (!/\s/.test(char)) {
      return char
    }
  }
  return ''
}

function previousNonWhitespace(value: string): string {
  for (let index = value.length - 1; index >= 0; index -= 1) {
    const char = value[index]
    if (!/\s/.test(char)) {
      return char
    }
  }
  return ''
}

function isOpeningChar(value: string): boolean {
  return value === '{' || value === '['
}

function isClosingChar(value: string): boolean {
  return value === '}' || value === ']'
}

function isMatchingPair(open: string, close: string): boolean {
  return (open === '{' && close === '}') || (open === '[' && close === ']')
}
