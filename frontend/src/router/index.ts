import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import Home from '../views/Home.vue'
import MultiView from '../views/MultiView.vue'

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
    path: '/multiview/:platform/:ids',
    name: 'MultiViewIds',
    component: MultiView
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
