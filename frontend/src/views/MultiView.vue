<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { X, LayoutGrid } from 'lucide-vue-next'

import { useMultiviewStore } from '@/stores/multiview'
import { useThemeStore } from '@/stores/theme'
import { useOrganizations } from '@/queries'

import { streamApi, userChannelApi, type Channel as ApiChannel, type Stream } from '@/api'
import { type LayoutChannel } from '@/utils/layoutEngine'
import { PRESET_GROUPS, PRESET_META, type PresetId } from '@/utils/presetLayouts'

import VideoGrid from '@/components/multiview/VideoGrid.vue'
import AddVideoModal from '@/components/multiview/AddVideoModal.vue'
import CollapsibleHeader from '@/components/multiview/CollapsibleHeader.vue'
import SidebarDrawer from '@/components/multiview/SidebarDrawer.vue'
import LayoutThumbnail from '@/components/multiview/LayoutThumbnail.vue'
import GroupSelectorModal from '@/components/multiview/GroupSelectorModal.vue'

const route = useRoute()
const router = useRouter()
const themeStore = useThemeStore()
const store = useMultiviewStore()
const orgsQuery = useOrganizations()

// === UI 状态管理 ===
const isLibraryOpen = ref(false)
const isCollapsed = ref(false)
const isDrawerOpen = ref(false)
const isAddModalOpen = ref(false)
const showDanmaku = ref(false)
const showDanmakuSettings = ref(false)
const replaceTargetNodeId = ref<string | null>(null)

// === 分组选择状态 ===
const isGroupSelectorOpen = ref(false)
const selectedGroup = ref<'favorites' | number | null>(null) 
const isRefreshing = ref(false)

// === 数据状态 ===
const allStreams = ref<Stream[]>([])
const likedChannels = ref<ApiChannel[]>([])
const likedOrgIds = ref<number[]>([])

// === 数据获取 ===
async function fetchData() {
  try {
    const [streamsRes, likedRes] = await Promise.all([
      streamApi.getAllStreams(),
      userChannelApi.getLiked()
    ])
    
    allStreams.value = streamsRes.data.filter(s => s.status === 'live')
    likedChannels.value = likedRes.data
    
    // 获取已收藏频道的 orgId
    const likedOrgs = new Set<number>()
    for (const ch of likedRes.data) {
      if (ch.org_id) likedOrgs.add(ch.org_id)
    }
    likedOrgIds.value = Array.from(likedOrgs)
  } catch (error) {
    console.error('Failed to fetch data:', error)
  }
}

// === 计算当前分组直播成员 ===
const groupMembers = computed<Stream[]>(() => {
  if (selectedGroup.value === null) return []
  
  let filtered: Stream[]
  if (selectedGroup.value === 'favorites') {
    const likedChannelIds = new Set(likedChannels.value.map(ch => ch.id))
    filtered = allStreams.value.filter(s => likedChannelIds.has(s.channel_id))
  } else {
    const orgId = selectedGroup.value
    filtered = allStreams.value.filter(s => s.org_id === orgId)
  }
  
  return filtered.sort((a, b) => {
    if (!a.started_at) return 1
    if (!b.started_at) return -1
    return new Date(a.started_at).getTime() - new Date(b.started_at).getTime()
  })
})


const organizationName = computed(() => {
  if (selectedGroup.value === null || selectedGroup.value === 'favorites') return null
  const orgId = selectedGroup.value
  const org = orgsQuery.data.value?.find(o => o.id === orgId)
  return org?.name || null
})

function handleSelectGroup(group: 'favorites' | number) {
  selectedGroup.value = group
}

function handleClearGroup() {
  selectedGroup.value = null
}

function handleOpenGroupSelector() {
  isGroupSelectorOpen.value = true
}

function handleGroupSelected(orgId: number) {
  selectedGroup.value = orgId
  isGroupSelectorOpen.value = false
}

// === 刷新处理 ===
async function handleRefresh() {
  isRefreshing.value = true
  try {
    await fetchData()
  } finally {
    isRefreshing.value = false
  }
}

// === 添加成员到网格 ===
function handleAddMember(member: Stream) {
  if (!member.video_id) return
  handleAddChannel({ platform: member.platform, id: member.video_id })
}

// === 业务逻辑转发至 Store ===

function openAddModal() {
  replaceTargetNodeId.value = null
  isAddModalOpen.value = true
}

