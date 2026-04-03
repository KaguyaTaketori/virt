<script setup lang="ts">
import { ref, onMounted, reactive, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

// 导入布局树引擎核心方法
import { 
  LayoutNode, 
  Channel, 
  createEmptyLeaf, 
  createLeaf, 
  addChannelToTree, 
  removeNodeAndMerge, 
  getActiveChannels 
} from '@/utils/layoutEngine'
import { X, LayoutGrid } from 'lucide-vue-next'

// 导入组件
import VideoGrid from '@/components/multiview/VideoGrid.vue'
import AddVideoModal from '@/components/multiview/AddVideoModal.vue'
import CollapsibleHeader from '@/components/multiview/CollapsibleHeader.vue'
import SidebarDrawer from '@/components/multiview/SidebarDrawer.vue'
import LayoutThumbnail from '@/components/multiview/LayoutThumbnail.vue'
import { useThemeStore } from '@/stores/theme'
import { getPresetMeta } from '@/utils/layoutEngine'

const route = useRoute()
const router = useRouter()
const themeStore = useThemeStore()
const isLibraryOpen = ref(false)


// === 状态管理 ===
const isCollapsed = ref(false)
const isDrawerOpen = ref(false)
const isAddModalOpen = ref(false)
const showDanmaku = ref(false)
const showDanmakuSettings = ref(false)
const replaceTargetNodeId = ref<string | null>(null)

// === 弹幕设置逻辑 ===
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

const layoutTree = ref<LayoutNode>(createEmptyLeaf())

const activeChannels = computed(() => getActiveChannels(layoutTree.value))

function saveTreeState() {
  localStorage.setItem('multiview_tree', JSON.stringify(layoutTree.value))
}

function openAddModal() {
  replaceTargetNodeId.value = null
  isAddModalOpen.value = true
}

function openReplaceModal(nodeId: string) {
  replaceTargetNodeId.value = nodeId
  isAddModalOpen.value = true
}

function handleAddChannel(channel: Channel) {
  if (replaceTargetNodeId.value) {
    function replace(node: LayoutNode) {
      if (node.id === replaceTargetNodeId.value) { node.channel = channel }
      else if (node.children) { replace(node.children[0]); replace(node.children[1]) }
    }
    replace(layoutTree.value)
  } else {
    addChannelToTree(layoutTree.value, channel)
  }
  saveTreeState()
}

function clearChannel(nodeId: string) {
  function clear(node: LayoutNode) {
    if (node.id === nodeId && node.type === 'leaf') { 
      node.channel = { platform: 'empty', id: `empty-${Date.now()}` } 
    }
    else if (node.children) { 
      clear(node.children[0]); clear(node.children[1]) 
    }
  }
  clear(layoutTree.value)
  saveTreeState()
}

function closeChannel(nodeId: string) {
  removeNodeAndMerge(layoutTree.value, nodeId)
  saveTreeState()
}

function removeChannelByPlatformId(platform: string, id: string) {
  function findAndRemove(node: LayoutNode): boolean {
    if (node.type === 'leaf' && node.channel?.platform === platform && node.channel?.id === id) {
      closeChannel(node.id)
      return true
    }
    if (node.children) return findAndRemove(node.children[0]) || findAndRemove(node.children[1])
    return false
  }
  findAndRemove(layoutTree.value)
}

function shareUrl(): void {
  const code = btoa(activeChannels.value.map(c => `${c.platform}_${c.id}`).join(','))
  const url  = `${window.location.origin}/multiview?c=${code}`
  navigator.clipboard.writeText(url).then(() => alert('分享链接已复制 ✓'))
}


const L = (v: Channel[], i: number) => createLeaf(v[i] || { platform: 'empty', id: `e-${i}` })

const PRESET_LIBRARY: Record<string, (v: Channel[]) => LayoutNode> = {
  '1-s': (v) => L(v, 0),
  '2-h': (v) => ({ id: 'r', type: 'split', direction: 'horizontal', ratio: 0.5, children: [L(v, 0), L(v, 1)] }),
  '2-v': (v) => ({ id: 'r', type: 'split', direction: 'vertical', ratio: 0.5, children: [L(v, 0), L(v, 1)] }),
  '3-1+2': (v) => ({ id: 'r', type: 'split', direction: 'horizontal', ratio: 0.65, children: [
    L(v, 0), 
    { id: 's', type: 'split', direction: 'vertical', ratio: 0.5, children: [L(v, 1), L(v, 2)] }
  ]}),
  '3-cols': (v) => ({ id: 'r', type: 'split', direction: 'horizontal', ratio: 0.33, children: [
    L(v, 0), 
    { id: 's', type: 'split', direction: 'horizontal', ratio: 0.5, children: [L(v, 1), L(v, 2)] }
  ]}),
  '4-grid': (v) => ({ id: 'r', type: 'split', direction: 'horizontal', ratio: 0.5, children: [
    { id: 'l', type: 'split', direction: 'vertical', ratio: 0.5, children: [L(v, 0), L(v, 2)] },
    { id: 'r', type: 'split', direction: 'vertical', ratio: 0.5, children: [L(v, 1), L(v, 3)] }
  ]}),
  '4-1+3': (v) => ({ id: 'r', type: 'split', direction: 'horizontal', ratio: 0.75, children: [
    L(v, 0),
    { id: 's1', type: 'split', direction: 'vertical', ratio: 0.33, children: [
      L(v, 1),
      { id: 's2', type: 'split', direction: 'vertical', ratio: 0.5, children: [L(v, 2), L(v, 3)] }
    ]}
  ]})
}

const PRESET_GROUPS = [
  { label: '1本视频', items: ['1-s'] },
  { label: '2本视频', items: ['2-h', '2-v'] },
  { label: '3本视频', items: ['3-1+2', '3-cols'] },
  { label: '4本视频', items: ['4-grid', '4-1+3'] }
]

function applyPreset(id: string) {
  const generator = PRESET_LIBRARY[id]
  if (generator) {
    layoutTree.value = generator(activeChannels.value)
    saveTreeState()
  }
}

// === 生命周期与初始化 ===
onMounted(() => {
  loadDanmakuSettings()
  
  // 检查是否有分享链接参数
  const share = Array.isArray(route.query.c) ? route.query.c[0] : route.query.c
  if (share) {
    try {
      const list = atob(share).split(',')
        .map(item => { const [platform, id] = item.split('_'); return { platform, id } as Channel })
        .filter(c => c.platform && c.id)
      
      if (list.length) { 
        layoutTree.value = createEmptyLeaf()
        list.forEach(ch => addChannelToTree(layoutTree.value, ch))
        router.replace({ name: 'MultiView' }) 
      }
    } catch { /**/ }
  } else {
    // 加载本地存储的布局树
    try {
      const saved = localStorage.getItem('multiview_tree')
      if (saved) layoutTree.value = JSON.parse(saved)
    } catch { /**/ }
  }
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
      @toggle-dark="() => themeStore.toggleDark()"
      @set-theme="(id: string) => themeStore.setTheme(id)"
    />

    <!-- 顶部工具栏 -->
    <CollapsibleHeader
      :is-collapsed="isCollapsed"
      :channels="activeChannels"
      :show-danmaku="showDanmaku"
      @toggle-drawer="isDrawerOpen = !isDrawerOpen"
      @toggle-collapse="isCollapsed = !isCollapsed"
      @open-add-modal="openAddModal"
      @remove-channel-by-platform-id="removeChannelByPlatformId"
      @apply-preset="applyPreset"
      @open-preset-library="isLibraryOpen = true" 
      @share="shareUrl"
      @update:show-danmaku="showDanmaku = $event"
      @open-settings="showDanmakuSettings = true"
    />

    <!-- 核心网格视图 (递归树结构) -->
    <VideoGrid
      :layout-tree="layoutTree"
      :show-danmaku="showDanmaku"
      :danmaku-settings="danmakuSettings"
      @request-add="openAddModal"
      @request-replace="openReplaceModal"
      @clear-channel="clearChannel"
      @close-channel="closeChannel"
      @update-tree="saveTreeState"
    />

    <!-- 添加视频模态框 -->
    <AddVideoModal v-model="isAddModalOpen" @add="handleAddChannel" />

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
                <h3 class="text-xs font-black text-zinc-600 uppercase tracking-[0.3em] mb-6 border-l-2 border-rose-500 pl-3">{{ group.label }}</h3>
                <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-6">
                  <button 
                    v-for="id in group.items" 
                    :key="id" 
                    @click="applyPreset(id); isLibraryOpen = false" 
                    class="group flex flex-col gap-3"
                  >
                    <!-- 使用 SVG 缩略图组件 -->
                    <div class="aspect-video w-full p-1 bg-zinc-800 rounded-xl border-2 border-transparent group-hover:border-rose-500 transition-all">
                      <LayoutThumbnail :type="id" />
                    </div>
                    
                    <div class="flex flex-col items-center">
                      <span class="text-xs font-bold text-zinc-400 group-hover:text-white">{{ getPresetMeta(id).label }}</span>
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

    <!-- 弹幕设置模态框 (完整还原) -->
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