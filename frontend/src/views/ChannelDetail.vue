<template>
  <div v-if="loading" class="flex justify-center py-16">
    <div class="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-pink-500"></div>
  </div>

  <div v-else-if="channel" class="min-h-screen bg-zinc-950">
    <!-- Banner -->
    <div 
      class="h-48 md:h-64 bg-cover bg-center relative"
      :style="channel.banner_url ? { backgroundImage: `url(${channel.banner_url})` } : { background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)' }"
    >
      <div class="absolute inset-0 bg-gradient-to-t from-zinc-950 via-zinc-950/50 to-transparent"></div>
    </div>

    <!-- 频道信息 -->
    <div class="relative px-4 md:px-8 -mt-20">
      <div class="flex flex-col md:flex-row md:items-end gap-4 md:gap-6">
        <!-- 头像 -->
        <div class="shrink-0">
          <img
            :src="channel.avatar_url || '/placeholder-avatar.png'"
            class="w-28 h-28 md:w-32 md:h-32 rounded-full border-4 border-zinc-950 object-cover"
            referrerpolicy="no-referrer"
          />
        </div>

        <!-- 名称和机构 -->
        <div class="flex-1 pb-2">
          <h1 class="text-2xl md:text-3xl font-bold text-white">{{ channel.name }}</h1>
          <div class="flex items-center gap-2 mt-1 flex-wrap">
            <span 
              v-if="channel.platform === 'youtube'"
              class="px-2 py-0.5 bg-red-600 text-white text-xs rounded-full"
            >
              YouTube
            </span>
            <span 
              v-else
              class="px-2 py-0.5 bg-blue-500 text-white text-xs rounded-full"
            >
              Bilibili
            </span>
            <span class="text-gray-400 text-sm">{{ getOrgName(channel.org_id) }}</span>
          </div>
          <!-- Bilibili 额外信息 -->
          <div v-if="channel.platform === 'bilibili'" class="mt-2 text-sm text-gray-400">
            <span v-if="channel.bilibili_fans" class="mr-4">
              粉丝: {{ channel.bilibili_fans.toLocaleString() }}
            </span>
            <span v-if="channel.bilibili_archive_count" class="mr-4">
              稿件: {{ channel.bilibili_archive_count }}
            </span>
            <p v-if="channel.bilibili_sign" class="mt-1 text-gray-500 line-clamp-2">{{ channel.bilibili_sign }}</p>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="flex items-center gap-3 pb-2">
          <n-button
            :type="channel.is_liked ? 'primary' : 'default'"
            @click="toggleLike"
            class="flex items-center gap-2"
          >
            <Heart class="w-4 h-4" :class="{ 'fill-current': channel.is_liked }" />
            <span>{{ channel.is_liked ? '已喜欢' : '喜欢' }}</span>
          </n-button>

          <n-button
            :type="channel.is_blocked ? 'error' : 'default'"
            @click="toggleBlock"
            class="flex items-center gap-2"
          >
            <Ban class="w-4 h-4" />
            <span>{{ channel.is_blocked ? '已屏蔽' : '屏蔽' }}</span>
          </n-button>

          <a
            v-if="channel.youtube_url"
            :href="channel.youtube_url"
            target="_blank"
            class="n-button n-button--default-type"
          >
            <Youtube class="w-4 h-4 mr-2" />
            YouTube
          </a>

          <a
            v-if="channel.twitter_url"
            :href="channel.twitter_url"
            target="_blank"
            class="n-button n-button--default-type"
          >
            <svg class="w-4 h-4 mr-2" viewBox="0 0 24 24" fill="currentColor">
              <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
            </svg>
            X
          </a>
        </div>
      </div>

      <!-- Tabs -->
      <div class="mt-8 border-b border-zinc-800">
        <nav class="flex gap-1">
          <button
            v-for="tab in tabs"
            :key="tab.value"
            @click="activeTab = tab.value"
            class="px-4 py-3 text-sm font-medium transition-colors relative"
            :class="activeTab === tab.value 
              ? 'text-white' 
              : 'text-gray-400 hover:text-white'"
          >
            {{ tab.label }}
            <span 
              v-if="activeTab === tab.value"
              class="absolute bottom-0 left-0 right-0 h-0.5 bg-pink-500"
            ></span>
          </button>
        </nav>
      </div>

      <!-- Tab 内容 -->
      <div class="py-6">
        <!-- 直播 Tab -->
        <div v-if="activeTab === 'live'">
          <div v-if="liveVideos.length > 0">
            <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              <div
                v-for="video in liveVideos"
                :key="video.id"
                class="bg-zinc-900 rounded-lg overflow-hidden hover:bg-zinc-800 transition-colors cursor-pointer"
                @click="addToMultiview(video)"
              >
                <div class="aspect-video relative">
                  <img 
                    :src="video.thumbnail_url || '/placeholder.png'" 
                    class="w-full h-full object-cover"
                    referrerpolicy="no-referrer"
                  />
                  <span 
                    v-if="video.status === 'live'"
                    class="absolute top-2 left-2 bg-red-600 text-white text-xs px-2 py-0.5 rounded flex items-center gap-1"
                  >
                    <span class="w-1.5 h-1.5 bg-white rounded-full animate-pulse"></span>
                    直播中
                  </span>
                  <span 
                    v-else-if="video.status === 'upcoming'"
                    class="absolute top-2 left-2 bg-yellow-600 text-white text-xs px-2 py-0.5 rounded"
                  >
                    预约
                  </span>
                  <span 
                    v-if="video.duration"
                    class="absolute bottom-2 right-2 bg-black/80 text-white text-xs px-2 py-1 rounded"
                  >
                    {{ video.duration }}
                  </span>
                </div>
                <div class="p-3">
                  <h4 class="text-sm text-white line-clamp-2">{{ video.title }}</h4>
                  <p class="text-xs text-gray-500 mt-1">{{ video.view_count }} views · {{ video.published_at }}</p>
                </div>
              </div>
            </div>

            <div v-if="liveTotalPages > 1" class="flex justify-center mt-6">
              <n-pagination
                v-model:page="liveCurrentPage"
                :page-count="liveTotalPages"
                @update:page="fetchLiveVideos(Number(route.params.id))"
              />
            </div>
          </div>
          <div v-else class="text-center py-12 text-gray-500">
            暂无直播
          </div>
        </div>

        <!-- 视频 Tab -->
        <div v-if="activeTab === 'videos'">
          <div v-if="videos.length > 0" class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            <div
              v-for="video in videos"
              :key="video.id"
              class="bg-zinc-900 rounded-lg overflow-hidden hover:bg-zinc-800 transition-colors cursor-pointer"
              @click="addToMultiview(video)"
            >
              <div class="aspect-video relative">
                <img 
                  :src="video.thumbnail_url || '/placeholder.png'" 
                  class="w-full h-full object-cover"
                  referrerpolicy="no-referrer"
                />
                <span class="absolute bottom-2 right-2 bg-black/80 text-white text-xs px-2 py-1 rounded">
                  {{ video.duration }}
                </span>
              </div>
              <div class="p-3">
                <h4 class="text-sm text-white line-clamp-2">{{ video.title }}</h4>
                <p class="text-xs text-gray-500 mt-1">{{ video.view_count }} views · {{ video.published_at }}</p>
              </div>
            </div>
          </div>
          <div v-else class="text-center py-12 text-gray-500">
            暂无视频
          </div>
          <div v-if="totalPages > 1" class="flex justify-center mt-6">
            <n-pagination
              v-model:page="currentPage"
              :page-count="totalPages"
              @update:page="fetchVideos(Number(route.params.id))"
            />
          </div>
        </div>

        <!-- Shorts Tab -->
        <div v-if="activeTab === 'shorts'">
          <div v-if="shortsVideos.length > 0" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
            <div
              v-for="video in shortsVideos"
              :key="video.id"
              class="bg-zinc-900 rounded-lg overflow-hidden hover:bg-zinc-800 transition-colors cursor-pointer"
              @click="addToMultiview(video)"
            >
              <div class="aspect-[9/16] relative">
                <img 
                  :src="video.thumbnail_url || '/placeholder.png'" 
                  class="w-full h-full object-cover"
                  referrerpolicy="no-referrer"
                />
                <span 
                  v-if="video.duration"
                  class="absolute bottom-2 right-2 bg-black/80 text-white text-xs px-2 py-1 rounded"
                >
                  {{ video.duration }}
                </span>
              </div>
              <div class="p-2">
                <h4 class="text-sm text-white line-clamp-2">{{ video.title }}</h4>
                <p class="text-xs text-gray-500 mt-1">{{ video.view_count }} views</p>
              </div>
            </div>
          </div>
          <div v-else class="text-center py-12 text-gray-500">
            暂无Shorts
          </div>
        </div>

        <!-- 概要 Tab -->
        <div v-if="activeTab === 'streams'">
          <div class="bg-zinc-900 rounded-lg p-6">
            <h3 class="text-lg font-medium text-white mb-4">频道简介</h3>
            <div v-if="channel.description" class="text-gray-300 whitespace-pre-wrap text-sm leading-relaxed">
              {{ channel.description }}
            </div>
            <div v-else class="text-center py-8 text-gray-500">
              暂无简介
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NPagination } from 'naive-ui'
import { Heart, Ban, Youtube } from 'lucide-vue-next'
import { useOrgStore } from '../stores/org'
import { channelApi, type Channel as ApiChannel } from '../api'

