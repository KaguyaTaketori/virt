<script setup lang="ts">
import { computed } from 'vue'
import { 
  Menu, Plus, X, ChevronUp, ChevronDown, 
  Share2, Captions, Settings, LayoutTemplate, Maximize2 
} from 'lucide-vue-next'
import { NPopover } from 'naive-ui'
import { Channel } from '@/utils/layoutEngine'

interface Props {
  isCollapsed: boolean
  channels: Channel[]
  showDanmaku: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'toggleDrawer'): void
  (e: 'toggleCollapse'): void
  (e: 'openAddModal'): void
  (e: 'removeChannelByPlatformId', platform: string, id: string): void
  (e: 'applyPreset', type: string): void
  (e: 'openPresetLibrary'): void // 打开全量预设 Modal
  (e: 'openSettings'): void
  (e: 'share'): void
  (e: 'update:showDanmaku', val: boolean): void
}>()

// --- 预设元数据定义 (用于图标展示) ---
const PRESET_META: Record<string, { label: string; icon: string }> = {
  '1-s': { label: '单窗口', icon: '1' },
  '2-h': { label: '左右对半', icon: '2h' },
  '2-v': { label: '上下对半', icon: '2v' },
  '3-1+2': { label: '1大🎞️ + 2小', icon: '3-12' },
  '3-cols': { label: '三列并行', icon: '3c' },
  '4-grid': { label: '2 × 2 田字格', icon: '4g' },
  '4-1+3': { label: '1大🎞️ + 3小', icon: '4-13' }
}

// 根据当前视频数量推荐预设
const currentRecommendations = computed(() => {
  const count = props.channels.length
  let ids: string[] = []
  
  if (count <= 1) ids = ['1-s']
  else if (count === 2) ids = ['2-h', '2-v']
  else if (count === 3) ids = ['3-1+2', '3-cols']
  else ids = ['4-grid', '4-1+3']

  return ids.map(id => ({ id, ...PRESET_META[id] }))
})
</script>


