import { createApp, h } from 'vue'
import { createMemoryHistory, createRouter, RouterView } from 'vue-router'
import ApiFlowsPage from '../src/views/api-testing/ApiFlowsPage.vue'
import ApiFlowDetailPage from '../src/views/api-testing/ApiFlowDetailPage.vue'
import '../src/styles/index.css'
const router = createRouter({history: createMemoryHistory(), routes: [
  {path: '/api/flows', component: ApiFlowsPage},
  {path: '/api/flows/:flowId', component: ApiFlowDetailPage}
]})
await router.push(window.location.search.includes('list') ? '/api/flows' : '/api/flows/1')
createApp({render: () => h(RouterView)}).use(router).mount('#app')
