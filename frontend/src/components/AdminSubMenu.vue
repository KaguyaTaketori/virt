<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Tv2, Building2, Users, Shield } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'

interface Props {
  collapsed?: boolean
}

const props = withDefaults(defineProps<Props>(), { collapsed: false })

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const items = computed(() => [
  {
    to: '/admin/channels',
    icon: Tv2,
    label: '频道管理',
    show: true,
  },
  {
    to: '/admin/organizations',
    icon: Building2,
    label: '机构管理',
    show: true,
  },
  {
    to: '/admin/users',
    icon: Users,
    label: '用户管理',
    show: auth.isAdmin,
  },
  {
    to: '/admin/roles',
    icon: Shield,
    label: '角色与权限',
    show: auth.isSuperAdmin,
  },
].filter((i) => i.show))

function isActive(to: string) {
  return route.path.startsWith(to)
}
</script>

<template>
  <div :class="collapsed ? '' : 'ml-4 mt-1 space-y-0.5'">
    <button
      v-for="item in items"
      :key="item.to"
      @click="router.push(item.to)"
      class="w-full flex items-center gap-3 rounded-lg px-2.5 py-2
             text-sm transition-colors duration-150"
      :class="isActive(item.to)
        ? 'bg-zinc-800 text-white'
        : 'text-zinc-400 hover:text-white hover:bg-zinc-800/60'"
      :title="collapsed ? item.label : undefined"
    >
      <component
        :is="item.icon"
        class="shrink-0"
        style="width: 1.125rem; height: 1.125rem;"
      />
      <span v-if="!collapsed" class="font-medium">{{ item.label }}</span>
    </button>
  </div>
</template>