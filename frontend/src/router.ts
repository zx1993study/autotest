import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

import { DEFAULT_AUTHENTICATED_PATH } from './constants/routes'
import { useAuthStore } from './store/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('./views/auth/LoginPage.vue'),
    meta: { public: true }
  },
  {
    path: '/',
    component: () => import('./layouts/AppLayout.vue'),
    children: [
      { path: '', redirect: DEFAULT_AUTHENTICATED_PATH },
      { path: 'system/dictionaries', component: () => import('./views/system/DictionariesPage.vue') },
      { path: 'system/operation-logs', component: () => import('./views/system/OperationLogsPage.vue') },
      { path: 'projects/info', component: () => import('./views/projects/ProjectInfoPage.vue') },
      { path: 'projects/auth', component: () => import('./views/projects/ProjectAuthPage.vue') },
      { path: 'projects/knowledge', component: () => import('./views/projects/KnowledgePage.vue') },
      { path: 'api/interfaces', component: () => import('./views/api-testing/ApiInterfacesPage.vue') },
      { path: 'api/fields', component: () => import('./views/api-testing/ApiFieldsPage.vue') },
      { path: 'api/case-drafts', component: () => import('./views/api-testing/ApiCaseDraftsPage.vue') },
      { path: 'api/cases', component: () => import('./views/api-testing/ApiCasesPage.vue') },
      { path: 'web/pages', component: () => import('./views/web-testing/WebPagesPage.vue') },
      { path: 'web/elements', component: () => import('./views/web-testing/WebElementsPage.vue') },
      { path: 'web/case-drafts', component: () => import('./views/web-testing/WebCaseDraftsPage.vue') },
      { path: 'web/cases', component: () => import('./views/web-testing/WebCasesPage.vue') },
      { path: 'ai/models', component: () => import('./views/ai/AiModelsPage.vue') },
      { path: 'ai/prompts', component: () => import('./views/ai/AiPromptTemplatesPage.vue') },
      { path: 'ai/tasks', component: () => import('./views/ai/AiGenerationTasksPage.vue') },
      { path: 'execution/dashboard', component: () => import('./views/execution/ExecutionDashboardPage.vue') },
      { path: 'execution/flows', component: () => import('./views/execution/ExecutionFlowsPage.vue') },
      { path: 'execution/flows/:flowId', component: () => import('./views/execution/ExecutionFlowDetailPage.vue') },
      { path: 'execution/plans', component: () => import('./views/execution/ExecutionPlansPage.vue') },
      { path: 'reports/records', component: () => import('./views/reports/ReportRecordsPage.vue') },
      { path: 'reports/statistics', component: () => import('./views/reports/ReportStatisticsPage.vue') }
    ]
  },
  { path: '/app/:pathMatch(.*)*', redirect: DEFAULT_AUTHENTICATED_PATH },
  { path: '/miniapp/:pathMatch(.*)*', redirect: DEFAULT_AUTHENTICATED_PATH },
  { path: '/:pathMatch(.*)*', redirect: DEFAULT_AUTHENTICATED_PATH }
]

export const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async to => {
  const authStore = useAuthStore()
  if (!authStore.initialized.value) {
    await authStore.loadCurrentUser()
  }
  if (to.meta.public) {
    return authStore.isAuthenticated.value && to.path === '/login' ? DEFAULT_AUTHENTICATED_PATH : true
  }
  if (!authStore.isAuthenticated.value) {
    return {
      path: '/login',
      query: { redirect: to.fullPath }
    }
  }
  return true
})
