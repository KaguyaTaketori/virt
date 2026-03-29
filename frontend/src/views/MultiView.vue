<script setup lang="ts">
/**
 * MultiView.vue
 *
 * 溢出修复链路：
 *   AppLayout → RouterView 容器 (flex-1 min-h-0)
 *     → 本组件根容器 (h-full flex flex-col overflow-hidden)
 *       → VideoGrid (flex-1 min-h-0)
 *   整个链路不含任何固定 height 计算，彻底消灭滚动条。
 */
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import VideoGrid from '@/components/multiview/VideoGrid.vue'
import AddVideoModal from '@/components/multiview/AddVideoModal.vue'
import CollapsibleHeader from '@/components/multiview/CollapsibleHeader.vue'
import SidebarDrawer from '@/components/multiview/SidebarDrawer.vue'
import { useThemeStore } from '@/stores/theme'

const themeStore = useThemeStore()

interface Channel {
  platform: 'youtube' | 'bilibili'
  id: string
}

interface Layout {
  name: string; label: string; cols: number; cells: number
}

const layouts: Layout[] = [
  { name: '1x1', label: '1×1', cols: 1, cells: 1 },
  { name: '2x1', label: '2×1', cols: 2, cells: 2 },
  { name: '2x2', label: '2×2', cols: 2, cells: 4 },
  { name: '3x2', label: '3×2', cols: 3, cells: 6 },
  { name: '3x3', label: '3×3', cols: 3, cells: 9 },
  { name: '4x3', label: '4×3', cols: 4, cells: 12 },
  { name: '4x4', label: '4×4', cols: 4, cells: 16 },
]

const route  = useRoute()
const router = useRouter()

const channels        = ref<Channel[]>([])
const selectedLayout  = ref<string>('2x2')
const showDanmaku     = ref<boolean>(false)
const isAddModalOpen  = ref<boolean>(false)
const isCollapsed     = ref<boolean>(false)
const isDrawerOpen    = ref<boolean>(false)

function addChannel(channel: Channel): void {
  if (!channels.value.find(c => c.id === channel.id && c.platform === channel.platform)) {
    channels.value.push(channel)
  }
  localStorage.setItem('multiview_channels', JSON.stringify(channels.value))
}

function removeChannel(idx: number): void {
  channels.value.splice(idx, 1)
  localStorage.setItem('multiview_channels', JSON.stringify(channels.value))
}

function shareUrl(): void {
  const code = btoa(channels.value.map(c => `${c.platform}_${c.id}`).join(','))
  const url  = `${window.location.origin}/multiview?c=${code}`
  navigator.clipboard.writeText(url).then(() => alert('分享链接已复制 ✓'))
}

onMounted(() => {
  const share = Array.isArray(route.query.c) ? route.query.c[0] : route.query.c
  if (share) {
    try {
      const list = atob(share).split(',')
        .map(item => { const [platform, id] = item.split('_'); return { platform, id } as Channel })
        .filter(c => c.platform && c.id)
      if (list.length) { channels.value = list; router.replace({ name: 'MultiView' }) }
    } catch { /**/ }
  } else {
    try {
      const saved = localStorage.getItem('multiview_channels')
      if (saved) channels.value = JSON.parse(saved)
    } catch { /**/ }
  }
})
</script>

<template>
  <div class="h-full w-full flex flex-col overflow-hidden bg-zinc-950 text-white">
    <SidebarDrawer
      v-model="isDrawerOpen"
      :is-dark="themeStore.isDark"
      :current-theme-id="themeStore.currentThemeId"
      :themes="themeStore.themes"
      @toggle-dark="themeStore.toggleDark"
      @set-theme="themeStore.setTheme"
    />

    <CollapsibleHeader
      :is-collapsed="isCollapsed"
      :channels="channels"
      :selected-layout="selectedLayout"
      :layouts="layouts"
      :show-danmaku="showDanmaku"
      @toggle-drawer="isDrawerOpen = !isDrawerOpen"
      @toggle-collapse="isCollapsed = !isCollapsed"
      @open-add-modal="isAddModalOpen = true"
      @remove-channel="removeChannel"
      @set-layout="selectedLayout = $event"
      @update:show-danmaku="showDanmaku = $event"
      @share="shareUrl"
      @open-settings=""
    />

    <VideoGrid
      :channels="channels"
      :selected-layout="selectedLayout"
      :layouts="layouts"
      :show-danmaku="showDanmaku"
      @request-add="isAddModalOpen = true"
    />

    <AddVideoModal v-model="isAddModalOpen" @add="addChannel" />
  </div>
</template>