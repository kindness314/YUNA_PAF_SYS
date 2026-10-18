import { createApp } from 'vue'
import Vant from 'vant'
import 'vant/lib/index.css'
import formCreate from '@form-create/vant'

import App from './App.vue'
import router from './router'

const app = createApp(App)

app.use(router)
app.use(Vant)
app.use(formCreate as never)

app.mount('#app')
