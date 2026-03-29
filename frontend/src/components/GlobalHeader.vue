<script setup lang="ts">
/**
 * GlobalHeader.vue — 顶部全局导航栏
 * 仅在非 Multiview 路由下渲染（由 AppLayout 控制）。
 */
import { ref } from 'vue'
import { Menu, Search, SlidersHorizontal, Bell, ChevronDown } from 'lucide-vue-next'

interface Props {
  /** 当前侧边栏是否处于收缩状态 */
  isSidebarCollapsed: boolean
}

defineProps<Props>()

const emit = defineEmits<{
  /** 通知父组件切换侧边栏展开/折叠 */
  (e: 'toggleSidebar'): void
}>()

const searchQuery = ref<string>('')
</script>

<template>
  <!--
    h-14 shrink-0：固定高度，禁止被 flex 压缩。
    z-20：确保在 Sidebar 和内容区之上。
  -->
  <header
    class="h-14 shrink-0 flex items-center gap-3 px-4
           bg-zinc-950 border-b border-zinc-800 z-20"
  >
    <!-- 左侧：汉堡菜单 + Logo -->
    <div class="flex items-center gap-3 shrink-0">
      <!-- 侧边栏开关 -->
      <button
        @click="emit('toggleSidebar')"
        class="p-2 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800
               transition-colors"
        :title="isSidebarCollapsed ? '展开导航' : '收起导航'"
      >
        <Menu class="w-5 h-5" />
      </button>

      <!-- Logo -->
      <router-link to="/" class="flex items-center gap-2 group">
        <div
          class="w-7 h-7 rounded-md bg-rose-600 flex items-center justify-center
                 group-hover:bg-rose-500 transition-colors shrink-0"
        >
          <span class="text-white text-[11px] font-black tracking-tighter">VL</span>
        </div>
        <span class="text-white font-semibold text-sm hidden sm:block">VTuber Live</span>
      </router-link>
    </div>

    <!-- 中间：搜索框 -->
    <div class="flex-1 max-w-xl mx-auto flex items-center gap-2">
      <div class="relative flex-1">
        <Search
          class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500
                 pointer-events-none"
        />
        <input
          v-model="searchQuery"
          type="text"
          placeholder="搜索"
          class="w-full bg-zinc-800 border border-zinc-700 rounded-lg
                 pl-9 pr-4 py-2 text-sm text-white placeholder-zinc-500
                 outline-none focus:border-zinc-500 focus:ring-1 focus:ring-zinc-500/30
                 transition-colors"
        />
      </div>
      <!-- 筛选按钮 -->
      <button
        class="p-2 rounded-lg bg-zinc-800 border border-zinc-700 text-zinc-400
               hover:text-white hover:border-zinc-600 transition-colors shrink-0"
        title="筛选"
      >
        <SlidersHorizontal class="w-4 h-4" />
      </button>
    </div>

    <!-- 右侧：通知 + 用户头像 -->
    <div class="flex items-center gap-2 shrink-0">
      <button
        class="p-2 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800
               transition-colors relative"
        title="通知"
      >
        <Bell class="w-5 h-5" />
      </button>

      <!-- 用户头像占位 -->
      <button
        class="flex items-center gap-1.5 px-2 py-1.5 rounded-lg
               hover:bg-zinc-800 transition-colors"
      >
        <div
          class="w-7 h-7 rounded-full bg-gradient-to-br from-rose-500 to-violet-600
                 flex items-center justify-center text-xs font-bold text-white shrink-0"
        >
          U
        </div>
        <ChevronDown class="w-3.5 h-3.5 text-zinc-400" />
      </button>
    </div>
  </header>
</template>