<template>
  <div class="relative">
    <!-- 展开手柄 -->
    <div class="absolute top-0 left-0 right-0 h-3 z-40 cursor-pointer" @click="emit('toggleCollapse')" />

    <Transition name="slide-down">
      <header v-if="!isCollapsed" class="flex items-center gap-2 px-3 h-12 bg-zinc-950/95 backdrop-blur-md border-b border-zinc-800 z-30">
        <button @click="emit('toggleDrawer')" class="icon-btn"><Menu class="w-4 h-4" /></button>
        <div class="w-px h-5 bg-zinc-700 mx-1" />

        <button @click="emit('openAddModal')" class="add-btn">
          <Plus class="w-3.5 h-3.5" /><span>添加</span>
        </button>

        <!-- 正在播放列表 -->
        <div class="flex items-center gap-1.5 overflow-x-auto scrollbar-none flex-1 mx-1">
          <TransitionGroup name="pills">
            <span v-for="ch in channels" :key="ch.id" class="channel-pill" :class="ch.platform === 'youtube' ? 'yt-pill' : 'bili-pill'">
              <span class="text-[10px] font-bold">{{ ch.platform === 'youtube' ? 'YT' : 'B' }}</span>
              <span class="max-w-[60px] truncate text-[11px]">{{ ch.id }}</span>
              <button @click="emit('removeChannelByPlatformId', ch.platform, ch.id)" class="close-pill-btn"><X class="w-2.5 h-2.5" /></button>
            </span>
          </TransitionGroup>
        </div>

        <div class="flex items-center gap-0.5 shrink-0">
          <!-- 智能布局预设 Popover -->
          <n-popover trigger="click" placement="bottom" scrollable style="background-color: #18181b; border: 1px solid #3f3f46; color: white; width: 240px;">
            <template #trigger>
              <button class="icon-btn flex items-center gap-1 hover:text-rose-400">
                <LayoutTemplate class="w-4 h-4" />
                <span class="text-[10px]">布局预设</span>
              </button>
            </template>
            
            <div class="p-2">
              <div class="text-[10px] text-zinc-500 font-bold mb-3 uppercase tracking-wider">适合当前 ({{ channels.length }}) 本视频</div>
              
              <div class="flex flex-col gap-1.5">
                <button 
                  v-for="opt in currentRecommendations" 
                  :key="opt.id" 
                  @click="emit('applyPreset', opt.id)"
                  class="preset-item-btn group"
                >
                  <!-- 简易布局图标预览 -->
                  <div class="w-10 h-6 bg-zinc-900 border border-zinc-700 rounded overflow-hidden flex p-0.5 gap-0.5">
                    <template v-if="opt.icon === '2h'"><div class="flex-1 bg-zinc-600"></div><div class="flex-1 bg-zinc-600"></div></template>
                    <template v-if="opt.icon === '3-12'"><div class="w-[60%] bg-rose-500/40"></div><div class="flex-1 flex flex-col gap-0.5"><div class="flex-1 bg-zinc-600"></div><div class="flex-1 bg-zinc-600"></div></div></template>
                    <template v-if="opt.icon === '4g'"><div class="flex-1 flex flex-col gap-0.5"><div class="flex-1 bg-zinc-600"></div><div class="flex-1 bg-zinc-600"></div></div><div class="flex-1 flex flex-col gap-0.5"><div class="flex-1 bg-zinc-600"></div><div class="flex-1 bg-zinc-600"></div></div></template>
                    <template v-else><div class="flex-1 bg-zinc-600"></div></template>
                  </div>
                  <span class="text-xs group-hover:text-white">{{ opt.label }}</span>
                </button>
              </div>

              <div class="h-px bg-zinc-800 my-3"></div>

              <button @click="emit('openPresetLibrary')" class="library-trigger-btn">
                <Maximize2 class="w-3 h-3" />
                <span>查看全部预设库</span>
              </button>
            </div>
          </n-popover>

          <div class="w-px h-5 bg-zinc-700 mx-1" />
          <button @click="emit('update:showDanmaku', !showDanmaku)" class="icon-btn" :class="showDanmaku ? 'text-rose-400' : ''"><Captions class="w-4 h-4" /></button>
          <button @click="emit('share')" class="icon-btn"><Share2 class="w-4 h-4" /></button>
          <button @click="emit('openSettings')" class="icon-btn"><Settings class="w-4 h-4" /></button>
          <div class="w-px h-5 bg-zinc-700 mx-1" />
          <button @click="emit('toggleCollapse')" class="icon-btn"><ChevronUp class="w-4 h-4" /></button>
        </div>
      </header>
    </Transition>

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
.icon-btn { @apply p-2 rounded-md text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors; }
.add-btn { @apply flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-rose-600 hover:bg-rose-500 text-white text-xs transition-colors shrink-0; }
.channel-pill { @apply inline-flex items-center gap-1 pl-2 pr-1 py-0.5 rounded-md border text-xs font-mono shrink-0; }
.yt-pill { @apply bg-red-500/20 text-red-400 border-red-500/30; }
.bili-pill { @apply bg-blue-500/20 text-blue-400 border-blue-500/30; }
.close-pill-btn { @apply ml-0.5 opacity-50 hover:opacity-100 rounded-sm hover:bg-white/10 p-0.5; }
.preset-item-btn { @apply flex items-center gap-3 px-2 py-1.5 rounded hover:bg-zinc-800 text-zinc-400 transition-colors text-left; }
.library-trigger-btn { @apply w-full flex items-center justify-center gap-2 py-2 text-[10px] text-zinc-500 hover:text-white hover:bg-zinc-800 rounded border border-dashed border-zinc-700 transition-all; }

.scrollbar-none::-webkit-scrollbar { display: none; }
.slide-down-enter-active, .slide-down-leave-active { transition: all 0.3s ease; }
.slide-down-enter-from, .slide-down-leave-to { transform: translateY(-100%); opacity: 0; }
</style>