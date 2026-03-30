<script setup lang="ts">
import {
  Menu, Plus, X, ChevronUp, ChevronDown,
  Share2, Captions, Settings
} from 'lucide-vue-next'

interface Channel {
  platform: 'youtube' | 'bilibili'
  id: string
}

interface Layout {
  name: string
  label: string
  cols: number
  cells: number
}

interface Props {
  isCollapsed: boolean
  channels: Channel[]
  selectedLayout: string
  layouts: Layout[]
  showDanmaku: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'toggleDrawer'): void
  (e: 'toggleCollapse'): void
  (e: 'openAddModal'): void
  (e: 'removeChannel', idx: number): void
  (e: 'setLayout', name: string): void
  (e: 'openSettings'): void
  (e: 'share'): void
  (e: 'update:showDanmaku', val: boolean): void
}>()

function platformLabel(p: string) {
  return p === 'youtube' ? 'YT' : 'B'
}

function platformColor(p: string) {
  return p === 'youtube'
    ? 'bg-red-500/20 text-red-400 border-red-500/30'
    : 'bg-blue-500/20 text-blue-400 border-blue-500/30'
}

function toggleDanmaku() {
  emit('update:showDanmaku', !props.showDanmaku)
}
</script>

<template>
  <div class="relative">
    <!-- ─── Transparent Pull Handle (always visible) ─── -->
    <div
      class="absolute top-0 left-0 right-0 h-3 z-40 cursor-pointer"
      @click="emit('toggleCollapse')"
      title="展开工具栏"
    />

    <!-- ─── Main Header Bar ─── -->
    <Transition
      enter-active-class="transition-all duration-300 ease-out"
      enter-from-class="-translate-y-full opacity-0"
      enter-to-class="translate-y-0 opacity-100"
      leave-active-class="transition-all duration-200 ease-in"
      leave-from-class="translate-y-0 opacity-100"
      leave-to-class="-translate-y-full opacity-0"
    >
      <header
        v-if="!isCollapsed"
        class="flex items-center gap-2 px-3 h-12 bg-zinc-950/95 backdrop-blur-md
               border-b border-zinc-800 z-30"
      >
        <!-- Left: Hamburger -->
        <button
          @click="emit('toggleDrawer')"
          class="icon-btn"
          title="菜单"
        >
          <Menu class="w-4 h-4" />
        </button>

        <div class="w-px h-5 bg-zinc-700 mx-1" />

        <!-- Add Button -->
        <button
          @click="emit('openAddModal')"
          class="flex items-center gap-1.5 px-3 py-1.5 rounded-md
                 bg-rose-600 hover:bg-rose-500 text-white text-xs font-medium
                 transition-colors shrink-0"
        >
          <Plus class="w-3.5 h-3.5" />
          <span>添加</span>
        </button>

        <!-- Channel Pills -->
        <div class="flex items-center gap-1.5 overflow-x-auto scrollbar-none flex-1 mx-1">
          <TransitionGroup
            enter-active-class="transition-all duration-200"
            enter-from-class="opacity-0 scale-75"
            enter-to-class="opacity-100 scale-100"
            leave-active-class="transition-all duration-150"
            leave-from-class="opacity-100 scale-100"
            leave-to-class="opacity-0 scale-75"
          >
            <span
              v-for="(ch, idx) in channels"
              :key="ch.id"
              class="inline-flex items-center gap-1 pl-2 pr-1 py-0.5 rounded-md
                     border text-xs font-mono shrink-0"
              :class="platformColor(ch.platform)"
            >
              <span class="text-[10px] font-bold">{{ platformLabel(ch.platform) }}</span>
              <span class="max-w-[60px] truncate text-[11px]">{{ ch.id }}</span>
              <button
                @click="emit('removeChannel', idx)"
                class="ml-0.5 opacity-50 hover:opacity-100 transition-opacity rounded-sm
                       hover:bg-white/10 p-0.5"
              >
                <X class="w-2.5 h-2.5" />
              </button>
            </span>
          </TransitionGroup>
        </div>

        <!-- Right Controls -->
        <div class="flex items-center gap-0.5 shrink-0">
          <!-- Layout Switcher -->
          <div class="flex items-center bg-zinc-900 border border-zinc-700 rounded-md p-0.5 gap-0.5">
            <button
              v-for="layout in layouts"
              :key="layout.name"
              @click="emit('setLayout', layout.name)"
              class="px-2 py-1 rounded text-[10px] font-medium transition-colors"
              :class="selectedLayout === layout.name
                ? 'bg-zinc-700 text-white'
                : 'text-zinc-500 hover:text-zinc-300'"
            >
              {{ layout.label }}
            </button>
          </div>

          <div class="w-px h-5 bg-zinc-700 mx-1" />

          <!-- Danmaku Toggle -->
          <button
            @click="toggleDanmaku"
            class="icon-btn"
            :class="showDanmaku ? 'bg-rose-500/20 text-rose-400' : ''"
            title="弹幕"
          >
            <Captions class="w-4 h-4" />
          </button>

          <!-- Share -->
          <button @click="emit('share')" class="icon-btn" title="分享">
            <Share2 class="w-4 h-4" />
          </button>

          <!-- Settings -->
          <button @click="emit('openSettings')" class="icon-btn" title="弹幕设置">
            <Settings class="w-4 h-4" />
          </button>

          <div class="w-px h-5 bg-zinc-700 mx-1" />

          <!-- Collapse -->
          <button
            @click="emit('toggleCollapse')"
            class="icon-btn"
            title="折叠工具栏"
          >
            <ChevronUp class="w-4 h-4" />
          </button>
        </div>
      </header>
    </Transition>

    <!-- ─── Collapsed Indicator (visible when collapsed) ─── -->
    <Transition
      enter-active-class="transition-all duration-300 ease-out"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition-all duration-150 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="isCollapsed"
        class="absolute top-0 left-0 right-0 h-10 z-30 flex items-center justify-between px-2"
      >
        <div class="flex items-center gap-1">
          <button
            @click="emit('toggleDrawer')"
            class="p-2 rounded-md text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors"
            title="菜单"
          >
            <Menu class="w-4 h-4" />
          </button>
          <button
            @click="emit('update:showDanmaku', !showDanmaku)"
            class="p-2 rounded-md transition-colors"
            :class="showDanmaku ? 'text-rose-400' : 'text-zinc-400 hover:text-white hover:bg-zinc-800'"
            title="弹幕"
          >
            <Captions class="w-4 h-4" />
          </button>
        </div>
        <button
          @click="emit('toggleCollapse')"
          class="flex items-center gap-1 px-3 py-1 rounded-full bg-zinc-800/80 hover:bg-zinc-700 text-zinc-400 hover:text-white text-xs transition-colors"
        >
          <span>工具栏</span>
          <ChevronDown class="w-3 h-3" />
        </button>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.icon-btn {
  @apply p-2 rounded-md text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors;
}
.scrollbar-none::-webkit-scrollbar {
  display: none;
}
</style>