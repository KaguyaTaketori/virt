<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Home, Heart, Tv2, ListVideo,
  LayoutGrid, Music, HelpCircle, Settings,
  SlidersHorizontal, ChevronDown, ChevronUp,
  ShieldCheck
} from 'lucide-vue-next'
import AdminSubMenu from '@/components/AdminSubMenu.vue'
import { useAuthStore } from '@/stores/auth'

interface Props {
  isCollapsed: boolean
}

const props = defineProps<Props>()
const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const showAdminMenu = ref(false)

// 1. 结构化导航数据，方便维护和自动生成分割线
const navSections = [
  {
    items: [
      { label: '主页', icon: Home, to: '/' },
      { label: '收藏', icon: Heart, to: '/favorites' },
      { label: '频道', icon: Tv2, to: '/channels' },
      { label: '播放列表', icon: ListVideo, to: '/playlists' },
    ]
  },
  {
    items: [
      { label: '多窗播放', icon: LayoutGrid, to: '/multiview' },
      { label: 'Musicdex', icon: Music, to: '/musicdex' },
    ]
  },
  {
    items: [
      { label: '帮助', icon: HelpCircle, to: '/help' },
    ]
  }
]

function isActive(to: string) {
  return to === '/' ? route.path === '/' : route.path.startsWith(to)
}

// 2. 优化折叠文字动画逻辑
// 使用 scale-0 而非 width-0 可以避免文字换行导致的跳动
const labelClass = computed(() =>
  props.isCollapsed
    ? 'opacity-0 translate-x-[-10px] pointer-events-none'
    : 'opacity-100 translate-x-0'
)
</script>

<template>
  <nav
    class="shrink-0 flex flex-col bg-zinc-950 border-r border-zinc-900/50 
           transition-all duration-300 ease-in-out relative z-20"
    :class="isCollapsed ? 'w-16' : 'w-56'"
  >
    <!-- 内容区 -->
    <div class="flex-1 overflow-y-auto overflow-x-hidden custom-scrollbar py-4 px-3">
      
      <div v-for="(section, sIdx) in navSections" :key="sIdx">
        <!-- 分割线 -->
        <div v-if="sIdx !== 0" class="my-3 mx-2 border-t border-zinc-900/50" />
        
        <div class="space-y-1">
          <button
            v-for="item in section.items"
            :key="item.to"
            @click="router.push(item.to)"
            class="w-full flex items-center gap-3 rounded-xl px-3 py-2.5
                   text-sm transition-all duration-200 relative group overflow-visible"
            :class="isActive(item.to)
              ? 'bg-zinc-900 text-white shadow-sm'
              : 'text-zinc-500 hover:text-zinc-200 hover:bg-zinc-900/50'"
          >
            <!-- 激活状态指示条 -->
            <div 
              v-if="isActive(item.to)"
              class="absolute left-0 w-1 h-5 bg-rose-500 rounded-r-full"
            />

            <component 
              :is="item.icon" 
              class="w-5 h-5 shrink-0 transition-transform duration-200 group-active:scale-90"
              :class="isActive(item.to) ? 'text-rose-500' : 'group-hover:text-zinc-200'"
            />
            
            <span 
              class="font-medium whitespace-nowrap transition-all duration-300 origin-left"
              :class="labelClass"
            >
              {{ item.label }}
            </span>

            <!-- 折叠模式下的浮动 Tooltip (毛玻璃质感) -->
            <div v-if="isCollapsed"
              class="absolute left-full ml-4 px-3 py-2 rounded-lg bg-zinc-900/90 
                     backdrop-blur-md border border-zinc-800 text-white text-xs 
                     whitespace-nowrap pointer-events-none z-50 opacity-0 
                     translate-x-[-10px] group-hover:opacity-100 group-hover:translate-x-0 
                     transition-all duration-200 shadow-xl shadow-black/40 font-bold"
            >
              {{ item.label }}
            </div>
          </button>
        </div>
      </div>

      <!-- 管理菜单部分 -->
      <div class="my-3 mx-2 border-t border-zinc-900/50" />
      <div class="space-y-1">
        <button
          @click="showAdminMenu = !showAdminMenu"
          class="w-full flex items-center gap-3 rounded-xl px-3 py-2.5
                 text-sm transition-all duration-200 text-zinc-500 hover:text-zinc-200 hover:bg-zinc-900/50"
        >
          <ShieldCheck class="w-5 h-5 shrink-0" :class="showAdminMenu ? 'text-blue-400' : ''" />
          <span class="font-medium flex-1 text-left whitespace-nowrap origin-left transition-all duration-300" :class="labelClass">
            系统管理
          </span>
          <template v-if="!isCollapsed">
            <ChevronUp v-if="showAdminMenu" class="w-4 h-4 opacity-40" />
            <ChevronDown v-else class="w-4 h-4 opacity-40" />
          </template>
        </button>

        <!-- 子菜单过渡动画 -->
        <transition name="menu-slide">
          <div v-if="showAdminMenu && !isCollapsed" class="overflow-hidden">
            <AdminSubMenu />
          </div>
        </transition>
      </div>
    </div>

    <!-- 底部功能按钮 -->
    <div class="shrink-0 border-t border-zinc-900/50 p-3 space-y-1 bg-zinc-950/50 backdrop-blur-sm">
      <button
        v-if="authStore.canAccessBilibili"
        @click="router.push('/settings')"
        class="w-full flex items-center gap-3 rounded-xl px-3 py-2.5
               text-zinc-500 hover:text-rose-400 hover:bg-rose-500/5 transition-all text-sm group relative"
      >
        <Settings class="w-5 h-5 shrink-0" />
        <span class="font-medium whitespace-nowrap origin-left transition-all duration-300" :class="labelClass">全局设置</span>
      </button>

      <button
        class="w-full flex items-center gap-3 rounded-xl px-3 py-2.5
               text-zinc-500 hover:text-zinc-200 hover:bg-zinc-900/50 transition-all text-sm group relative"
      >
        <SlidersHorizontal class="w-5 h-5 shrink-0" />
        <span class="font-medium whitespace-nowrap origin-left transition-all duration-300" :class="labelClass">界面偏好</span>
      </button>
    </div>
  </nav>
</template>

<style scoped>
/* 1. 子菜单滑动动画 */
.menu-slide-enter-active,
.menu-slide-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  max-height: 300px;
}

.menu-slide-enter-from,
.menu-slide-leave-to {
  opacity: 0;
  max-height: 0;
  transform: translateY(-10px);
}

/* 2. 隐藏滚动条但保留功能 */
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: transparent;
  border-radius: 4px;
}
.custom-scrollbar:hover::-webkit-scrollbar-thumb {
  background: #27272a; /* zinc-800 */
}

/* 3. 辅助类：文字强制不换行，防止折叠过程中布局崩坏 */
span {
  display: inline-block;
}
</style>