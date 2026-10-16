import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

import { DEFAULT_AUTHENTICATED_PATH } from './constants/routes'
import { useAuthStore } from './store/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('./views/auth/LoginPage.vue'),
    meta: { public: true, title: '登录' }
  },
  {
    path: '/',
    component: () => import('./layouts/AppLayout.vue'),
    children: [
      { path: '', redirect: DEFAULT_AUTHENTICATED_PATH },
      { path: 'system/users', component: () => import('./views/system/SystemUsersPage.vue'), meta: { title: '用户管理' } },
      { path: 'system/dictionaries', component: () => import('./views/system/DictionariesPage.vue'), meta: { title: '字典信息' } },
      { path: 'system/operation-logs', component: () => import('./views/system/OperationLogsPage.vue'), meta: { title: '用户操作日志' } },
      { path: 'projects/info', component: () => import('./views/projects/ProjectInfoPage.vue'), meta: { title: '项目信息' } },
      { path: 'projects/auth', component: () => import('./views/projects/ProjectAuthPage.vue'), meta: { title: '项目鉴权' } },
      { path: 'projects/knowledge', component: () => import('./views/projects/KnowledgePage.vue'), meta: { title: '用例知识库' } },
      { path: 'projects/app-knowledge', component: () => import('./views/projects/AppKnowledgePage.vue'), meta: { title: 'App 知识库' } },
      { path: 'api/interfaces', component: () => import('./views/api-testing/ApiInterfacesPage.vue'), meta: { title: 'API 管理' } },
      { path: 'api/interfaces/:interfaceId', component: () => import('./views/api-testing/ApiInterfaceDetailPage.vue'), meta: { title: 'API 详情' } },
      { path: 'api/flows', component: () => import('./views/api-testing/ApiFlowsPage.vue'), meta: { title: 'API 功能管理' } },
      { path: 'api/flows/:flowId', component: () => import('./views/api-testing/ApiFlowDetailPage.vue'), meta: { title: 'API 功能详情', keyByPath: true } },
      { path: 'web/pages', component: () => import('./views/web-testing/WebPagesPage.vue'), meta: { title: '页面管理' } },
      { path: 'web/pages/:pageId', component: () => import('./views/web-testing/WebPageFunctionsPage.vue'), meta: { title: '页面功能', keyByPath: true } },
      { path: 'web/pages/:pageId/features/:featureId', component: () => import('./views/web-testing/WebFunctionDetailPage.vue'), meta: { title: '功能详情', keyByPath: true } },
      { path: 'web/features/:featureId', component: () => import('./views/web-testing/WebFunctionDetailPage.vue'), meta: { title: '功能详情', keyByPath: true } },
      { path: 'app/devices', component: () => import('./views/app-testing/AppDevicesPage.vue'), meta: { title: 'App 设备池' } },
      { path: 'app/entries', component: () => import('./views/app-testing/AppEntriesPage.vue'), meta: { title: 'App 应用入口' } },
      { path: 'app/features', component: () => import('./views/app-testing/AppFeaturesPage.vue'), meta: { title: 'App 功能测试' } },
      { path: 'app/features/:featureId', component: () => import('./views/app-testing/AppFeatureDetailPage.vue'), meta: { title: 'App 功能详情' } },
      { path: 'app/features/:featureId/scenarios/:scenarioId', component: () => import('./views/app-testing/AppScenarioDetailPage.vue'), meta: { title: 'App 场景详情' } },
      { path: 'system/model-configs', component: () => import('./views/system/ModelConfigsPage.vue'), meta: { title: '模型配置' } },
      { path: 'execution/generation-tasks', component: () => import('./views/execution/GenerationTasksPage.vue'), meta: { title: '生成记录' } },
      { path: 'execution/dashboard', component: () => import('./views/execution/ExecutionDashboardPage.vue'), meta: { title: '执行看板' } },
      { path: 'execution/flows', redirect: '/api/flows' },
      { path: 'execution/flows/:flowId', redirect: to => `/api/flows/${to.params.flowId}` },
      { path: 'execution/plans', component: () => import('./views/execution/ExecutionPlansPage.vue'), meta: { title: '执行计划' } },
      { path: 'execution/plans/:planId', component: () => import('./views/execution/ExecutionPlanDetailPage.vue'), meta: { title: '执行计划详情' } },
      { path: 'execution/agents', component: () => import('./views/execution/ExecutionAgentsPage.vue'), meta: { title: '执行节点' } },
      { path: 'reports/records', component: () => import('./views/reports/ReportRecordsPage.vue'), meta: { title: '执行记录' } },
      { path: 'reports/statistics', component: () => import('./views/reports/ReportStatisticsPage.vue'), meta: { title: '统计报告' } }
    ]
  },
  { path: '/app/:pathMatch(.*)*', redirect: DEFAULT_AUTHENTICATED_PATH },
  { path: '/miniapp/:pathMatch(.*)*', redirect: DEFAULT_AUTHENTICATED_PATH },
  { path: '/:pathMatch(.*)*', redirect: DEFAULT_AUTHENTICATED_PATH }
]

export const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
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
