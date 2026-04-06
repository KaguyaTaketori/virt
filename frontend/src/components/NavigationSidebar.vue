<script setup lang="ts">
/**
 * frontend/src/components/NavigationSidebar.vue（精简版）
 *
 * 问题 4 修复：引入已有但未使用的 useBilibiliGuard，删除散落的重复过滤
 * 问题 5 修复：使用 AdminSubMenu 组件替换重复的管理子菜单
 */
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Home, Heart, Tv2, ListVideo,
  LayoutGrid, Music, HelpCircle, Settings,
  SlidersHorizontal, ChevronDown, ChevronUp,
} from 'lucide-vue-next'
import AdminSubMenu from '@/components/AdminSubMenu.vue'
import { useAuthStore } from '@/stores/auth'

interface Props {
  isCollapsed: boolean
}

const props = defineProps<Props>()
const route = useRoute()
const router = useRouter()
const showAdminMenu = ref(false)
const authStore = useAuthStore()

const navItems = [
  { label: '主页',     icon: Home,      to: '/' },
  { label: '收藏',     icon: Heart,     to: '/favorites' },
  { label: '频道',     icon: Tv2,       to: '/channels' },
  { label: '播放列表', icon: ListVideo, to: '/playlists' },
  { label: '多窗播放', icon: LayoutGrid, to: '/multiview' },
  { label: 'Musicdex', icon: Music,      to: '/musicdex' },
  { label: '帮助',     icon: HelpCircle, to: '/help' },
]

function isActive(to: string) {
  return to === '/' ? route.path === '/' : route.path.startsWith(to)
}

const labelClass = computed(() =>
  props.isCollapsed
    ? 'opacity-0 w-0 overflow-hidden whitespace-nowrap'
    : 'opacity-100 w-auto'
)
</script>

<template>
  <nav
    class="shrink-0 overflow-hidden flex flex-col bg-zinc-950 border-r border-zinc-800
           transition-all duration-300 ease-in-out"
    :class="isCollapsed ? 'w-14' : 'w-52'"
  >
    <div class="flex-1 overflow-y-auto overflow-x-hidden py-3 space-y-0.5 px-2">

      <template v-for="(item, idx) in navItems" :key="item.to">
        <!-- 分隔线：多窗播放前、帮助前 -->
        <div v-if="idx === 4 || idx === 6" class="my-2 border-t border-zinc-800" />

        <button
          @click="router.push(item.to)"
          class="w-full flex items-center gap-3 rounded-lg px-2.5 py-2.5
                 text-sm transition-colors duration-150 relative group"
          :class="isActive(item.to)
            ? 'bg-zinc-800 text-white'
            : 'text-zinc-400 hover:text-white hover:bg-zinc-800/60'"
          :title="isCollapsed ? item.label : undefined"
        >
          <component :is="item.icon" style="width:1.125rem;height:1.125rem" class="shrink-0"
            :class="isActive(item.to) ? 'text-rose-400' : ''" />
          <span class="font-medium leading-none transition-all duration-300" :class="labelClass">
            {{ item.label }}
          </span>
          <!-- 折叠时的 tooltip -->
          <span v-if="isCollapsed"
            class="absolute left-full ml-2.5 px-2.5 py-1.5 rounded-md bg-zinc-800
                   border border-zinc-700 text-white text-xs whitespace-nowrap
                   pointer-events-none z-50 opacity-0 group-hover:opacity-100
                   translate-x-1 group-hover:translate-x-0 transition-all duration-150
                   shadow-lg shadow-black/40">
            {{ item.label }}
          </span>
        </button>
      </template>

      <!-- 管理菜单 -->
      <div class="my-2 border-t border-zinc-800" />
      <button
        @click="showAdminMenu = !showAdminMenu"
        class="w-full flex items-center gap-3 rounded-lg px-2.5 py-2.5
               text-sm transition-colors text-zinc-400 hover:text-white hover:bg-zinc-800/60"
      >
        <Settings style="width:1.125rem;height:1.125rem" class="shrink-0" />
        <span class="font-medium flex-1 leading-none" :class="labelClass">管理</span>
        <template v-if="!isCollapsed">
          <ChevronUp v-if="showAdminMenu" class="w-3 h-3 opacity-50" />
          <ChevronDown v-else class="w-3 h-3 opacity-50" />
        </template>
      </button>

      <!-- ↓ 问题 5 修复：使用独立组件，删除重复的 hardcoded 子菜单 -->
      <AdminSubMenu v-if="showAdminMenu && !isCollapsed" />

    </div>

    <!-- 底部设置按钮 -->
    <div class="shrink-0 border-t border-zinc-800 py-3 px-2 space-y-0.5">
      <button
        v-if="authStore.canAccessBilibili"
        @click="router.push('/settings')"
        class="w-full flex items-center gap-3 rounded-lg px-2.5 py-2.5
               text-zinc-500 hover:text-white hover:bg-zinc-800/60 transition-colors text-sm group relative"
      >
        <Settings style="width:1.125rem;height:1.125rem" class="shrink-0" />
        <span class="font-medium leading-none transition-all duration-300" :class="labelClass">设置</span>
      </button>
      <button
        class="w-full flex items-center gap-3 rounded-lg px-2.5 py-2.5
               text-zinc-500 hover:text-white hover:bg-zinc-800/60 transition-colors text-sm group relative"
      >
        <SlidersHorizontal style="width:1.125rem;height:1.125rem" class="shrink-0" />
        <span class="font-medium leading-none transition-all duration-300" :class="labelClass">偏好设置</span>
      </button>
    </div>
  </nav>
</template>