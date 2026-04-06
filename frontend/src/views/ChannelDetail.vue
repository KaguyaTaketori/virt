<template>
  <div v-if="loading" class="flex justify-center py-16">
    <div class="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-pink-500"></div>
  </div>

  <div v-else-if="bilibiliError" class="flex flex-col items-center justify-center py-16 text-center">
    <div class="bg-zinc-800 p-8 rounded-lg max-w-md">
      <h3 class="text-xl font-bold text-yellow-400 mb-2">需要登录</h3>
      <p class="text-gray-300 mb-4">{{ bilibiliError }}</p>
      <n-button type="primary" @click="goToLogin">去登录</n-button>
    </div>
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
          <div v-if="channel.platform === 'bilibili' && authStore.canAccessBilibili" class="mt-2 text-sm text-gray-400">
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

          <n-button
            v-if="channel.platform === 'bilibili'"
            tag="a"
            :href="'https://space.bilibili.com/' + channel.channel_id"
            target="_blank"
            class="flex items-center gap-2"
          >
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
            </svg>
            <span>B站</span>
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
        <!-- Bilibili 主页 Tab -->
        <div v-if="activeTab === 'home' && isBilibili">
          <div v-if="bilibiliInfo" class="space-y-6">
            <div class="bg-zinc-900 rounded-lg p-6">
              <div class="flex flex-col md:flex-row gap-6">
                <img 
                  :src="bilibiliInfo.face" 
                  class="w-24 h-24 rounded-full"
                  referrerpolicy="no-referrer"
                />
                <div class="flex-1">
                  <h3 class="text-xl font-bold text-white">{{ bilibiliInfo.name }}</h3>
                  <div class="flex flex-wrap gap-3 mt-2 text-sm text-gray-400">
                    <span class="text-pink-400">粉丝 {{ bilibiliInfo.fans?.toLocaleString() }}</span>
                    <span>关注 {{ bilibiliInfo.attention }}</span>
                    <span>稿件 {{ bilibiliInfo.archive_count }}</span>
                  </div>
                  <p v-if="bilibiliInfo.sign" class="mt-3 text-gray-300 text-sm">{{ bilibiliInfo.sign }}</p>
                </div>
              </div>
            </div>
            <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
              <div 
                v-for="v in bilibiliVideos.slice(0, 8)" 
                :key="v.bvid"
                class="bg-zinc-900 rounded-lg overflow-hidden hover:bg-zinc-800 transition-colors cursor-pointer"
              >
                <div class="aspect-video relative">
                  <img 
                    :src="v.pic + '@.webp'" 
                    class="w-full h-full object-cover"
                    referrerpolicy="no-referrer"
                  />
                  <span class="absolute bottom-2 right-2 bg-black/80 text-white text-xs px-2 py-1 rounded">
                    {{ formatDuration(v.duration) }}
                  </span>
                </div>
                <div class="p-2">
                  <h4 class="text-sm text-white line-clamp-2">{{ v.title }}</h4>
                  <p class="text-xs text-gray-500 mt-1">{{ v.play?.toLocaleString() }}播放</p>
                </div>
              </div>
            </div>
          </div>
          <div v-else class="text-center py-12 text-gray-500">加载中...</div>
        </div>

        <!-- Bilibili 动态 Tab -->
        <div v-if="activeTab === 'dynamics' && isBilibili">
          <div v-if="bilibiliDynamics.length > 0" class="space-y-4">
            <div 
              v-for="d in bilibiliDynamics" 
              :key="d.dynamic_id"
              class="bg-zinc-900 rounded-lg p-4"
            >
              <div class="flex items-center gap-2 mb-2">
                <span class="text-xs px-2 py-0.5 bg-pink-600 text-white rounded">{{ getDynamicTypeLabel(d.type) }}</span>
                <span class="text-xs text-gray-500">{{ formatTimestamp(d.timestamp) }}</span>
              </div>
              <p class="text-gray-300 text-sm whitespace-pre-wrap">{{ d.content }}</p>
              <div v-if="d.images?.length > 0" class="flex gap-2 mt-3 flex-wrap">
                <img 
                  v-for="(img, idx) in d.images.slice(0, 4)" 
                  :key="idx"
                  :src="img + '@.webp'" 
                  class="w-20 h-20 object-cover rounded"
                  referrerpolicy="no-referrer"
                />
              </div>
              <p v-if="d.repost_content" class="mt-2 text-gray-500 text-sm border-l-2 border-gray-700 pl-3">
                {{ d.repost_content }}
              </p>
            </div>
          </div>
          <div v-else class="text-center py-12 text-gray-500">暂无动态</div>
        </div>

        <!-- Bilibili 投稿 Tab (从数据库读取) -->
        <div v-if="activeTab === 'videos' && isBilibili">
          <div v-if="videos.length > 0" class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            <div
              v-for="video in videos"
              :key="video.id"
              class="bg-zinc-900 rounded-lg overflow-hidden hover:bg-zinc-800 transition-colors cursor-pointer"
              @click="addToMultiview(video)"
            >
              <div class="aspect-video relative">
                <img 
                  :src="video.thumbnail_url + '@.webp'" 
                  class="w-full h-full object-cover"
                  referrerpolicy="no-referrer"
                />
                <span class="absolute bottom-2 right-2 bg-black/80 text-white text-xs px-2 py-1 rounded">
                  {{ video.duration }}
                </span>
              </div>
              <div class="p-3">
                <h4 class="text-sm text-white line-clamp-2">{{ video.title }}</h4>
                <p class="text-xs text-gray-500 mt-1">{{ video.view_count.toLocaleString() }}播放 · {{ video.published_at }}</p>
              </div>
            </div>
          </div>
          <div v-else class="text-center py-12 text-gray-500">暂无投稿</div>
          <div v-if="totalPages > 1" class="flex justify-center mt-6">
            <n-pagination
              v-model:page="currentPage"
              :page-count="totalPages"
              @update:page="fetchVideos(Number(route.params.id))"
            />
          </div>
        </div>

        <!-- YouTube 直播 Tab -->
        <div v-if="activeTab === 'live' && !isBilibili">
          <div v-if="liveVideos.length > 0">
            <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              <div
                v-for="video in [...liveVideos].sort((a, b) => {
                  if (a.status === 'upcoming' && b.status !== 'upcoming') return -1
                  if (a.status !== 'upcoming' && b.status === 'upcoming') return 1
                  return 0
                })"
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

        <!-- YouTube 视频 Tab -->
        <div v-if="activeTab === 'videos' && !isBilibili">
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

        <!-- YouTube Shorts Tab -->
        <div v-if="activeTab === 'shorts' && !isBilibili">
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

        <!-- YouTube 概要 Tab -->
        <div v-if="activeTab === 'streams' && !isBilibili">
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
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NPagination, useMessage } from 'naive-ui'
import { Heart, Ban, Youtube } from 'lucide-vue-next'
import { useOrgStore } from '../stores/org'
import { useAuthStore } from '../stores/auth'
import { useMultiviewStore } from '@/stores/multiview'
import { channelApi, userChannelApi, type Channel as ApiChannel } from '../api'


