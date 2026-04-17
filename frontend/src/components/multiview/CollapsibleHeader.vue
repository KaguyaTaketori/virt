<script setup lang="ts">
import { 
  Menu, ChevronUp, ChevronDown, Share2, 
  Captions, Settings, RefreshCw 
} from 'lucide-vue-next'
import type { Stream } from '@/api'
import type { LayoutChannel } from '@/types/multiview'
import type { PresetId } from '@/utils/presetLayouts'

// 导入拆分的子组件
import ToolbarGroupSelect from './header/ToolbarGroupSelect.vue'
import ToolbarMemberList from './header/ToolbarMemberList.vue'
import ToolbarPresetMenu from './header/ToolbarPresetMenu.vue'

// 定义类型
export type GroupType = 'favorites' | number

interface Props {
  isCollapsed: boolean
  channels: LayoutChannel[]
  showDanmaku: boolean
  selectedGroup: GroupType | null
  organizationName: string | null
  groupMembers: Stream[]
  isRefreshing: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'toggleDrawer'): void
  (e: 'toggleCollapse'): void
  (e: 'openAddModal'): void
  (e: 'removeChannelByPlatformId', platform: string, id: string): void
  (e: 'applyPreset', type: PresetId): void
  (e: 'openPresetLibrary'): void 
  (e: 'openSettings'): void
  (e: 'share'): void
  (e: 'update:showDanmaku', val: boolean): void
  (e: 'selectGroup', group: GroupType): void
  (e: 'clearGroup'): void
  (e: 'refresh'): void
  (e: 'addMember', member: Stream): void
  (e: 'openGroupSelector'): void
}>()
</script>

<template>
  <div class="relative w-full select-none">
    <!-- 顶部感应区：点击可快速切换折叠状态 -->
    <div 
      class="absolute top-0 left-0 right-0 h-1.5 z-50 cursor-pointer hover:bg-rose-500/20 transition-colors" 
      @click="emit('toggleCollapse')" 
    />

    <!-- 1. 展开状态的工具栏 -->
    <Transition name="slide-down">
      <header 
        v-if="!isCollapsed" 
        class="flex items-center gap-2 px-3 h-14 bg-zinc-950/95 backdrop-blur-md border-b border-zinc-800 z-40 overflow-hidden"
      >
        <!-- 基础导航操作 -->
        <div class="flex items-center shrink-0">
          <button @click="emit('toggleDrawer')" class="icon-btn" title="打开侧边栏">
            <Menu class="w-4 h-4" />
          </button>
          <div class="w-px h-5 bg-zinc-800 mx-1.5" />
        </div>

        <!-- 子组件 A: 分组选择 -->
        <ToolbarGroupSelect 
          :selected-group="selectedGroup"
          :organization-name="organizationName"
          :members-count="groupMembers.length"
          @select="g => emit('selectGroup', g)"
          @open-selector="emit('openGroupSelector')"
        />

        <!-- 刷新按钮 -->
        <button
          @click="emit('refresh')"
          class="shrink-0 p-2 rounded-md text-zinc-500 hover:text-white hover:bg-zinc-800 transition-all active:scale-90"
          :class="{ 'animate-spin text-rose-500': isRefreshing }"
          :disabled="isRefreshing"
          title="刷新成员状态"
        >
          <RefreshCw class="w-4 h-4" />
        </button>

        <!-- 子组件 B: 正在直播的成员头像列表 (占据中间剩余空间) -->
        <ToolbarMemberList 
          :members="groupMembers"
          :has-selected-group="!!selectedGroup"
          @add="m => emit('addMember', m)"
          @open-add-modal="emit('openAddModal')"
        />

        <!-- 右侧工具组 -->
        <div class="flex items-center gap-1 shrink-0 ml-auto">
          <!-- 子组件 C: 布局预设菜单 -->
          <ToolbarPresetMenu 
            :channel-count="channels.length"
            @apply="p => emit('applyPreset', p)"
            @open-library="emit('openPresetLibrary')"
          />

          <div class="w-px h-5 bg-zinc-800 mx-1" />

          <!-- 功能开关 -->
          <button 
            @click="emit('update:showDanmaku', !showDanmaku)" 
            class="icon-btn" 
            :class="{ 'text-rose-500 bg-rose-500/10': showDanmaku }"
            title="显示/隐藏弹幕"
          >
            <Captions class="w-4 h-4" />
          </button>

          <button @click="emit('share')" class="icon-btn" title="分享配置">
            <Share2 class="w-4 h-4" />
          </button>

          <button @click="emit('openSettings')" class="icon-btn" title="播放器设置">
            <Settings class="w-4 h-4" />
          </button>

          <div class="w-px h-5 bg-zinc-800 mx-1" />

          <!-- 收起按钮 -->
          <button @click="emit('toggleCollapse')" class="icon-btn hover:text-rose-500" title="收起工具栏">
            <ChevronUp class="w-4 h-4" />
          </button>
        </div>
      </header>
    </Transition>

    <!-- 2. 已收起状态的迷你工具栏 (悬浮感) -->
    <Transition name="fade">
      <div
        v-if="isCollapsed"
        class="absolute top-0 left-0 right-0 h-10 z-30 flex items-center justify-between px-4 bg-gradient-to-b from-zinc-950/80 to-transparent pointer-events-none"
      >
        <div class="flex items-center gap-1 pointer-events-auto">
          <button
            @click="emit('toggleDrawer')"
            class="p-2 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-900/80 backdrop-blur-sm transition-all"
          >
            <Menu class="w-4 h-4" />
          </button>
          <button
            @click="emit('update:showDanmaku', !showDanmaku)"
            class="p-2 rounded-lg transition-all backdrop-blur-sm"
            :class="showDanmaku ? 'text-rose-500 bg-rose-500/10' : 'text-zinc-400 hover:text-white hover:bg-zinc-900/80'"
          >
            <Captions class="w-4 h-4" />
          </button>
        </div>

        <button
          @click="emit('toggleCollapse')"
          class="pointer-events-auto flex items-center gap-1.5 px-4 py-1 rounded-full bg-zinc-900/90 hover:bg-zinc-800 text-zinc-400 hover:text-zinc-100 text-[11px] font-bold border border-zinc-800 transition-all shadow-xl backdrop-blur-md"
        >
          <span>展开工具栏</span>
          <ChevronDown class="w-3.5 h-3.5" />
        </button>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
/* 统一样式类 */
.icon-btn {
  @apply p-2 rounded-md text-zinc-400 hover:text-white hover:bg-zinc-800 transition-all duration-200 active:scale-90;
}

/* 动画：工具栏下拉 */
.slide-down-enter-active, 
.slide-down-leave-active { 
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1); 
}
.slide-down-enter-from, 
.slide-down-leave-to { 
  transform: translateY(-100%); 
  opacity: 0; 
}

/* 动画：渐显 */
.fade-enter-active, 
.fade-leave-active { 
  transition: opacity 0.3s ease; 
}
.fade-enter-from, 
.fade-leave-to { 
  opacity: 0; 
}

/* 隐藏滚动条 */
.scrollbar-none::-webkit-scrollbar {
  display: none;
}
</style>