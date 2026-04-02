import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

declare module 'vue-router' {
  interface RouteMeta {
    fullscreen?: boolean
    title?: string
    requiresAdmin?: boolean
    requiresSuperadmin?: boolean
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
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { fullscreen: true, title: '登录' },
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
  {
    path: '/admin/users',
    name: 'AdminUsers',
    component: () => import('../views/AdminUsers.vue'),
    meta: { title: '用户管理', requiresAdmin: true },
  },
  {
    path: '/admin/roles',
    name: 'AdminRoles',
    component: () => import('../views/AdminRoles.vue'),
    meta: { title: '角色与权限', requiresSuperadmin: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  
  if (to.meta.requiresSuperadmin && !authStore.isSuperAdmin) {
    next({ name: 'Home', query: { error: 'no_permission' } })
    return
  }
  
  if (to.meta.requiresAdmin && !authStore.isAdmin) {
    next({ name: 'Home', query: { error: 'no_permission' } })
    return
  }
  
  next()
})

export default router