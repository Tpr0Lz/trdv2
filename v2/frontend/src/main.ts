import { createApp } from 'vue'
import { createPinia } from 'pinia'
import naive from 'naive-ui'

import App from './App.vue'
import router from './router'
import './styles.css'

// 中文注释：前端入口只挂载全局插件，业务状态放在 Pinia store 内。
createApp(App).use(createPinia()).use(router).use(naive).mount('#app')

