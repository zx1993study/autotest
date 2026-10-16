import { createApp, h } from 'vue'
import { RouterView } from 'vue-router'
import { router } from '../src/router'
import '../src/styles/index.css'

router.afterEach(to => { document.body.dataset.route = to.path })
window.addEventListener('web-workspace:navigate', event => {
  void router.push((event as CustomEvent<string>).detail)
})
await router.push('/web/pages/10')
await router.isReady()
createApp({ render: () => h(RouterView) }).use(router).mount('#app')