interface Video {
  id: string
  title: string
  thumbnail_url: string | null
  duration: string | null
  view_count: number
  published_at: string | null
  status: string
}

interface Dynamic {
  dynamic_id: string
  type: number
  timestamp: number
  content: string
  images: string[]
  repost_content: string | null
}

interface BilibiliVideo {
  bvid: string
  title: string
  pic: string
  aid: number
  duration: string
  pubdate: number
  play: number
}

const route = useRoute()
const router = useRouter()
const orgStore = useOrgStore()
const authStore = useAuthStore()
const multiviewStore = useMultiviewStore()
const message = useMessage()

const channel = ref<ApiChannel | null>(null)
const loading = ref(true)
const bilibiliError = ref<string | null>(null)
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

const bilibiliInfo = ref<any>(null)
const bilibiliDynamics = ref<Dynamic[]>([])
const bilibiliVideos = ref<BilibiliVideo[]>([])

const isBilibili = computed(() => channel.value?.platform === 'bilibili')

const tabs = computed(() => {
  if (isBilibili.value) {
    return [
      { value: 'videos', label: '投稿' },
      { value: 'dynamics', label: '动态' },
      { value: 'home', label: '主页' }
    ]
  }
  return [
    { value: 'live', label: '直播' },
    { value: 'videos', label: '视频' },
    { value: 'shorts', label: 'Shorts' },
    { value: 'streams', label: '概要' }
  ]
})

function getOrgName(orgId: number | null): string {
  if (!orgId) return ''
  const org = orgStore.organizations.find(o => o.id === orgId)
  return org?.name || ''
}

