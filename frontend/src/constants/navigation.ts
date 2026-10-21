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
      { label: '项目鉴权', path: '/projects/auth' }
    ]
  },
  {
    title: '知识库管理',
    items: [
      { label: '用例知识库', path: '/projects/knowledge' },
      { label: 'App知识库', path: '/projects/app-knowledge' },
      { label: '执行计划', path: '/execution/plans' }
    ]
  },
  {
    title: 'API 测试',
    items: [
      { label: 'API 管理', path: '/api/interfaces' },
      { label: 'API 功能管理', path: '/api/flows' },
      { label: 'API 报告', path: '/api/reports' }
    ]
  },
  {
    title: 'Web 测试',
    items: [
      { label: '页面管理', path: '/web/pages' }
    ]
  },
  {
    title: 'App 测试',
    items: [
      { label: '设备池', path: '/app/devices' },
      { label: '应用入口', path: '/app/entries' },
      { label: '功能测试', path: '/app/features' }
    ]
  },
  {
    title: '小程序测试',
    items: [
      { label: '页面功能', path: '/miniapp/pages' },
      { label: '用例与业务流程', path: '/miniapp/cases' }
    ]
  },
  {
    title: '执行管理',
    items: [
      { label: '执行看板', path: '/execution/dashboard' },
      { label: '生成记录', path: '/execution/generation-tasks' },
      { label: '执行节点', path: '/execution/agents' }
    ]
  },
  {
    title: '系统管理',
    items: [
      { label: '用户管理', path: '/system/users' },
      { label: '模型配置', path: '/system/model-configs' },
      { label: '字典信息', path: '/system/dictionaries' },
      { label: '用户操作日志', path: '/system/operation-logs' }
    ]
  }
]

export const hiddenFeaturePrefixes: readonly string[] = []
