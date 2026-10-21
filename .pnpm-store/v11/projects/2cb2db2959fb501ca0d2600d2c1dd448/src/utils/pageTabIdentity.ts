import type { LocationQuery } from 'vue-router'

import { API_MODULE_TAB_KEY, DETAIL_PAGE_TABS } from '../constants/routes'

type PageRoute = { path: string; query: LocationQuery }

function cleanPath(path: string) {
  return path.split(/[?#]/)[0].replace(/\/+$/, '') || '/'
}

export function pageTabKey(route: PageRoute) {
  const path = cleanPath(route.path)
  const detail = DETAIL_PAGE_TABS.find(item => item.pattern.test(path))
  if (detail) return detail.key
  const moduleValue = route.query.module_id
  const moduleId = Number(Array.isArray(moduleValue) ? moduleValue[0] : moduleValue)
  return path === '/api/interfaces' && Number.isInteger(moduleId) && moduleId > 0
    ? API_MODULE_TAB_KEY : path
}

export function pageTabTitle(route: PageRoute, fallbackTitle: string) {
  return pageTabKey(route) === API_MODULE_TAB_KEY ? 'API 列表' : fallbackTitle.trim() || '未命名页面'
}

export function isParentPage(previousPath: string, route: PageRoute) {
  const detail = DETAIL_PAGE_TABS.find(item => item.pattern.test(cleanPath(previousPath)))
  return Boolean(detail?.parents.includes(pageTabKey(route)))
}

export function storedPageRoute(fullPath: string): PageRoute | null {
  try {
    const url = new URL(fullPath, 'http://localhost')
    return { path: url.pathname, query: { module_id: url.searchParams.get('module_id') } }
  } catch {
    return null
  }
}
