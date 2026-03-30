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
import { ref, onMounted, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import VideoGrid from '@/components/multiview/VideoGrid.vue'
import AddVideoModal from '@/components/multiview/AddVideoModal.vue'
import CollapsibleHeader from '@/components/multiview/CollapsibleHeader.vue'
import SidebarDrawer from '@/components/multiview/SidebarDrawer.vue'
import { useThemeStore } from '@/stores/theme'

const themeStore = useThemeStore()

const defaultDanmakuSettings = {
  fontSize: 24,
  speed: 2,
  opacity: 1,
  color: '#ffffff',
  strokeEnabled: true,
  strokeColor: '#000000',
  strokeWidth: 2
}

const danmakuSettings = reactive({ ...defaultDanmakuSettings })

function loadDanmakuSettings() {
  try {
    const saved = localStorage.getItem('danmaku_settings')
    if (saved) Object.assign(danmakuSettings, JSON.parse(saved))
  } catch {}
}

function saveDanmakuSettings() {
  localStorage.setItem('danmaku_settings', JSON.stringify(danmakuSettings))
}

loadDanmakuSettings()

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
const showDanmakuSettings = ref<boolean>(false)

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
      @toggle-dark="() => themeStore.toggleDark()"
      @set-theme="(id: string) => themeStore.setTheme(id)"
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
      @open-settings="showDanmakuSettings = true"
    />

    <VideoGrid
      :channels="channels"
      :selected-layout="selectedLayout"
      :layouts="layouts"
      :show-danmaku="showDanmaku"
      :danmaku-settings="danmakuSettings"
      @request-add="isAddModalOpen = true"
    />

    <AddVideoModal v-model="isAddModalOpen" @add="addChannel" />

    <!-- Danmaku Settings Modal -->
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
              <label class="block text-sm text-zinc-400 mb-2">字体大小: {{ danmakuSettings.fontSize }}px</label>
              <input
                type="range"
                v-model.number="danmakuSettings.fontSize"
                min="12"
                max="48"
                class="w-full accent-rose-500"
                @change="saveDanmakuSettings"
              />
            </div>

            <div>
              <label class="block text-sm text-zinc-400 mb-2">弹幕速度: {{ danmakuSettings.speed }}</label>
              <input
                type="range"
                v-model.number="danmakuSettings.speed"
                min="0.5"
                max="6"
                step="0.5"
                class="w-full accent-rose-500"
                @change="saveDanmakuSettings"
              />
            </div>

            <div>
              <label class="block text-sm text-zinc-400 mb-2">不透明度: {{ danmakuSettings.opacity }}</label>
              <input
                type="range"
                v-model.number="danmakuSettings.opacity"
                min="0.3"
                max="1"
                step="0.1"
                class="w-full accent-rose-500"
                @change="saveDanmakuSettings"
              />
            </div>

            <div>
              <label class="block text-sm text-zinc-400 mb-2">弹幕颜色</label>
              <div class="flex gap-2 flex-wrap">
                <button
                  v-for="c in ['#ffffff', '#ff6b6b', '#ffd700', '#90EE90', '#87CEEB', '#ff69b4']"
                  :key="c"
                  @click="danmakuSettings.color = c; saveDanmakuSettings()"
                  class="w-8 h-8 rounded-full border-2 transition-transform hover:scale-110"
                  :style="{ backgroundColor: c }"
                  :class="danmakuSettings.color === c ? 'border-white' : 'border-transparent'"
                />
              </div>
            </div>

            <div class="flex items-center gap-3">
              <label class="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  v-model="danmakuSettings.strokeEnabled"
                  class="w-4 h-4 accent-rose-500"
                  @change="saveDanmakuSettings"
                />
                <span class="text-sm text-zinc-300">描边</span>
              </label>
              <template v-if="danmakuSettings.strokeEnabled">
                <input
                  v-model="danmakuSettings.strokeColor"
                  type="color"
                  class="w-8 h-8 rounded cursor-pointer"
                  @change="saveDanmakuSettings"
                />
                <span class="text-xs text-zinc-500">宽度</span>
                <input
                  type="range"
                  v-model.number="danmakuSettings.strokeWidth"
                  min="0"
                  max="4"
                  class="w-20 accent-rose-500"
                  @change="saveDanmakuSettings"
                />
              </template>
            </div>

            <div class="pt-4 border-t border-zinc-700">
              <button
                @click="Object.assign(danmakuSettings, defaultDanmakuSettings); saveDanmakuSettings()"
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