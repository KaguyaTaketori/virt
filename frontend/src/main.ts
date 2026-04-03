import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { VueQueryPlugin } from '@tanstack/vue-query'
import naive from 'naive-ui'
import router from './router'
import App from './App.vue'
import './style.css'

const app = createApp(App)

app.config.errorHandler = (err, instance, info) => {
  console.error('[Global Error]', { err, info, component: instance?.$options.name })
  // 生产环境可在此上报到 Sentry 等平台：
  // if (import.meta.env.PROD) Sentry.captureException(err, { extra: { info } })
}

app.config.warnHandler = (msg, instance, trace) => {
  if (import.meta.env.DEV) {
    console.warn('[Vue Warn]', msg, trace)
  }
}

app.use(createPinia())
app.use(VueQueryPlugin)
app.use(router)
app.use(naive)

app.mount('#app')
 