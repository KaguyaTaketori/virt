<script setup lang="ts">
import { ref, computed, onMounted, inject, type Ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NPagination } from 'naive-ui'
import { 
  Heart, Ban, Youtube, 
  ExternalLink, Share2, MessageSquare, ThumbsUp 
} from 'lucide-vue-next'

import { useInfiniteScroll } from '@vueuse/core'

import { useOrgStore } from '@/stores/org'
import { useAuthStore } from '@/stores/auth'
import { channelApi, type Channel as ApiChannel } from '@/api'
import { useChannelVideos } from '@/composables/useChannelVideos'
import { useChannelActions } from '@/composables/useChannelActions'
import { useBilibiliData }   from '@/composables/useBilibiliData'

// --- 基础状态 ---
const route = useRoute()
const router = useRouter()
const orgStore = useOrgStore()
const authStore = useAuthStore()

const channel = ref<ApiChannel | null>(null)
const loading = ref(true)
const bilibiliError = ref<string | null>(null)
  
const activeTab = ref('videos')

const { toggleLike, toggleBlock, addToMultiview } = useChannelActions(channel)

// --- Composables ---
const uploadState = useChannelVideos({ status: 'upload', pageSize: 24 })
const shortsState = useChannelVideos({ status: 'short',  pageSize: 48 })
const liveState   = useChannelVideos({
  status: ['live', 'upcoming'],
  pageSize: 48,
  mergeSort: (a, b) => {
    if (a.status === 'upcoming' && b.status !== 'upcoming') return -1
    if (a.status !== 'upcoming' && b.status === 'upcoming') return 1
    return 0
  }
})

const { 
  dynamics: bilibiliAllDynamics, 
  videos: bilibiliVideos, 
  info: bilibiliInfo, 
  loading: bilibiliDynamicsLoading, 
  hasMore: bilibiliDynamicsHasMore, 
  fetch: runBilibiliFetch, 
  loadMore: runBilibiliLoadMore,
  reset: resetBilibiliData 
} = useBilibiliData()

const bilibiliDynamics = computed(() => bilibiliAllDynamics.value)

const isBilibili = computed(() => channel.value?.platform === 'bilibili')

// --- 生命周期与监听 ---
const mainScrollRef = inject<Ref<HTMLElement | null>>('mainScrollRef')

useInfiniteScroll(
  mainScrollRef,
  () => {
    if (activeTab.value === 'dynamics' && bilibiliDynamicsHasMore.value && !bilibiliDynamicsLoading.value) {
      loadMoreDynamics()
    }
  },
  { distance: 100 }
)

// --- 逻辑方法 ---
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


const displayVideos = computed(() => {
  if (isBilibili.value && bilibiliVideos.value.length > 0) {
    return bilibiliVideos.value.map(v => ({
      id: v.bvid,
      thumbnail_url: v.pic,
      title: v.title,
      duration: v.duration,
      view_count: v.play,
      published_at: formatPubDate(v.pubdate),
      status: 'upload',
      isRaw: true
    }))
  }
  return uploadState.videos.value
})



function goToLogin() {
  router.push({ name: 'Login' })
}

async function fetchChannel(id: number) {
  loading.value = true
  bilibiliError.value = null
  try {
    const { data } = await channelApi.get(id)
    channel.value = data
    
    uploadState.reset()
    liveState.reset()
    shortsState.reset()
    resetBilibiliData()

    if (isBilibili.value) {
      activeTab.value = 'videos'
      await Promise.all([
        uploadState.fetch(id),
        runBilibiliFetch(id)
      ])
    } else {
      activeTab.value = 'live'
      await Promise.all([
        liveState.fetch(id),
        uploadState.fetch(id)
      ])
    }
  } catch (err: any) {
    if (err.response?.status === 403) {
      bilibiliError.value = err.response.data?.detail || 'B站功能需要登录'
    }
    console.error('Failed to fetch channel:', err)
  } finally {
    loading.value = false
  }
}

function loadMoreDynamics() {
  if (channel.value) {
    runBilibiliLoadMore(channel.value.id)
  }
}

// function onPageScroll() {
//   if (activeTab.value !== 'dynamics') return
//   if (bilibiliDynamicsLoading.value || !bilibiliDynamicsHasMore.value) return;

//   const target = mainScrollRef?.value || document.documentElement;
//   const { scrollTop, clientHeight, scrollHeight } = target;
  
//   const threshold = 50; 
//   const isBottom = scrollTop + clientHeight >= scrollHeight - threshold;
  