async function toggleLike() {
  if (!channel.value) return
  const prev = channel.value.is_liked
  channel.value.is_liked = !prev
  try {
    if (!prev) {
      await userChannelApi.like(channel.value.id)
      message.success('已添加到收藏')
    } else {
      await userChannelApi.unlike(channel.value.id)
      message.info('已取消收藏')
    }
  } catch {
    channel.value.is_liked = prev
    message.error('操作失败，请重试')
  }
}

async function toggleBlock() {
  if (!channel.value) return
  const prev = channel.value.is_blocked
  channel.value.is_blocked = !prev
  try {
    if (!prev) {
      await userChannelApi.block(channel.value.id)
      message.success('已屏蔽该频道')
    } else {
      await userChannelApi.unblock(channel.value.id)
      message.info('已取消屏蔽')
    }
  } catch {
    channel.value.is_blocked = prev
    message.error('操作失败，请重试')
  }
}

function addToMultiview(video?: Video) {
  if (!channel.value) return
  const id = video?.id ?? channel.value.channel_id
  multiviewStore.addFromVideoId(channel.value.platform as 'youtube' | 'bilibili', id)
  router.push({ name: 'MultiView' })
}

function goToLogin() {
  router.push({ name: 'Login' })
}

async function fetchChannel(id: number) {
  loading.value = true
  bilibiliError.value = null
  try {
    const { data } = await channelApi.get(id)
    channel.value = data
    currentPage.value = 1
    liveCurrentPage.value = 1
    
    if (isBilibili.value) {
      activeTab.value = 'videos'
      await fetchVideos(id)
      await fetchBilibiliData(id)
    } else {
      activeTab.value = 'live'
      await fetchLiveVideos(id)
      await fetchVideos(id)
      await fetchShortsVideos(id)
    }
  } catch (err: any) {
    if (err.response?.status === 403) {
      bilibiliError.value = err.response.data?.detail || 'B站功能需要登录后访问'
      channel.value = null
    } else {
      console.error('Failed to fetch channel:', err)
    }
  } finally {
    loading.value = false
  }
}

async function fetchBilibiliData(channelId: number) {
  try {
    const { data } = await channelApi.getBilibili(channelId)
    bilibiliInfo.value = data.info
    bilibiliDynamics.value = data.dynamics
    bilibiliVideos.value = data.videos
  } catch (err) {
    console.error('Failed to fetch Bilibili data:', err)
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

async function fetchLiveVideos(_channelId: number) {
  try {
    const [liveRes, upcomingRes] = await Promise.all([
      channelApi.getVideos(_channelId, liveCurrentPage.value, 48, 'live'),
      channelApi.getVideos(_channelId, liveCurrentPage.value, 48, 'upcoming')
    ])
    liveVideos.value = [...upcomingRes.data.videos, ...liveRes.data.videos]
    liveTotalPages.value = liveRes.data.total_pages
    liveTotalVideos.value = liveRes.data.total
  } catch (err) {
    console.error('Failed to fetch live videos:', err)
  }
}

async function fetchShortsVideos(channelId: number) {
  try {
    const platform = channel.value?.platform
    const status = platform === 'youtube' ? 'short' : undefined
    const { data } = await channelApi.getVideos(channelId, 1, 48, status)
    shortsVideos.value = data.videos
  } catch (err) {
    console.error('Failed to fetch shorts videos:', err)
  }
}

function formatTimestamp(ts: number): string {
  const date = new Date(ts * 1000)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)
  
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days < 7) return `${days}天前`
  return date.toLocaleDateString('zh-CN')
}

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  return `${m}:${s.toString().padStart(2, '0')}`
}

function getDynamicTypeLabel(type: number): string {
  const map: Record<number, string> = {
    1: '转发',
    2: '图文',
    4: '文字',
    8: '视频',
    64: '专栏'
  }
  return map[type] || '动态'
}

onMounted(async () => {
  await orgStore.invalidate()
  const channelId = Number(route.params.id)
  await fetchChannel(channelId)
})

watch(activeTab, async (tab) => {
  if (!channel.value) return
  const channelId = Number(route.params.id)
  
  if (isBilibili.value) {
    if (tab === 'home' && !bilibiliInfo.value) {
      await fetchBilibiliData(channelId)
    } else if (tab === 'videos') {
      currentPage.value = 1
      await fetchVideos(channelId)
    }
  } else {
    if (tab === 'videos') {
      currentPage.value = 1
      await fetchVideos(channelId)
    } else if (tab === 'live') {
      liveCurrentPage.value = 1
      await fetchLiveVideos(channelId)
    } else if (tab === 'shorts') {
      await fetchShortsVideos(channelId)
    }
  }
})
</script>