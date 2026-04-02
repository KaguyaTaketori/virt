import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

declare module 'vue-router' {
  interface RouteMeta {
    fullscreen?: boolean
    title?: string
  }
}

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Home',
    component: () => import('../views/Home.vue'),
    meta: { title: '直播列表' },
  },
  {
    path: '/multiview',
    name: 'MultiView',
    component: () => import('../views/MultiView.vue'),
    meta: { fullscreen: true, title: '多窗播放' },
  },
  {
    path: '/channels',
    name: 'Channels',
    component: () => import('../views/Channels.vue'),
    meta: { title: '频道' },
  },
  {
    path: '/channel/:id',
    name: 'ChannelDetail',
    component: () => import('../views/ChannelDetail.vue'),
    meta: { title: '频道详情' },
  },
  {
    path: '/admin/channels',
    name: 'AdminChannels',
    component: () => import('../views/AdminChannels.vue'),
    meta: { title: '频道管理' },
  },
  {
    path: '/admin/organizations',
    name: 'AdminOrganizations',
    component: () => import('../views/AdminOrganizations.vue'),
    meta: { title: '机构管理' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router