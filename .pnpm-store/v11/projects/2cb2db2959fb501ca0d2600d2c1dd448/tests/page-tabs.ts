import { router } from '../src/router'
import { pageTabKey, usePageTabsStore } from '../src/store/page-tabs'
import { API_MODULE_TAB_KEY } from '../src/constants/routes'

const store = usePageTabsStore()

function assert(value: unknown, message: string) {
  if (!value) throw new Error(message)
}

function open(path: string, previousPath?: string, title = 'Test page') {
  const route = router.resolve(path)
  store.openRoute(route, title, previousPath)
  return pageTabKey(route)
}

function checkDetails() {
  const pairs = [
    ['/api/interfaces/10', '/api/interfaces/11', '/api/interfaces?project_id=1&module_id=22'],
    ['/api/flows/1', '/api/flows/2', '/api/flows'],
    ['/web/pages/10', '/web/pages/20', '/web/pages'],
    ['/web/pages/10/features/101', '/web/pages/20/features/202', '/web/pages/20'],
    ['/web/features/101', '/web/features/202', '/web/pages/20'],
    ['/app/features/10', '/app/features/20', '/app/features'],
    ['/app/features/10/scenarios/101', '/app/features/20/scenarios/202', '/app/features/20'],
    ['/execution/plans/10', '/execution/plans/20', '/execution/plans']
  ]
  for (const [first, second, parent] of pairs) {
    store.clearTabs()
    open(parent)
    const key = open(first, undefined, 'First title')
    const index = store.tabs.value.findIndex(tab => tab.key === key)
    const count = store.tabs.value.length
    const latest = `${second}?project_id=2#latest`
    assert(open(latest, first, 'Updated title') === key, `detail identity changed: ${first}`)
    assert(store.tabs.value.length === count, `duplicate detail tab: ${second}`)
    assert(store.tabs.value[index].path === latest, `latest detail path was lost: ${second}`)
    assert(store.tabs.value[index].title === 'Updated title', `latest title was lost: ${second}`)
    open(parent, latest)
    assert(!store.tabs.value.some(tab => tab.key === key), `return left a stale detail: ${second}`)
    assert(store.tabs.value.length === count - 1, `return added a parent tab: ${parent}`)
    store.clearTabs()
    open(first)
    open(parent, first)
    assert(store.tabs.value.length === 2, `direct-entry return added a tab: ${parent}`)
  }
}

function checkRouteCoverage() {
  for (const route of router.getRoutes().filter(route => route.components && route.meta.title)) {
    const first = route.path.replace(/:[A-Za-z]+/g, '10')
    const second = route.path.replace(/:[A-Za-z]+/g, '20')
    store.clearTabs()
    const key = open(`${first}?project_id=1`)
    const count = store.tabs.value.length
    assert(open(`${second}?project_id=2`) === key, `page type is not reusable: ${route.path}`)
    assert(store.tabs.value.length === count, `page type was duplicated: ${route.path}`)
    if (first !== second) assert(route.meta.keyByPath, `detail does not reload its data: ${route.path}`)
  }
}

function checkModulesAndAliases() {
  store.clearTabs()
  open('/api/interfaces?project_id=1', undefined, 'Directory')
  open('/api/interfaces?project_id=1&module_id=21', undefined, 'API management')
  const latest = '/api/interfaces?project_id=2&module_id=22&keyword=latest#cases'
  open(latest, undefined, 'API management')
  const modules = store.tabs.value.filter(tab => tab.key === API_MODULE_TAB_KEY)
  assert(modules.length === 1 && modules[0].path === latest, 'module lists did not share a tab')
  assert(modules[0].title === 'API 列表', 'module title was not updated')
  assert(store.tabs.value.some(tab => tab.key === '/api/interfaces'), 'directory tab was overwritten')
  const key = open('/web/features/101')
  open('/web/pages/20/features/202')
  assert(store.tabs.value.filter(tab => tab.key === key).length === 1, 'Web detail aliases were duplicated')
  assert(pageTabKey({ path: '/web/pages/20/', query: {} }) === '/web/pages/:detail', 'trailing slash split identity')
  open('/system/users', undefined, 'Shared label')
  open('/projects/info', undefined, 'Shared label')
  assert(store.tabs.value.some(tab => tab.key === '/system/users')
    && store.tabs.value.some(tab => tab.key === '/projects/info'), 'unrelated page types were merged by label')
}

function checkClosingAndLimit() {
  store.clearTabs()
  const key = open('/web/pages/10')
  open('/web/pages/20')
  store.closeOtherTabs(key)
  assert(store.tabs.value.length === 1 && store.tabs.value[0].path === '/web/pages/20', 'close others lost latest path')
  assert(store.closeTab(key) === '/reports/statistics', 'close did not fall back to default page')
  assert(store.tabs.value.length === 1, 'closing last tab did not restore default')
  for (let i = 0; i < 24; i += 1) open(`/test/page-${i}`)
  assert(store.tabs.value.length === 20, 'tab limit changed')
  const firstKey = store.tabs.value[0].key
  open('/test/page-23?updated=1')
  assert(store.tabs.value.length === 20 && store.tabs.value[0].key === firstKey, 'reuse evicted another tab')
  store.closeAllTabs()
  assert(store.tabs.value.length === 1, 'close all did not reset tabs')
}

Object.assign(window, {
  pageTabSnapshot: () => JSON.parse(JSON.stringify(store.tabs.value)),
  runPageTabChecks: () => {
    checkDetails()
    checkRouteCoverage()
    checkModulesAndAliases()
    checkClosingAndLimit()
    return { passed: true, groups: 4, routes: router.getRoutes().filter(route => route.components && route.meta.title).length }
  }
})