// 引入我们刚才新建的布局树引擎
import { 
  createEmptyLeaf, 
  addChannelToTree, 
  getActiveChannels,
  type LayoutNode 
} from '@/utils/layoutEngine'

interface Video {
  id: string
  title: string
  thumbnail_url: string
  duration: string
  view_count: number
  published_at: string
  status: string
}

const route = useRoute()
const router = useRouter()
const orgStore = useOrgStore()

const channel = ref<ApiChannel | null>(null)
const loading = ref(true)
const activeTab = ref('videos')

const videos = ref<Video[]>([])
const liveVideos = ref<Video[]>([])
const shortsVideos = ref<Video[]>([])
const currentPage = ref(1)
const totalPages = ref(0)
const totalVideos = ref(0)
const liveCurrentPage = ref(1)
const liveTotalPages = ref(0)
const liveTotalVideos = ref(0)

const tabs = [
  { value: 'live', label: '直播' },
  { value: 'videos', label: '视频' },
  { value: 'shorts', label: 'Shorts' },
  { value: 'streams', label: '概要' }
]

function getOrgName(orgId: number | null): string {
  if (!orgId) return ''
  const org = orgStore.organizations.find(o => o.id === orgId)
  return org?.name || ''
}

function toggleLike() {
  if (channel.value) {
    channel.value.is_liked = !channel.value.is_liked
  }
}

