/** Navigation metadata consumed by the global application layout. */

export interface NavigationItem {
  label: string
  path: string
}

export interface NavigationGroup {
  title: string
  items: NavigationItem[]
}

export const navigationGroups: NavigationGroup[] = [
  {
    title: '执行报告',
    items: [
      { label: '统计报告', path: '/reports/statistics' },
      { label: '执行记录', path: '/reports/records' }
    ]
  },
  {
    title: '项目管理',
    items: [
      { label: '项目信息', path: '/projects/info' },
      { label: '项目鉴权', path: '/projects/auth' },
      { label: '用例知识库', path: '/projects/knowledge' }
    ]
  },
  {
    title: 'API 测试',
    items: [
      { label: 'API 管理', path: '/api/interfaces' },
      { label: '字段信息', path: '/api/fields' },
      { label: '用例草稿', path: '/api/case-drafts' },
      { label: '正式用例', path: '/api/cases' }
    ]
  },
  {
    title: 'Web 测试',
    items: [
      { label: '页面功能', path: '/web/pages' },
      { label: '元素信息', path: '/web/elements' },
      { label: '用例草稿', path: '/web/case-drafts' },
      { label: '正式用例', path: '/web/cases' }
    ]
  },
  {
    title: 'AI 能力',
    items: [
      { label: '模型配置', path: '/ai/models' },
      { label: 'Prompt模板', path: '/ai/prompts' },
      { label: '生成任务', path: '/ai/tasks' }
    ]
  },
  {
    title: 'App 测试',
    items: [
      { label: 'App 页面功能', path: '/app/pages' },
      { label: 'App 元素', path: '/app/elements' },
      { label: '用例草稿', path: '/app/case-drafts' },
      { label: '正式用例', path: '/app/cases' }
    ]
  },
  {
    title: '小程序测试',
    items: [
      { label: '页面功能', path: '/miniapp/pages' },
      { label: '元素信息', path: '/miniapp/elements' },
      { label: '用例草稿', path: '/miniapp/case-drafts' },
      { label: '正式用例', path: '/miniapp/cases' }
    ]
  },
  {
    title: '执行管理',
    items: [
      { label: '执行看板', path: '/execution/dashboard' },
      { label: '执行流程', path: '/execution/flows' },
      { label: '执行计划', path: '/execution/plans' }
    ]
  },
  {
    title: '系统管理',
    items: [
      { label: '字典信息', path: '/system/dictionaries' },
      { label: '用户操作日志', path: '/system/operation-logs' }
    ]
  }
]

export const hiddenFeaturePrefixes = ['/app/', '/miniapp/'] as const
