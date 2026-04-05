<script setup lang="ts">
import { computed } from 'vue'
import { 
  Menu, Plus, X, ChevronUp, ChevronDown, 
  Share2, Captions, Settings, LayoutTemplate, Maximize2,
  RefreshCw, Star, CirclePlus
} from 'lucide-vue-next'
import { NPopover, NTooltip } from 'naive-ui'
import type { Channel as StreamChannel, Organization } from '@/api'
import { type PresetId, PRESET_META as GLOBAL_PRESET_META } from '@/utils/presetLayouts'

interface Props {
  isCollapsed: boolean
  channels: Channel[]
  showDanmaku: boolean
  selectedGroup: string | null
  organizationName: string | null
  groupMembers: StreamChannel[]
  isRefreshing: boolean
}

interface Channel {
  platform: string
  id: string
}

export type GroupType = 'favorites' | number

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
  (e: 'addMember', member: StreamChannel): void
}>()

const LOCAL_ICONS: Record<PresetId, string> = {
  '1-s': '1',
  '2-h': '2h',
  '2-v': '2v',
  '3-1+2': '3-12',
  '3-cols': '3c',
  '4-grid': '4g',
  '4-1+3': '4-13'
}

const currentRecommendations = computed(() => {
  const count = props.channels.length
  let ids: PresetId[] = []
  
  if (count <= 1) ids = ['1-s']
  else if (count === 2) ids = ['2-h', '2-v']
  else if (count === 3) ids = ['3-1+2', '3-cols']
  else ids = ['4-grid', '4-1+3']

  return ids.map(id => ({ 
    id, 
    label: GLOBAL_PRESET_META[id].label, 
    icon: LOCAL_ICONS[id] 
  }))
})

const groupLabel = computed(() => {
  if (props.selectedGroup === 'favorites') return '收藏夹'
  if (typeof props.selectedGroup === 'number') return props.organizationName || `机构 ${props.selectedGroup}`
  return '请选择分组'
})

function formatLiveDuration(startedAt: string | null): string {
  if (!startedAt) return ''
  const start = new Date(startedAt)
  const now = new Date()
  const diffMs = now.getTime() - start.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  
  if (diffMins < 60) {
    return `${diffMins}m`
  }
  const hours = Math.floor(diffMins / 60)
  return `${hours}h`
}

function handleSelectGroup(group: GroupType) {
  emit('selectGroup', group)
}

function handleRefresh() {
  emit('refresh')
}

function handleAddMember(member: StreamChannel) {
  emit('addMember', member)
}
</script>

