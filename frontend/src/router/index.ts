import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import Home from '../views/Home.vue'
import MultiView from '../views/MultiView.vue'
import AdminChannels from '../views/AdminChannels.vue'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/multiview',
    name: 'MultiView',
    component: MultiView
  },
  {
    path: '/admin/channels',
    name: 'AdminChannels',
    component: AdminChannels
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
