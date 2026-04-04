import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { VueQueryPlugin, QueryClient } from '@tanstack/vue-query'
import naive from 'naive-ui'
import router from './router'
import App from './App.vue'
import './style.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 60_000 },
  },
})

import { setSharedQueryClient } from './stores/auth'

const app = createApp(App)
const pinia = createPinia()

app.config.errorHandler = (err, _instance, info) => {
  console.error('[Global Error]', { err, info })
}

app.use(pinia)

setSharedQueryClient(queryClient)

app.use(VueQueryPlugin, { queryClient })
app.use(router)
app.use(naive)
app.mount('#app')