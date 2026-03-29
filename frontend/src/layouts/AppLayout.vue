<script setup lang="ts">
/**
 * AppLayout.vue — 顶层布局编排组件
 *
 * 核心策略：
 * - Multiview 路由：整个 viewport 交给 <router-view>，Header/Sidebar 完全不渲染
 * - 普通路由：渲染 GlobalHeader + NavigationSidebar + 内容区
 *
 * 溢出处理原则：
 *   根容器 h-screen overflow-hidden → 子容器用 flex-1 min-h-0 → 滚动只发生在 <main>
 *   "min-h-0" 是关键！Flex 子项默认 min-height: auto 会撑破父容器，必须显式设为 0。
 */
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import GlobalHeader from '../components/GlobalHeader.vue'
import NavigationSidebar from '../components/NavigationSidebar.vue'

// ── 侧边栏折叠状态（持久化到 localStorage）──────────────────────────────────
const isSidebarCollapsed = ref<boolean>(
  localStorage.getItem('sidebarCollapsed') === 'true'
)

function toggleSidebar(): void {
  isSidebarCollapsed.value = !isSidebarCollapsed.value
  localStorage.setItem('sidebarCollapsed', String(isSidebarCollapsed.value))
}

// ── 路由检测：是否为 Multiview 页面 ──────────────────────────────────────────
const route = useRoute()

/** Multiview 路由名称列表，增加路由时在此扩展 */
const MULTIVIEW_ROUTE_NAMES = new Set(['MultiView'])

const isMultiviewRoute = computed<boolean>(
  () => MULTIVIEW_ROUTE_NAMES.has(route.name as string)
)
</script>

<template>
  <!--
    根容器：h-screen + overflow-hidden
    这是解决全局滚动条的第一道防线。
    任何子组件产生的溢出都在此被截断，滚动只允许发生在明确指定 overflow-y-auto 的容器内。
  -->
  <div class="h-screen w-screen overflow-hidden bg-zinc-950 text-white flex flex-col">

    <!-- ══ MULTIVIEW 模式：仅渲染路由视图，零 Chrome ══ -->
    <template v-if="isMultiviewRoute">
      <!--
        flex-1 min-h-0：让 router-view 容器撑满剩余高度但不超出父容器。
        Multiview 内部的 VideoGrid 会用 h-full 填满此容器。
      -->
      <div class="flex-1 min-h-0 relative">
        <router-view />
      </div>
    </template>

    <!-- ══ 普通页面模式：Header + Sidebar + 内容区 ══ -->
    <template v-else>

      <!-- ── GlobalHeader（固定顶部，不参与 flex 伸缩）── -->
      <GlobalHeader
        :is-sidebar-collapsed="isSidebarCollapsed"
        @toggle-sidebar="toggleSidebar"
      />

      <!-- ── 下半部分：Sidebar + 主内容，水平排布 ── -->
      <!--
        flex-1 min-h-0：占满 Header 以下空间，且高度不超出屏幕。
        overflow-hidden：阻止 sidebar 或主内容的水平/垂直溢出冒泡到根容器。
      -->
      <div class="flex flex-1 min-h-0 overflow-hidden">

        <!-- ── NavigationSidebar ── -->
        <NavigationSidebar :is-collapsed="isSidebarCollapsed" />

        <!-- ── 主内容区 ── -->
        <!--
          flex-1 min-w-0：水平方向撑满剩余空间，min-w-0 防止内容撑宽。
          overflow-y-auto：只有这里允许垂直滚动，其余容器全部 overflow-hidden。
        -->
        <main class="flex-1 min-w-0 overflow-y-auto bg-zinc-900">
          <router-view />
        </main>

      </div>
    </template>

  </div>
</template>