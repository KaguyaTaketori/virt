<script setup lang="ts">
import { computed, provide, useTemplateRef } from 'vue'
import { useRoute } from 'vue-router'
import { useStorage, useToggle } from '@vueuse/core'
import GlobalHeader from '@/components/GlobalHeader.vue'
import NavigationSidebar from '@/components/NavigationSidebar.vue'

// 1. 状态管理
const isSidebarCollapsed = useStorage('sidebar-collapsed', false)
const toggleSidebar = useToggle(isSidebarCollapsed)

const route = useRoute()

// 2. 全屏模式逻辑
const isFullscreen = computed<boolean>(
  () => route.meta.fullscreen === true
)

// 3. 注入滚动容器引用
// 这样子组件（如 BilibiliFeed）可以通过 inject('mainScrollRef') 实现无限滚动
const mainScrollRef = useTemplateRef<HTMLElement>('mainScrollRef')
provide('mainScrollRef', mainScrollRef)
</script>

<template>
  <div class="h-screen w-screen overflow-hidden bg-zinc-950 text-zinc-100 flex flex-col font-sans antialiased">
    
    <!-- 全屏模式：如多窗预览、大屏播放器 -->
    <template v-if="isFullscreen">
      <main class="flex-1 min-h-0 relative bg-black">
        <router-view v-slot="{ Component }">
          <transition name="page-fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </template>

    <!-- 标准模式：带导航和标题栏 -->
    <template v-else>
      <GlobalHeader
        :is-sidebar-collapsed="isSidebarCollapsed"
        @toggle-sidebar="toggleSidebar"
        class="z-30 border-b border-zinc-800/50"
      />
      
      <div class="flex flex-1 min-h-0 overflow-hidden relative">
        <!-- 侧边栏：宽度由内部组件控制，此处保持 flex 布局 -->
        <NavigationSidebar 
          :is-collapsed="isSidebarCollapsed" 
          class="z-20 transition-all duration-300 ease-in-out border-r border-zinc-800/30"
        />
        
        <!-- 主内容区 -->
        <main 
          ref="mainScrollRef" 
          class="flex-1 min-w-0 overflow-y-auto bg-zinc-900/50 custom-scrollbar relative"
        >
          <!-- 页面切换动画 -->
          <router-view v-slot="{ Component }">
            <transition name="page-slide" mode="out-in">
              <component :is="Component" :key="route.fullPath" />
            </transition>
          </router-view>
        </main>
      </div>
    </template>
  </div>
</template>

<style>
/* 1. 全局滚动条美化 (针对 zinc-900 风格) */
.custom-scrollbar::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #3f3f46; /* zinc-700 */
  border-radius: 10px;
  border: 2px solid transparent;
  background-clip: content-box;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: #52525b; /* zinc-600 */
  border: 2px solid transparent;
  background-clip: content-box;
}

/* 2. 页面过渡动画：平滑滑动淡入 */
.page-slide-enter-active,
.page-slide-leave-active {
  transition: all 0.25s ease-out;
}

.page-slide-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.page-slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* 3. 纯淡入动画 */
.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity 0.3s ease;
}
.page-fade-enter-from,
.page-fade-leave-to {
  opacity: 0;
}

/* 4. 强制隐藏原生滚动条的基础配置 */
html, body {
  margin: 0;
  padding: 0;
  overflow: hidden;
  background-color: #09090b; /* zinc-950 */
}
</style>