function toggleBlock() {
  if (channel.value) {
    channel.value.is_blocked = !channel.value.is_blocked
  }
}

// === 重点修改：适配全新的二叉树多窗系统 ===
function addToMultiview(video?: Video) {
  if (!channel.value) return
  
  // 构造要添加的视频节点数据
  const channelData = {
    platform: channel.value.platform as 'youtube' | 'bilibili',
    id: video ? video.id : channel.value.channel_id
  }

  let tree: LayoutNode
  try {
    // 尝试读取现有的布局树
    const saved = localStorage.getItem('multiview_tree')
    tree = saved ? JSON.parse(saved) : createEmptyLeaf()
    
    // 检查这个视频是否已经在当前播放列表中了
    const existingChannels = getActiveChannels(tree)
    const isExist = existingChannels.some(
      c => c.id === channelData.id && c.platform === channelData.platform
    )

    if (!isExist) {
      // 核心算法：自动寻找最大面积的窗口切分一半给新视频，或者填补空位
      addChannelToTree(tree, channelData)
      localStorage.setItem('multiview_tree', JSON.stringify(tree))
    }
  } catch (err) {
    // 如果解析失败，重新创建一个树
    tree = createEmptyLeaf()
    addChannelToTree(tree, channelData)
    localStorage.setItem('multiview_tree', JSON.stringify(tree))
  }

  router.push({ name: 'MultiView' })
}
// ===========================================

async function fetchChannel(id: number) {
  loading.value = true
  try {
    const { data } = await channelApi.get(id)
    channel.value = data
    currentPage.value = 1
    liveCurrentPage.value = 1
    await fetchVideos(id)
    await fetchLiveVideos(id)
    await fetchShortsVideos(id)
  } catch (err) {
    console.error('Failed to fetch channel:', err)
  } finally {
    loading.value = false
  }
}

async function fetchVideos(channelId: number) {
  try {
    const platform = channel.value?.platform
    const status = platform === 'youtube' ? 'upload' : undefined
    const { data } = await channelApi.getVideos(channelId, currentPage.value, 24, status)
    videos.value = data.videos
    totalPages.value = data.total_pages
    totalVideos.value = data.total
  } catch (err) {
    console.error('Failed to fetch videos:', err)
  }
}

async function fetchLiveVideos(channelId: number) {
  try {
    const platform = channel.value?.platform
    const status = platform === 'youtube' ? 'live' : undefined
    const { data } = await channelApi.getVideos(channelId, liveCurrentPage.value, 48, status)
    liveVideos.value = data.videos
    liveTotalPages.value = data.total_pages
    liveTotalVideos.value = data.total
  } catch (err) {
    console.error('Failed to fetch live videos:', err)
  }
}

async function fetchShortsVideos(channelId: number) {
  try {
    const platform = channel.value?.platform
    const status = platform === 'youtube' ? 'short' : undefined
    const { data } = await channelApi.getVideos(channelId, 1, 50, status)
    shortsVideos.value = data.videos
  } catch (err) {
    console.error('Failed to fetch shorts videos:', err)
  }
}

onMounted(async () => {
  await orgStore.fetchOrganizations()
  const channelId = Number(route.params.id)
  await fetchChannel(channelId)
})

watch(activeTab, async (tab) => {
  if (!channel.value) return
  const channelId = Number(route.params.id)
  if (tab === 'videos') {
    currentPage.value = 1
    await fetchVideos(channelId)
  } else if (tab === 'live') {
    liveCurrentPage.value = 1
    await fetchLiveVideos(channelId)
  } else if (tab === 'shorts') {
    await fetchShortsVideos(channelId)
  }
})
</script>