import { readonly, ref } from 'vue'
import type { LocationQuery, RouteLocationNormalizedLoaded } from 'vue-router'

import { DEFAULT_AUTHENTICATED_PATH } from '../constants/routes'
import { readSessionValue, writeSessionValue } from '../utils/browserSession'

export interface OpenedPageTab {
  key: string
  path: string
  title: string
  closable: boolean
}

const STORAGE_KEY = 'opened_page_tabs'
const MAX_TABS = 20
const REMOVED_PAGE_PATHS = new Set(['/api/case-drafts', '/api/cases', '/web/elements', '/web/case-drafts', '/web/cases'])
const DEFAULT_TAB: OpenedPageTab = {
  key: DEFAULT_AUTHENTICATED_PATH,
  path: DEFAULT_AUTHENTICATED_PATH,
  title: '统计报告',
  closable: true
}

const tabs = ref<OpenedPageTab[]>(readStoredTabs())

export function pageTabKey(route: { path: string; query: LocationQuery }) {
  if (route.path === '/api/interfaces') {
    const moduleId = singleQueryValue(route.query.module_id)
    if (moduleId) {
      const projectId = singleQueryValue(route.query.project_id)
      return `${route.path}?project_id=${projectId}&module_id=${moduleId}`
    }
  }
  return route.path
}

function openRoute(route: RouteLocationNormalizedLoaded, fallbackTitle: string) {
  const key = pageTabKey(route)
  const existingIndex = tabs.value.findIndex(tab => tab.key === key)
  if (existingIndex >= 0) {
    const next = [...tabs.value]
    next[existingIndex] = { ...next[existingIndex], path: route.fullPath }
    setTabs(next)
    return
  }

  const next = [...tabs.value]
  if (next.length >= MAX_TABS) {
    const removableIndex = next.findIndex(tab => tab.closable)
    if (removableIndex >= 0) next.splice(removableIndex, 1)
  }
  next.push({
    key,
    path: route.fullPath,
    title: fallbackTitle || '未命名页面',
    closable: true
  })
  setTabs(next)
}

function setTitle(key: string, title: string) {
  const cleanTitle = title.trim()
  if (!cleanTitle) return
  setTabs(tabs.value.map(tab => tab.key === key ? { ...tab, title: cleanTitle } : tab))
}

function closeTab(key: string) {
  const index = tabs.value.findIndex(tab => tab.key === key)
  if (index < 0 || !tabs.value[index].closable) return null
  const next = tabs.value.filter(tab => tab.key !== key)
  const nextActive = next[Math.min(index, next.length - 1)] || DEFAULT_TAB
  setTabs(next)
  return nextActive.path
}

function closeOtherTabs(activeKey: string) {
  setTabs(tabs.value.filter(tab => !tab.closable || tab.key === activeKey))
}

function closeAllTabs() {
  setTabs([DEFAULT_TAB])
}

function pruneTabs(isValidPath: (path: string) => boolean) {
  setTabs(tabs.value.filter(tab => !tab.closable || isValidPath(tab.path)))
}

function clearTabs() {
  setTabs([DEFAULT_TAB])
}

function setTabs(next: OpenedPageTab[]) {
  const normalized = normalizeTabs(next)
  tabs.value = normalized
  if (typeof window !== 'undefined') {
    writeSessionValue(STORAGE_KEY, JSON.stringify(normalized))
  }
}

function readStoredTabs() {
  if (typeof window === 'undefined') return [DEFAULT_TAB]
  try {
    const raw = readSessionValue(STORAGE_KEY)
    return normalizeTabs(raw ? JSON.parse(raw) : [])
  } catch {
    return [DEFAULT_TAB]
  }
}

function normalizeTabs(value: unknown): OpenedPageTab[] {
  const source = Array.isArray(value) ? value : []
  const result: OpenedPageTab[] = []
  const keys = new Set<string>()
  for (const item of source) {
    if (!isStoredTab(item) || keys.has(item.key) || result.length >= MAX_TABS) continue
    if ([item.key, item.path].some(path => REMOVED_PAGE_PATHS.has(path.split(/[?#]/)[0].replace(/\/$/, '')))) continue
    keys.add(item.key)
    result.push({ ...item, closable: true })
  }
  return result.length ? result : [DEFAULT_TAB]
}

function isStoredTab(value: unknown): value is OpenedPageTab {
  if (typeof value !== 'object' || value === null) return false
  const item = value as Record<string, unknown>
  return typeof item.key === 'string'
    && item.key.startsWith('/')
    && typeof item.path === 'string'
    && item.path.startsWith('/')
    && typeof item.title === 'string'
    && item.title.trim().length > 0
}

function singleQueryValue(value: LocationQuery[string]) {
  const current = Array.isArray(value) ? value[0] : value
  return current == null ? '' : String(current)
}

export function usePageTabsStore() {
  return {
    tabs: readonly(tabs),
    openRoute,
    setTitle,
    closeTab,
    closeOtherTabs,
    closeAllTabs,
    pruneTabs,
    clearTabs
  }
}
