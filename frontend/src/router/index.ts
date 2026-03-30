import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import Home from '../views/Home.vue'
import MultiView from '../views/MultiView.vue'
import Channels from '../views/Channels.vue'
import ChannelDetail from '../views/ChannelDetail.vue'
import AdminChannels from '../views/AdminChannels.vue'
import AdminOrganizations from '../views/AdminOrganizations.vue'

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
    path: '/channels',
    name: 'Channels',
    component: Channels
  },
  {
    path: '/channel/:id',
    name: 'ChannelDetail',
    component: ChannelDetail
  },
  {
    path: '/admin/channels',
    name: 'AdminChannels',
    component: AdminChannels
  },
  {
    path: '/admin/organizations',
    name: 'AdminOrganizations',
    component: AdminOrganizations
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