//   if (isBottom) {
//     loadMoreDynamics();
//   }
// }

onMounted(async () => {
  await orgStore.invalidate()
  const channelId = Number(route.params.id)
  await fetchChannel(channelId)
})

watch(activeTab, async (tab) => {
  if (!channel.value) return
  const channelId = channel.value.id

  // 按需加载数据
  if (tab === 'videos' && uploadState.videos.value.length === 0) {
    await uploadState.fetch(channelId)
  } else if (tab === 'live' && liveState.videos.value.length === 0) {
    await liveState.fetch(channelId)
  } else if (tab === 'shorts' && shortsState.videos.value.length === 0) {
    await shortsState.fetch(channelId)
  } else if (tab === 'home' && !bilibiliInfo.value) {
    await runBilibiliFetch(channelId)
  } else if (tab === 'dynamics' && bilibiliDynamics.value.length === 0) {
    await runBilibiliFetch(channelId)
  }
})

// --- 格式化工具函数 ---
function formatCount(num: number): string {
  return num >= 10000 ? (num / 10000).toFixed(1) + '万' : num.toString()
}

function formatPubDate(ts: number): string {
  return ts ? new Date(ts * 1000).toLocaleDateString('zh-CN') : ''
}

function formatTimestamp(ts: number): string {
  const date = new Date(ts * 1000)
  return date.toLocaleDateString('zh-CN') + ' ' + date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function getDynamicTypeLabel(type: number): string {
  const map: Record<number, string> = { 1: '转发', 2: '图文', 4: '文字', 8: '视频', 64: '专栏' }
  return map[type] || '动态'
}

function getOrgName(orgId: number | null): string {
  if (!orgId) return ''
  return orgStore.organizations.find(o => o.id === orgId)?.name || ''
}
</script>

<template>
  <!-- 全局加载状态 -->
  <div v-if="loading" class="flex justify-center py-16">
    <div class="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-pink-500"></div>
  </div>

  <!-- B站未登录/无权限错误 -->
  <div v-else-if="bilibiliError" class="flex flex-col items-center justify-center py-16 text-center">
    <div class="bg-zinc-800 p-8 rounded-lg max-w-md">
      <h3 class="text-xl font-bold text-yellow-400 mb-2">需要登录</h3>
      <p class="text-gray-300 mb-4">{{ bilibiliError }}</p>
      <n-button type="primary" @click="goToLogin">去登录</n-button>
    </div>
  </div>

  <!-- 主内容区 -->
  <div v-else-if="channel" class="min-h-screen bg-zinc-950">
    <!-- Banner 封面 -->
    <div class="h-48 md:h-64 relative overflow-hidden bg-zinc-900">
      <img 
        v-if="channel.banner_url"
        :src="channel.banner_url" 
        class="absolute inset-0 w-full h-full object-cover"
        referrerpolicy="no-referrer"
      />
      <div v-else class="absolute inset-0" style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);"></div>
      <!-- 渐变遮罩层 -->
      <div class="absolute inset-0 bg-gradient-to-t from-zinc-950 via-zinc-950/50 to-transparent"></div>
    </div>

    <!-- 频道详细信息 -->
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

        <!-- 名称和机构信息 -->
        <div class="flex-1 pb-2">
          <h1 class="text-2xl md:text-3xl font-bold text-white">{{ channel.name }}</h1>
          <div class="flex items-center gap-2 mt-1 flex-wrap">
            <span 
              :class="['px-2 py-0.5 text-white text-xs rounded-full', isBilibili ? 'bg-blue-500' : 'bg-red-600']"
            >
              {{ isBilibili ? 'Bilibili' : 'YouTube' }}
            </span>
            <span class="text-gray-400 text-sm">{{ getOrgName(channel.org_id) }}</span>
          </div>
          <!-- Bilibili 专属粉丝/简介 -->
          <div v-if="isBilibili && authStore.canAccessBilibili" class="mt-2 text-sm text-gray-400">
            <span v-if="channel.bilibili_fans" class="mr-4">粉丝: {{ channel.bilibili_fans.toLocaleString() }}</span>
            <span v-if="channel.bilibili_archive_count" class="mr-4">稿件: {{ channel.bilibili_archive_count }}</span>
            <p v-if="channel.bilibili_sign" class="mt-1 text-gray-500 line-clamp-2">{{ channel.bilibili_sign }}</p>
          </div>
        </div>

        <!-- 交互按钮 -->
        <div class="flex items-center gap-3 pb-2">
          <n-button :type="channel.is_liked ? 'primary' : 'default'" @click="toggleLike">
            <Heart class="w-4 h-4 mr-2" :class="{ 'fill-current': channel.is_liked }" />
            {{ channel.is_liked ? '已喜欢' : '喜欢' }}
          </n-button>
          <n-button :type="channel.is_blocked ? 'error' : 'default'" @click="toggleBlock">
            <Ban class="w-4 h-4 mr-2" />
            {{ channel.is_blocked ? '已屏蔽' : '屏蔽' }}
          </n-button>
          <n-button v-if="isBilibili" tag="a" :href="'https://space.bilibili.com/' + channel.channel_id" target="_blank">
            B站
          </n-button>
          <a v-if="channel.youtube_url" :href="channel.youtube_url" target="_blank" class="n-button n-button--default-type">
            <Youtube class="w-4 h-4 mr-2" /> YouTube
          </a>
        </div>
      </div>

      <!-- Tab 导航 -->
      <div class="mt-8 border-b border-zinc-800">
        <nav class="flex gap-1">
          <button
            v-for="tab in tabs" :key="tab.value"
            @click="activeTab = tab.value"
            :class="['px-4 py-3 text-sm font-medium transition-colors relative', activeTab === tab.value ? 'text-white' : 'text-gray-400 hover:text-white']"
          >
            {{ tab.label }}
            <span v-if="activeTab === tab.value" class="absolute bottom-0 left-0 right-0 h-0.5 bg-pink-500"></span>
          </button>
        </nav>
      </div>

      <!-- Tab 内容区 -->
      <div class="py-6">
        <!-- 投稿/普通视频 (B站 & YouTube) -->
        <div v-if="activeTab === 'videos'">
          <div v-if="displayVideos.length > 0" class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            <div v-for="video in displayVideos" :key="video.id" class="video-card bg-zinc-900 rounded-lg overflow-hidden hover:bg-zinc-800 transition-colors cursor-pointer" @click="addToMultiview(video.id)">
              <div class="aspect-video relative">
                <img :src="video.thumbnail_url + (isBilibili ? '@.webp' : '')" class="w-full h-full object-cover" referrerpolicy="no-referrer" />
                <span class="absolute bottom-2 right-2 bg-black/80 text-white text-xs px-2 py-1 rounded">{{ video.duration }}</span>
              </div>
              <div class="p-3">
                <h4 class="text-sm text-white line-clamp-2">{{ video.title }}</h4>
                <p class="text-xs text-gray-500 mt-1">{{ video.view_count.toLocaleString() }} 播放 · {{ video.published_at }}</p>
              </div>
            </div>
          </div>
          <div v-else-if="!uploadState.loading.value" class="text-center py-12 text-gray-500">暂无投稿</div>
          
          <div v-if="uploadState.totalPages.value > 1" class="flex justify-center mt-6">
            <n-pagination v-model:page="uploadState.page.value" :page-count="uploadState.totalPages.value" @update:page="uploadState.fetch(Number(route.params.id))" />
          </div>
        </div>

        <!-- YouTube 直播 Tab -->
        <div v-if="activeTab === 'live' && !isBilibili">
          <div v-if="liveState.videos.value.length > 0">
            <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              <div v-for="video in liveState.videos.value" :key="video.id" class="bg-zinc-900 rounded-lg overflow-hidden hover:bg-zinc-800 transition-colors cursor-pointer" @click="addToMultiview(video.id)">
                <div class="aspect-video relative">
                  <img :src="video.thumbnail_url || '/placeholder.png'" class="w-full h-full object-cover" referrerpolicy="no-referrer" />
                  <span v-if="video.status === 'live'" class="absolute top-2 left-2 bg-red-600 text-white text-xs px-2 py-0.5 rounded flex items-center gap-1">
                    <span class="w-1.5 h-1.5 bg-white rounded-full animate-pulse"></span>直播中
                  </span>
                  <span v-else-if="video.status === 'upcoming'" class="absolute top-2 left-2 bg-yellow-600 text-white text-xs px-2 py-0.5 rounded">预约</span>
                  <span v-if="video.duration" class="absolute bottom-2 right-2 bg-black/80 text-white text-xs px-2 py-1 rounded">{{ video.duration }}</span>
                </div>
                <div class="p-3">
                  <h4 class="text-sm text-white line-clamp-2">{{ video.title }}</h4>
                  <p class="text-xs text-gray-500 mt-1">{{ video.view_count }} views · {{ video.published_at }}</p>
                </div>
              </div>
            </div>
            <div v-if="liveState.totalPages.value > 1" class="flex justify-center mt-6">
              <n-pagination v-model:page="liveState.page.value" :page-count="liveState.totalPages.value" @update:page="liveState.fetch(Number(route.params.id))" />
            </div>
          </div>
          <div v-else-if="!liveState.loading.value" class="text-center py-12 text-gray-500">暂无直播</div>
        </div>

        <!-- YouTube Shorts Tab -->
        <div v-if="activeTab === 'shorts' && !isBilibili">
          <div v-if="shortsState.videos.value.length > 0" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
            <div v-for="video in shortsState.videos.value" :key="video.id" class="bg-zinc-900 rounded-lg overflow-hidden hover:bg-zinc-800 transition-colors cursor-pointer" @click="addToMultiview(video.id)">
              <div class="aspect-[9/16] relative">
                <img :src="video.thumbnail_url || '/placeholder.png'" class="w-full h-full object-cover" referrerpolicy="no-referrer" />
              </div>
              <div class="p-2">
                <h4 class="text-sm text-white line-clamp-2">{{ video.title }}</h4>
                <p class="text-xs text-gray-500 mt-1">{{ video.view_count }} views</p>
              </div>
            </div>
          </div>
          <div v-else-if="!shortsState.loading.value" class="text-center py-12 text-gray-500">暂无 Shorts</div>
        </div>

        <!-- Bilibili 动态 Tab -->
        <div v-if="activeTab === 'dynamics' && isBilibili">
          <div v-if="bilibiliDynamics.length > 0" class="space-y-4">
            <div v-for="d in bilibiliDynamics" :key="d.dynamic_id" class="bg-zinc-900 rounded-lg p-5 shadow-sm border border-zinc-800/50">
              
              <!-- 1. 动态头部：用户信息与置顶 -->
              <div class="flex items-center justify-between mb-4">
                <div class="flex items-center gap-3">
                  <img :src="d.face" class="w-10 h-10 rounded-full border border-zinc-700" referrerpolicy="no-referrer" />
                  <div>
                    <div class="flex items-center gap-2">
                      <span class="text-sm font-bold text-gray-200">{{ d.uname }}</span>
                      <span v-if="d.is_top" class="text-[10px] px-1 bg-orange-500/20 text-orange-500 border border-orange-500/30 rounded">置顶</span>
                    </div>
                    <div class="flex items-center gap-2 mt-0.5">
                      <span class="text-[10px] text-pink-500">{{ getDynamicTypeLabel(d.type) }}</span>
                      <span class="text-[10px] text-gray-500">{{ formatTimestamp(d.timestamp) }}</span>
                    </div>
                  </div>
                </div>
                <a :href="d.url" target="_blank" class="text-gray-500 hover:text-pink-500 transition-colors">
                  <ExternalLink class="w-4 h-4" />
                </a>
              </div>

              <!-- 2. 话题 -->
              <div v-if="d.topic" class="mb-2">
                <span class="text-blue-400 text-sm cursor-pointer hover:underline">#{{ d.topic }}#</span>
              </div>

              <!-- 3. 动态正文 -->
              <div class="text-gray-200 text-sm leading-relaxed whitespace-pre-wrap break-words">
                <template v-for="(node, idx) in d.content_nodes" :key="idx">
                  <span v-if="node.type === 'text'">{{ node.text }}</span>
                  <!-- AT 节点 -->
                  <a v-else-if="node.type === 'at'" :href="'https://space.bilibili.com/' + node.rid" target="_blank" class="text-blue-400 hover:underline mx-0.5">
                    {{ node.text }}
                  </a>
                  <!-- 表情节点 -->
                  <img 
                    v-else-if="node.type === 'emoji'" 
                    :src="node.url" 
                    class="inline-block w-[20px] h-[20px] mx-0.5 align-text-bottom"
                    referrerpolicy="no-referrer"
                  />
                </template>
              </div>

              <!-- 4. 转发内容 -->
              <div v-if="d.repost_content" class="mt-3 p-3 bg-zinc-950/50 rounded border-l-2 border-zinc-700">
                <p class="text-gray-400 text-xs italic leading-snug">
                  {{ d.repost_content }}
                </p>
              </div>

              <!-- 5. 图片展示 (多图适配) -->
              <div v-if="d.images?.length > 0" 
                  :class="['mt-4 grid gap-2 max-w-2xl', 
                            d.images.length === 1 ? 'grid-cols-1' : d.images.length === 2 ? 'grid-cols-2' : 'grid-cols-3']">
                <div v-for="(img, idx) in d.images" :key="idx" class="rounded overflow-hidden bg-zinc-800">
                  <img 
                    :src="img + (d.images.length === 1 ? '@600w_600h.webp' : '@300w_300h_1c.webp')" 
                    class="w-full h-full object-cover hover:scale-105 transition-transform duration-500 cursor-zoom-in" 
                    referrerpolicy="no-referrer" 
                    loading="lazy"
                  />
                </div>
              </div>

              <!-- 6. 底部统计信息 -->
              <div class="mt-4 pt-4 border-t border-zinc-800/50 flex items-center gap-6 text-gray-500">
                <div class="flex items-center gap-1.5 hover:text-pink-500 cursor-pointer transition-colors">
                  <Share2 class="w-4 h-4" />
                  <span class="text-xs">{{ d.stat.forward || '转发' }}</span>
                </div>
                <div class="flex items-center gap-1.5 hover:text-pink-500 cursor-pointer transition-colors">
                  <MessageSquare class="w-4 h-4" />
                  <span class="text-xs">{{ d.stat.comment || '评论' }}</span>
                </div>
                <div class="flex items-center gap-1.5 hover:text-pink-500 cursor-pointer transition-colors">
                  <ThumbsUp class="w-4 h-4" />
                  <span class="text-xs">{{ d.stat.like || '点赞' }}</span>
                </div>
              </div>

            </div>
            
            <!-- 加载更多 -->
            <div v-if="bilibiliDynamicsHasMore" class="text-center py-4">
              <n-button 
                :loading="bilibiliDynamicsLoading" 
                @click="loadMoreDynamics"
                quaternary
              >
                加载更多
              </n-button>
            </div>
            <div v-else-if="bilibiliDynamics.length > 0" class="text-center py-4 text-gray-500 text-sm">
              没有更多了
            </div>
          </div>
          <div v-else-if="bilibiliDynamicsLoading" class="text-center py-20">
            <n-spin size="medium" />
          </div>
          <div v-else class="text-center py-20">
            <div class="text-gray-600 mb-2">暂无动态数据</div>
            <div class="text-xs text-gray-700">尝试刷新页面或检查登录状态</div>
          </div>
        </div>

        <!-- Bilibili 主页 Tab (Raw Info) -->
        <div v-if="activeTab === 'home' && isBilibili">
          <div v-if="bilibiliInfo" class="space-y-6">
            <div class="bg-zinc-900 rounded-lg p-6">
              <div class="flex flex-col md:flex-row gap-6">
                <img :src="bilibiliInfo.face" class="w-24 h-24 rounded-full" referrerpolicy="no-referrer" />
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
            <!-- B站主页展示最新几个视频 -->
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <a 
                v-for="v in bilibiliVideos.slice(0, 8)" 
                :key="v.bvid" 
                :href="'https://www.bilibili.com/video/' + v.bvid"
                target="_blank"
                class="bg-zinc-900 rounded-lg overflow-hidden group hover:ring-1 hover:ring-pink-500 transition-all"
              >
                <!-- 封面图容器 -->
                <div class="relative aspect-video">
                  <img 
                    :src="v.pic + '@320w_200h_1c.webp'" 
                    class="object-cover w-full h-full" 
                    referrerpolicy="no-referrer"
                    loading="lazy"
                  />
                  <!-- 时长悬浮窗 -->
                  <span class="absolute bottom-1 right-1 bg-black/60 text-[10px] text-white px-1 rounded">
                    {{ v.duration }}
                  </span>
                </div>
                
                <!-- 文字信息 -->
                <div class="p-2">
                  <h4 class="text-xs text-white line-clamp-2 mb-1 group-hover:text-pink-400 transition-colors">
                    {{ v.title }}
                  </h4>
                  <div class="flex justify-between items-center text-[10px] text-gray-500">
                    <span>{{ formatCount(v.play) }}播放</span>
                    <span>{{ formatPubDate(v.pubdate) }}</span>
                  </div>
                </div>
              </a>
            </div>
          </div>
          <div v-else class="text-center py-12 text-gray-500">加载中...</div>
        </div>

        <!-- YouTube 概要 (频道简介) -->
        <div v-if="activeTab === 'streams' && !isBilibili">
          <div class="bg-zinc-900 rounded-lg p-6">
            <h3 class="text-lg font-medium text-white mb-4">频道简介</h3>
            <div v-if="channel.description" class="text-gray-300 whitespace-pre-wrap text-sm leading-relaxed">{{ channel.description }}</div>
            <div v-else class="text-center py-8 text-gray-500">暂无简介</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>