function openReplaceModal(nodeId: string) {
  replaceTargetNodeId.value = nodeId
  isAddModalOpen.value = true
}

function handleAddChannel(channel: LayoutChannel) {
  if (replaceTargetNodeId.value) {
    store.replaceChannel(replaceTargetNodeId.value, channel)
  } else {
    store.addChannel(channel)
  }
}

async function handleShare() {
  await store.copyShareUrl()
  alert('分享链接已复制 ✓')
}

function handleApplyPreset(id: PresetId) {
  store.applyPreset(id)
  isLibraryOpen.value = false
}

// === 生命周期 ===
onMounted(async () => {
  // 加载直播数据
  await fetchData()
  
  // 1. 优先检查分享参数
  const shareCode = route.query.c as string
  if (shareCode) {
    const success = store.loadFromShareParam(shareCode)
    if (success) {
      router.replace({ name: 'MultiView' }) // 清理 URL
      return
    }
  }

  // 2. 否则初始化本地缓存
})
</script>


<template>
  <div class="h-full w-full flex flex-col overflow-hidden bg-zinc-950 text-white">
    <!-- 侧边栏抽屉组件 -->
    <SidebarDrawer
      v-model="isDrawerOpen"
      :is-dark="themeStore.isDark"
      :current-theme-id="themeStore.currentThemeId"
      :themes="themeStore.themes"
      @toggle-dark="themeStore.toggleDark()"
      @set-theme="themeStore.setTheme"
    />

    <!-- 顶部工具栏 -->
    <CollapsibleHeader
      :is-collapsed="isCollapsed"
      :channels="store.activeChannels"
      :show-danmaku="showDanmaku"
      :selected-group="selectedGroup"
      :organization-name="organizationName"
      :group-members="groupMembers"
      :is-refreshing="isRefreshing"
      @toggle-drawer="isDrawerOpen = !isDrawerOpen"
      @toggle-collapse="isCollapsed = !isCollapsed"
      @open-add-modal="openAddModal"
      @remove-channel-by-platform-id="store.removeByPlatformId"
      @apply-preset="handleApplyPreset"
      @open-preset-library="isLibraryOpen = true" 
      @share="handleShare"
      @update:show-danmaku="showDanmaku = $event"
      @open-settings="showDanmakuSettings = true"
      @select-group="handleSelectGroup"
      @clear-group="handleClearGroup"
      @open-group-selector="handleOpenGroupSelector"
      @refresh="handleRefresh"
      @add-member="handleAddMember"
    />


    <!-- 核心网格视图 (递归树结构) -->
    <VideoGrid
      :layout-tree="store.tree"
      :show-danmaku="showDanmaku"
      :danmaku-settings="store.danmakuSettings"
      @request-add="openAddModal"
      @request-replace="openReplaceModal"
      @clear-channel="store.clearChannel"
      @close-channel="store.closeChannel"
    />

    <!-- 添加视频模态框 -->
    <AddVideoModal v-model="isAddModalOpen" @add="handleAddChannel" />

    <!-- 分组选择器模态框 -->
    <GroupSelectorModal
      v-model="isGroupSelectorOpen"
      :organizations="orgsQuery.data.value ?? []"
      :liked-org-ids="likedOrgIds"
      @select="handleGroupSelected"
    />

    <Teleport to="body">
      <Transition name="fade">
        <div v-if="isLibraryOpen" class="fixed inset-0 bg-black/90 backdrop-blur-md z-[100] flex items-center justify-center p-4" @click.self="isLibraryOpen = false">
          <div class="bg-zinc-900 border border-zinc-800 rounded-3xl w-full max-w-5xl max-h-[85vh] overflow-hidden flex flex-col shadow-2xl">
            <div class="px-8 py-6 border-b border-zinc-800 flex items-center justify-between">
              <div class="flex items-center gap-3">
                <div class="p-2 bg-rose-500/20 rounded-lg text-rose-500"><LayoutGrid class="w-6 h-6" /></div>
                <div>
                  <h2 class="text-xl font-bold">全量布局预设库</h2>
                  <p class="text-xs text-zinc-500">根据视频数量选择最适合的排版模式</p>
                </div>
              </div>
              <button @click="isLibraryOpen = false" class="p-2 hover:bg-zinc-800 rounded-full transition-colors"><X /></button>
            </div>

            <div class="flex-1 overflow-y-auto p-8 grid grid-cols-1 gap-10">
              <div v-for="group in PRESET_GROUPS" :key="group.label">
                <h3 class="text-xs font-black text-zinc-600 uppercase tracking-[0.3em] mb-6 border-l-2 border-rose-500 pl-3">
                  {{ group.label }}
                </h3>
                <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-6">
                  <button 
                    v-for="id in group.items" 
                    :key="id" 
                    @click="handleApplyPreset(id)" 
                    class="group flex flex-col gap-3 text-center"
                  >
                    <div class="aspect-video w-full p-1 bg-zinc-800 rounded-xl border-2 border-transparent group-hover:border-rose-500 transition-all">
                      <LayoutThumbnail :type="id" />
                    </div>
                    <div class="flex flex-col">
                      <span class="text-xs font-bold text-zinc-400 group-hover:text-white">{{ PRESET_META[id].label }}</span>
                      <span class="text-[9px] text-zinc-600 mt-0.5 tracking-widest uppercase">{{ id }}</span>
                    </div>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- 弹幕设置模态框 -->
    <Teleport to="body">
      <div
        v-if="showDanmakuSettings"
        class="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
        @click.self="showDanmakuSettings = false"
      >
        <div class="bg-zinc-900 rounded-xl p-6 w-[400px] max-h-[80vh] overflow-y-auto border border-zinc-700">
          <div class="flex items-center justify-between mb-6">
            <h2 class="text-lg font-bold">弹幕设置</h2>
            <button @click="showDanmakuSettings = false" class="text-zinc-400 hover:text-white">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div class="space-y-5">
            <div>
              <label class="block text-sm text-zinc-400 mb-2">字体大小: {{ store.danmakuSettings.fontSize }}px</label>
              <input
                type="range"
                v-model.number="store.danmakuSettings.fontSize"
                min="12"
                max="48"
                class="w-full accent-rose-500"
                
              />
            </div>

            <div>
              <label class="block text-sm text-zinc-400 mb-2">弹幕速度: {{ store.danmakuSettings.speed }}</label>
              <input
                type="range"
                v-model.number="store.danmakuSettings.speed"
                min="0.5"
                max="6"
                step="0.5"
                class="w-full accent-rose-500"
                
              />
            </div>

            <div>
              <label class="block text-sm text-zinc-400 mb-2">不透明度: {{ store.danmakuSettings.opacity }}</label>
              <input
                type="range"
                v-model.number="store.danmakuSettings.opacity"
                min="0.3"
                max="1"
                step="0.1"
                class="w-full accent-rose-500"
                
              />
            </div>

            <div>
              <label class="block text-sm text-zinc-400 mb-2">弹幕颜色</label>
              <div class="flex gap-2 flex-wrap">
                <button
                  v-for="c in ['#ffffff', '#ff6b6b', '#ffd700', '#90EE90', '#87CEEB', '#ff69b4']"
                  :key="c"
                  @click="store.updateDanmakuSettings({ color: c })"
                  class="w-8 h-8 rounded-full border-2 transition-transform hover:scale-110"
                  :style="{ backgroundColor: c }"
                  :class="store.danmakuSettings.color === c ? 'border-white' : 'border-transparent'"
                />
              </div>
            </div>

            <div class="flex items-center gap-3">
              <label class="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  v-model="store.danmakuSettings.strokeEnabled"
                  class="w-4 h-4 accent-rose-500"
                  
                />
                <span class="text-sm text-zinc-300">描边</span>
              </label>
              <template v-if="store.danmakuSettings.strokeEnabled">
                <input
                  v-model="store.danmakuSettings.strokeColor"
                  type="color"
                  class="w-8 h-8 rounded cursor-pointer"
                  
                />
                <span class="text-xs text-zinc-500">宽度</span>
                <input
                  type="range"
                  v-model.number="store.danmakuSettings.strokeWidth"
                  min="0"
                  max="4"
                  class="w-20 accent-rose-500"
                  
                />
              </template>
            </div>

            <div class="pt-4 border-t border-zinc-700">
              <button
                @click="store.resetDanmakuSettings()"
                class="px-4 py-2 bg-zinc-700 hover:bg-zinc-600 rounded text-sm transition-colors"
              >
                恢复默认
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>