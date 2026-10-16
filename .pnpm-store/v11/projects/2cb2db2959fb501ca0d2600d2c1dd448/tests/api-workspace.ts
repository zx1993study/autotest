import { createApp, h } from 'vue'
import { createMemoryHistory, createRouter, RouterView } from 'vue-router'
import ApiInterfacesPage from '../src/views/api-testing/ApiInterfacesPage.vue'
import ApiInterfaceDetailPage from '../src/views/api-testing/ApiInterfaceDetailPage.vue'
import '../src/styles/index.css'

const router = createRouter({ history: createMemoryHistory(), routes: [
  { path: '/', component: ApiInterfacesPage },
  { path: '/api/interfaces/:interfaceId', component: ApiInterfaceDetailPage }
] })
await router.push(window.location.search.includes('detail') ? '/api/interfaces/30' : '/')
window.addEventListener('api-workspace:navigate', event => {
  void router.push((event as CustomEvent<string>).detail)
})
createApp({ render: () => h(RouterView) }).use(router).mount('#app')
