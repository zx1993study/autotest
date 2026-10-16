import { createApp, h, ref } from 'vue'
import ApiModuleSelect from '../src/components/api-case-drafts/ApiModuleSelect.vue'
import '../src/styles/index.css'

createApp({
  setup() {
    const selected = ref<number | string>(1)
    const project = ref(1)
    return () => h('main', { style: 'box-sizing:border-box;width:min(100%,680px);padding:24px;margin:auto' }, [
      h('label', { class: 'field' }, [h('span', '所属模块'), h(ApiModuleSelect, {
        projectId: project.value,
        modelValue: selected.value,
        'onUpdate:modelValue': (value: number | string) => { selected.value = value }
      })]),
      h('button', { id: 'switch-project', type: 'button', onClick: () => { project.value = 2 } }, '切换项目')
    ])
  }
}).mount('#app')
