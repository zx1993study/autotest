import { createApp, h } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import ProjectAuthPage from '../src/views/projects/ProjectAuthPage.vue'
import '../src/styles/index.css'

const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/', component: { render: () => null } }] })
createApp({ render: () => h(ProjectAuthPage) }).use(router).mount('#app')
