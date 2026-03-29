<script setup lang="ts">
/**
 * MultiviewToolbar.vue — Multiview 专属悬浮工具条
 *
 * 因为 Multiview 页面隐藏了全局 Header/Sidebar，
 * 该组件提供一个半透明、可自动隐藏的悬浮工具条。
 *
 * 使用方式：在 MultiViewLayout.vue 的根容器中直接引入，
 * 无需通过 AppLayout 传递（Multiview 自己管理自己的 UI）。
 *
 * 自动隐藏逻辑：
 *   - 鼠标移至屏幕顶部 32px 区域内时显示
 *   - 离开后延迟 2s 自动隐藏
 *   - 也可点击 Pin 按钮钉住，不再自动隐藏
 */
import { ref, onMounted, onUnmounted } from 'vue'
import {
  Plus, LayoutGrid, Captions, Share2,
  Settings, Pin, PinOff, ChevronDown
} from 'lucide-vue-next'

// ── Props & Emits ─────────────────────────────────────────────────────────────

interface Layout {
  name: string
  label: string
}

interface Props {
  layouts: Layout[]
  selectedLayout: string
  showDanmaku: boolean
  channelCount: number
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'openAddModal'): void
  (e: 'setLayout', name: string): void
  (e: 'update:showDanmaku', val: boolean): void
  (e: 'share'): void
  (e: 'openSettings'): void
}>()

// ── 可见性状态 ────────────────────────────────────────────────────────────────

const isVisible = ref<boolean>(true)
const isPinned  = ref<boolean>(false)

let hideTimer: ReturnType<typeof setTimeout> | null = null

function showToolbar(): void {
  isVisible.value = true
  if (hideTimer) { clearTimeout(hideTimer); hideTimer = null }
}

function scheduleHide(): void {
  if (isPinned.value) return
  if (hideTimer) clearTimeout(hideTimer)
  hideTimer = setTimeout(() => { isVisible.value = false }, 2000)
}

/** 监听鼠标靠近顶部 */
function handleMouseMove(e: MouseEvent): void {
  if (e.clientY < 32) {
    showToolbar()
  }
}

/** 鼠标离开工具条区域时启动倒计时 */
function onMouseLeave(): void {
  scheduleHide()
}

onMounted(() => {
  window.addEventListener('mousemove', handleMouseMove)
  // 初始 3s 后自动隐藏
  setTimeout(() => { if (!isPinned.value) isVisible.value = false }, 3000)
})

onUnmounted(() => {
  window.removeEventListener('mousemove', handleMouseMove)
  if (hideTimer) clearTimeout(hideTimer)
})
</script>

<template>
  <!--
    固定定位，顶部居中。
    pointer-events-none 包裹层：让工具条隐藏时不拦截视频区域的鼠标事件。
    工具条本身 pointer-events-auto。
  -->
  <div
    class="fixed top-0 left-0 right-0 flex justify-center z-40 pointer-events-none"
    @mousemove.stop
  >
    <!-- 靠近顶部时的感应区（不可见，仅用于触发 showToolbar）-->
    <div
      class="absolute top-0 left-0 right-0 h-8 pointer-events-auto"
      @mouseenter="showToolbar"
    />

    <!-- 工具条主体 -->
    <Transition
      enter-active-class="transition-all duration-250 ease-out"
      enter-from-class="-translate-y-full opacity-0"
      enter-to-class="translate-y-0 opacity-100"
      leave-active-class="transition-all duration-200 ease-in"
      leave-from-class="translate-y-0 opacity-100"
      leave-to-class="-translate-y-full opacity-0"
    >
      <div
        v-if="isVisible"
        class="pointer-events-auto mt-0 flex items-center gap-2 px-3 h-11
               bg-zinc-950/85 backdrop-blur-md
               border border-t-0 border-zinc-700/60
               rounded-b-xl shadow-xl shadow-black/50"
        @mouseenter="showToolbar"
        @mouseleave="onMouseLeave"
      >
        <!-- Logo 微标 -->
        <div class="flex items-center gap-2 pr-2 border-r border-zinc-700">
          <div class="w-5 h-5 rounded bg-rose-600 flex items-center justify-center shrink-0">
            <span class="text-white text-[9px] font-black">VL</span>
          </div>
          <span class="text-zinc-400 text-xs font-mono">
            {{ channelCount }} 窗
          </span>
        </div>

        <!-- 添加视频 -->
        <button
          @click="emit('openAddModal')"
          class="flex items-center gap-1.5 px-2.5 py-1 rounded-md
                 bg-rose-600/80 hover:bg-rose-500 text-white text-xs font-medium
                 transition-colors"
        >
          <Plus class="w-3.5 h-3.5" />
          <span>添加</span>
        </button>

        <div class="w-px h-5 bg-zinc-700" />

        <!-- 布局切换（仅显示 label 紧凑版）-->
        <div class="flex items-center bg-zinc-900/80 border border-zinc-700 rounded-md p-0.5 gap-0.5">
          <button
            v-for="layout in layouts"
            :key="layout.name"
            @click="emit('setLayout', layout.name)"
            class="px-2 py-0.5 rounded text-[10px] font-medium transition-colors"
            :class="selectedLayout === layout.name
              ? 'bg-zinc-700 text-white'
              : 'text-zinc-500 hover:text-zinc-300'"
          >
            {{ layout.label }}
          </button>
        </div>

        <div class="w-px h-5 bg-zinc-700" />

        <!-- 弹幕开关 -->
        <button
          @click="emit('update:showDanmaku', !showDanmaku)"
          class="p-1.5 rounded-md transition-colors"
          :class="showDanmaku
            ? 'text-rose-400 bg-rose-500/10 hover:bg-rose-500/20'
            : 'text-zinc-500 hover:text-white hover:bg-zinc-800'"
          title="弹幕"
        >
          <Captions class="w-3.5 h-3.5" />
        </button>

        <!-- 分享 -->
        <button
          @click="emit('share')"
          class="p-1.5 rounded-md text-zinc-500 hover:text-white hover:bg-zinc-800 transition-colors"
          title="分享"
        >
          <Share2 class="w-3.5 h-3.5" />
        </button>

        <!-- 设置 -->
        <button
          @click="emit('openSettings')"
          class="p-1.5 rounded-md text-zinc-500 hover:text-white hover:bg-zinc-800 transition-colors"
          title="弹幕设置"
        >
          <Settings class="w-3.5 h-3.5" />
        </button>

        <div class="w-px h-5 bg-zinc-700" />

        <!-- Pin 按钮：锁定工具条不自动隐藏 -->
        <button
          @click="isPinned = !isPinned"
          class="p-1.5 rounded-md transition-colors"
          :class="isPinned
            ? 'text-amber-400 bg-amber-500/10 hover:bg-amber-500/20'
            : 'text-zinc-500 hover:text-white hover:bg-zinc-800'"
          :title="isPinned ? '取消固定' : '固定工具条'"
        >
          <component :is="isPinned ? Pin : PinOff" class="w-3.5 h-3.5" />
        </button>

        <!-- 收起把手（手动隐藏）-->
        <button
          @click="isVisible = false"
          class="p-1.5 rounded-md text-zinc-600 hover:text-white hover:bg-zinc-800 transition-colors"
          title="隐藏工具条"
        >
          <ChevronDown class="w-3.5 h-3.5" />
        </button>
      </div>
    </Transition>
  </div>
</template>