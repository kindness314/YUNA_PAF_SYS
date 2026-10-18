import { createPinia } from 'pinia'
import { createApp } from 'vue'
import type { Component } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as Icons from '@element-plus/icons-vue'
import FcDesigner from '@form-create/designer'
import formCreate from '@form-create/element-ui'
import VChart from 'vue-echarts'
import 'echarts'

import App from './App.vue'
import router from './router'
import './styles.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(ElementPlus)
for (const [name, comp] of Object.entries(Icons)) {
  // 图标包所有导出均为现成 Vue 组件，此转换仅统一类型
  const icon = comp as Component
  app.component(name, icon)
}
app.use(formCreate)
app.use(FcDesigner)
app.component('VChart', VChart)

app.mount('#app')