<template>
  <div class="relative">
    <!-- 展开手柄 -->
    <div class="absolute top-0 left-0 right-0 h-3 z-40 cursor-pointer" @click="emit('toggleCollapse')" />

    <Transition name="slide-down">
      <header v-if="!isCollapsed" class="flex items-center gap-2 px-3 h-14 bg-zinc-950/95 backdrop-blur-md border-b border-zinc-800 z-30">
        <button @click="emit('toggleDrawer')" class="icon-btn"><Menu class="w-4 h-4" /></button>
        <div class="w-px h-5 bg-zinc-700 mx-1" />

        <!-- 分组选择 Popover -->
        <n-popover trigger="click" placement="bottom-start" :show-arrow="false">
          <template #trigger>
            <button class="group-select-btn">
              <span v-if="selectedGroup">{{ groupLabel }}</span>
              <span v-else>选择分组</span>
              <span v-if="selectedGroup" class="text-zinc-500">({{ groupMembers.length }})</span>
            </button>
          </template>
          
          <div class="bg-zinc-900 border border-zinc-700 rounded-lg shadow-xl overflow-hidden min-w-[140px]">
            <button
              @click="handleSelectGroup('favorites')"
              class="w-full flex items-center gap-2 px-3 py-2.5 text-left text-sm text-zinc-300 hover:bg-zinc-800 transition-colors border-b border-zinc-800"
            >
              <Star class="w-4 h-4 text-amber-400" />
              <span>收藏夹</span>
            </button>
            <button
              @click="emit('openGroupSelector')"
              class="w-full flex items-center gap-2 px-3 py-2.5 text-left text-sm text-zinc-300 hover:bg-zinc-800 transition-colors"
            >
              <div class="w-4 h-4 rounded-full border border-zinc-500" />
              <span>全部</span>
            </button>
          </div>
        </n-popover>

        <!-- 刷新按钮 -->
        <button
          @click="emit('refresh')"
          class="shrink-0 p-1.5 rounded-md text-zinc-500 hover:text-white hover:bg-zinc-800 transition-colors"
          :class="{ 'animate-spin': isRefreshing }"
          :disabled="isRefreshing"
        >
          <RefreshCw class="w-4 h-4" />
        </button>

        <!-- 头像栏 -->
        <div class="flex items-center gap-2 flex-1 mx-2 min-w-0">
          <!-- 头像滚动区域 -->
          <div class="avatar-bar flex-1 min-w-0 flex items-center">
            <div class="avatar-list flex items-center gap-2">
              <n-tooltip
                v-for="member in groupMembers.slice(0, 10)"
                :key="member.id"
                placement="bottom"
                :delay="300"
              >
                <template #trigger>
                  <button
                    @click="handleAddMember(member)"
                    class="avatar-wrapper relative shrink-0"
                  >
                    <img
                      v-if="member.channel_avatar"
                      :src="member.channel_avatar"
                      class="avatar-img"
                      referrerpolicy="no-referrer"
                    />
                    <div v-else class="avatar-placeholder">
                      {{ member.channel_name?.charAt(0) || '?' }}
                    </div>
                    <span v-if="member.started_at" class="avatar-badge">
                      {{ formatLiveDuration(member.started_at) }}
                    </span>
                  </button>
                </template>
                <span class="text-xs">{{ member.channel_name }}</span>
              </n-tooltip>

              <!-- 添加按钮 (在头像旁边) -->
              <button @click="emit('openAddModal')" class="add-icon-btn shrink-0 ml-1">
                <CirclePlus class="w-5 h-5" />
              </button>

              <div
                v-if="!selectedGroup"
                class="text-xs text-zinc-600 italic"
              >
                从上方选择分组查看直播成员
              </div>
              <div
                v-else-if="groupMembers.length === 0"
                class="text-xs text-zinc-600 italic"
              >
                该分组暂无直播
              </div>
            </div>
          </div>
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
.group-select-btn { @apply flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-zinc-800 hover:bg-zinc-700 text-xs text-zinc-300 transition-colors shrink-0; }
.add-icon-btn { @apply p-1.5 rounded-md text-rose-400 hover:text-rose-300 hover:bg-zinc-800 transition-colors; }
.channel-pill { @apply inline-flex items-center gap-1 pl-2 pr-1 py-0.5 rounded-md border text-xs font-mono shrink-0; }
.yt-pill { @apply bg-red-500/20 text-red-400 border-red-500/30; }
.bili-pill { @apply bg-blue-500/20 text-blue-400 border-blue-500/30; }
.close-pill-btn { @apply ml-0.5 opacity-50 hover:opacity-100 rounded-sm hover:bg-white/10 p-0.5; }
.preset-item-btn { @apply flex items-center gap-3 px-2 py-1.5 rounded hover:bg-zinc-800 text-zinc-400 transition-colors text-left; }
.library-trigger-btn { @apply w-full flex items-center justify-center gap-2 py-2 text-[10px] text-zinc-500 hover:text-white hover:bg-zinc-800 rounded border border-dashed border-zinc-700 transition-all; }

.scrollbar-none::-webkit-scrollbar { display: none; }
.slide-down-enter-active, .slide-down-leave-active { transition: all 0.3s ease; }
.slide-down-enter-from, .slide-down-leave-to { transform: translateY(-100%); opacity: 0; }

.avatar-bar {
  overflow-x: auto;
  scrollbar-width: none;
}
.avatar-bar::-webkit-scrollbar {
  display: none;
}

.avatar-wrapper {
  position: relative;
  width: 40px;
  height: 40px;
  flex-shrink: 0;
}

.avatar-img {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  object-fit: cover;
  border: 2px solid transparent;
  transition: border-color 0.2s;
}

.avatar-wrapper:hover .avatar-img {
  border-color: #f43f5e;
}

.avatar-placeholder {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #3f3f46;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #a1a1aa;
  font-weight: 600;
}

.avatar-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  background: #f43f5e;
  color: white;
  font-size: 9px;
  font-weight: 600;
  padding: 1px 4px;
  border-radius: 999px;
  white-space: nowrap;
}

.avatar-list {
  padding: 2px 0;
}
</style>