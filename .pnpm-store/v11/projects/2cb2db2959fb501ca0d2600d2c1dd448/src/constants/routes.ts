export const DEFAULT_AUTHENTICATED_PATH = '/reports/statistics'

export const API_MODULE_TAB_KEY = '/api/interfaces/:module'

export const DETAIL_PAGE_TABS = [
  { pattern: /^\/api\/interfaces\/[^/]+$/, key: '/api/interfaces/:detail', parents: ['/api/interfaces', API_MODULE_TAB_KEY] },
  { pattern: /^\/api\/flows\/[^/]+$/, key: '/api/flows/:detail', parents: ['/api/flows'] },
  { pattern: /^\/web\/pages\/[^/]+$/, key: '/web/pages/:detail', parents: ['/web/pages'] },
  { pattern: /^\/web\/pages\/[^/]+\/features\/[^/]+$/, key: '/web/features/:detail', parents: ['/web/pages/:detail', '/web/pages'] },
  { pattern: /^\/web\/features\/[^/]+$/, key: '/web/features/:detail', parents: ['/web/pages/:detail', '/web/pages'] },
  { pattern: /^\/app\/features\/[^/]+$/, key: '/app/features/:detail', parents: ['/app/features'] },
  { pattern: /^\/app\/features\/[^/]+\/scenarios\/[^/]+$/, key: '/app/features/:detail/scenarios/:detail', parents: ['/app/features/:detail', '/app/features'] },
  { pattern: /^\/execution\/plans\/[^/]+$/, key: '/execution/plans/:detail', parents: ['/execution/plans'] }
]
