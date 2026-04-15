<script setup lang="ts">
import { computed, inject, type Ref, watch } from 'vue'
import { NSpin, NEmpty } from 'naive-ui'
import { 
  ExternalLink, Share2, MessageSquare, ThumbsUp, 
  PlayCircle, Clock 
} from 'lucide-vue-next'
import { useInfiniteScroll } from '@vueuse/core'

import { useBilibiliData } from '@/composables/useBilibiliData'
import { useChannelActions } from '@/composables/useChannelActions'
import { formatCount, formatTimestamp, formatPubDate } from '@/utils/format'

interface Props {
  channelId: number
  activeTab: string
  platform: 'bilibili' | 'youtube'
}

const props = defineProps<Props>()
const emit = defineEmits(['update:activeTab'])

const {
  dynamics,
  videos,
  info,
  loading,
  hasMore,
  fetchInfo,
  fetchVideos,
  fetchDynamics,
  loadMoreDynamics,
  reset: resetBilibiliData
} = useBilibiliData()

const { addToMultiview } = useChannelActions(computed(() => null) as any)

watch(
  [() => props.channelId, () => props.activeTab],
  ([newId, newTab], [oldId, _oldTab]) => {
    if (!newId) return

    if (newId !== oldId) {
      resetBilibiliData()
    }

    if (newTab === 'videos') {
      if (videos.value.length === 0 || newId !== oldId) fetchVideos(newId)
    } else if (newTab === 'dynamics') {
      if (dynamics.value.length === 0 || newId !== oldId) fetchDynamics(newId)
    } else if (newTab === 'home') {
      if (!info.value || newId !== oldId) fetchInfo(newId)
    }
  },
  { immediate: true }
)

const mainScrollRef = inject<Ref<HTMLElement | null>>('mainScrollRef')
useInfiniteScroll(
  mainScrollRef, 
  () => {
    if (props.activeTab === 'dynamics' && hasMore.value && !loading.value) {
      loadMoreDynamics(props.channelId)
    }
  }, 
  { distance: 300 }
)

const getDynamicTypeLabel = (type: number) => {
  const map: Record<number, string> = { 1: '转发', 2: '图文', 4: '文字', 8: '视频', 64: '专栏' }
  return map[type] || '动态'
}
</script>

<template>
  <div class="bilibili-feed min-h-[400px]">

    <div v-if="loading && dynamics.length === 0 && videos.length === 0 && !info" class="flex justify-center py-20">
      <n-spin stroke="#ec4899" />
    </div>

    <!-- 1. 投稿 Tab -->
    <div v-else-if="activeTab === 'videos'">
      <div v-if="videos.length > 0" class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6 animate-in fade-in duration-500">
        <div 
          v-for="v in videos" :key="v.bvid" 
          class="group cursor-pointer bg-zinc-900/50 rounded-xl overflow-hidden hover:bg-zinc-800 transition-all border border-zinc-800/50 hover:border-pink-500/30"
          @click="addToMultiview(v.bvid, platform)"
        >
          <div class="aspect-video relative overflow-hidden bg-zinc-800">
            <img 
              :src="v.pic + '@480w_270h_1c.webp'" 
              class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" 
              referrerpolicy="no-referrer"
              loading="lazy"
            />
            <div class="absolute bottom-2 right-2 bg-black/70 text-white text-[10px] px-1.5 py-0.5 rounded backdrop-blur-sm flex items-center gap-1">
              <Clock class="w-3 h-3" /> {{ v.duration }}
            </div>
          </div>
          <div class="p-3">
            <h4 class="text-sm text-zinc-100 line-clamp-2 font-medium group-hover:text-pink-400 transition-colors h-10 leading-snug">
              {{ v.title }}
            </h4>
            <div class="flex items-center justify-between mt-3 text-[11px] text-zinc-500">
              <span class="flex items-center gap-1"><PlayCircle class="w-3 h-3" />{{ formatCount(v.play) }}</span>
              <span>{{ formatPubDate(v.pubdate) }}</span>
            </div>
          </div>
        </div>
      </div>
      <n-empty v-else description="暂无投稿内容" class="py-20" />
    </div>

    <!-- 2. 动态 Tab -->
    <div v-else-if="activeTab === 'dynamics'" class="max-w-3xl mx-auto space-y-6 animate-in slide-in-from-bottom-4 duration-500">
      <div v-for="d in dynamics" :key="d.dynamic_id" class="bg-zinc-900/40 rounded-xl p-5 border border-zinc-800/50 hover:border-zinc-700 transition-colors shadow-sm">
        <!-- 动态头部 -->
        <div class="flex items-center justify-between mb-4">
          <div class="flex items-center gap-3">
            <img :src="d.face + '@100w_100h.webp'" class="w-10 h-10 rounded-full ring-1 ring-zinc-700 object-cover" referrerpolicy="no-referrer" />
            <div>
              <div class="flex items-center gap-2">
                <span class="text-sm font-bold text-zinc-200">{{ d.uname }}</span>
                <span v-if="d.is_top" class="text-[10px] px-1.5 py-0.5 bg-pink-500/10 text-pink-500 border border-pink-500/20 rounded font-medium">置顶</span>
              </div>
              <div class="flex items-center gap-2 mt-0.5 text-[10px] text-zinc-500">
                <span class="text-pink-500/80 font-medium">{{ getDynamicTypeLabel(d.type) }}</span>
                <span>{{ formatTimestamp(d.timestamp) }}</span>
              </div>
            </div>
          </div>
          <a :href="d.url" target="_blank" class="p-2 -mr-2 text-zinc-600 hover:text-pink-500 transition-colors" title="在B站打开">
            <ExternalLink class="w-4 h-4" />
          </a>
        </div>

        <!-- 动态正文渲染 -->
        <div class="text-[14px] leading-relaxed text-zinc-300 whitespace-pre-wrap break-words">
          <template v-for="(node, idx) in d.content_nodes" :key="idx">
            <span v-if="node.type === 'text'">{{ node.text }}</span>
            <a v-else-if="node.type === 'at'" :href="'https://space.bilibili.com/' + node.rid" target="_blank" class="text-blue-400 hover:text-blue-300 transition-colors mx-0.5 font-medium">
              {{ node.text }}
            </a>
            <img v-else-if="node.type === 'emoji'" :src="node.url" class="inline-block w-5 h-5 mx-0.5 align-text-bottom" referrerpolicy="no-referrer" />
          </template>
        </div>

        <!-- 图片网格 -->
        <div v-if="d.images?.length" :class="['mt-4 grid gap-2', d.images.length === 1 ? 'grid-cols-1 max-w-md' : d.images.length === 2 ? 'grid-cols-2' : 'grid-cols-3']">
          <div v-for="(img, idx) in d.images" :key="idx" class="rounded-lg overflow-hidden bg-zinc-800 aspect-square">
            <img :src="img + '@400w_400h_1c.webp'" class="w-full h-full object-cover hover:scale-105 transition-transform duration-500 cursor-zoom-in" referrerpolicy="no-referrer" loading="lazy" />
          </div>
        </div>

        <!-- 转发卡片 (如果有) -->
        <div v-if="d.repost_content" class="mt-4 p-3 bg-zinc-950/40 rounded-lg border-l-2 border-zinc-600 italic text-[13px] text-zinc-500 leading-snug">
          {{ d.repost_content }}
        </div>

        <!-- 底部数据 -->
        <div class="mt-5 pt-4 border-t border-zinc-800/50 flex items-center gap-8 text-zinc-500">
          <div class="flex items-center gap-1.5 hover:text-pink-500 cursor-pointer transition-colors group">
            <Share2 class="w-4 h-4 group-hover:scale-110 transition-transform" /> <span class="text-xs">{{ d.stat.forward || '转发' }}</span>
          </div>
          <div class="flex items-center gap-1.5 hover:text-blue-400 cursor-pointer transition-colors group">
            <MessageSquare class="w-4 h-4 group-hover:scale-110 transition-transform" /> <span class="text-xs">{{ d.stat.comment || '评论' }}</span>
          </div>
          <div class="flex items-center gap-1.5 hover:text-red-500 cursor-pointer transition-colors group">
            <ThumbsUp class="w-4 h-4 group-hover:scale-110 transition-transform" /> <span class="text-xs">{{ d.stat.like || '点赞' }}</span>
          </div>
        </div>
      </div>

      <!-- 加载更多状态 -->
      <div class="py-8 text-center min-h-[60px]">
        <n-spin v-if="loading" size="small" stroke="#ec4899" />
        <span v-else-if="!hasMore && dynamics.length > 0" class="text-zinc-600 text-xs tracking-wider">END - 没有更多动态了</span>
      </div>
    </div>

    <!-- 3. 主页 Tab -->
    <div v-else-if="activeTab === 'home'" class="max-w-4xl mx-auto space-y-8 animate-in fade-in duration-700">
      <div v-if="info" class="bg-zinc-900/40 border border-zinc-800/50 rounded-2xl p-8 flex flex-col md:flex-row gap-8 items-center md:items-start shadow-xl">
        <img :src="info.face + '@200w_200h.webp'" class="w-24 h-24 rounded-full ring-4 ring-zinc-800/50 shadow-2xl object-cover" referrerpolicy="no-referrer" />
        <div class="flex-1 text-center md:text-left">
          <h2 class="text-2xl font-bold text-white">{{ info.name }}</h2>
          <div class="flex justify-center md:justify-start gap-8 mt-4">
            <div class="flex flex-col"><span class="text-zinc-500 text-[10px] uppercase tracking-wider mb-1">粉丝</span><span class="text-pink-500 font-bold text-xl">{{ formatCount(info.fans) }}</span></div>
            <div class="flex flex-col"><span class="text-zinc-500 text-[10px] uppercase tracking-wider mb-1">关注</span><span class="text-zinc-200 font-bold text-xl">{{ info.attention }}</span></div>
            <div class="flex flex-col"><span class="text-zinc-500 text-[10px] uppercase tracking-wider mb-1">稿件</span><span class="text-zinc-200 font-bold text-xl">{{ info.archive_count }}</span></div>
          </div>
          <p class="mt-6 text-zinc-400 text-sm leading-relaxed max-w-2xl italic border-l-2 border-zinc-800 pl-4">
            {{ info.sign || '该UP主很神秘，还没有填写简介~' }}
          </p>
        </div>
      </div>
      
      <!-- 主页推荐视频 -->
      <div v-if="videos.length">
        <h3 class="text-lg font-bold text-zinc-200 mb-6 flex items-center gap-2">
          <PlayCircle class="w-5 h-5 text-pink-500" /> 最近投稿
        </h3>
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-6">
          <div v-for="v in videos.slice(0, 4)" :key="v.bvid" class="group cursor-pointer" @click="addToMultiview(v.bvid, platform)">
            <div class="aspect-video rounded-xl overflow-hidden mb-3 bg-zinc-800 shadow-lg">
              <img :src="v.pic + '@320w_200h_1c.webp'" class="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700" referrerpolicy="no-referrer" />
            </div>
            <p class="text-xs text-zinc-300 line-clamp-2 group-hover:text-pink-400 transition-colors leading-snug">{{ v.title }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 进入动画 */
.animate-in {
  animation-duration: 0.4s;
  animation-fill-mode: both;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideInFromBottom {
  from { transform: translateY(20px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

.fade-in { animation-name: fadeIn; }
.slide-in-from-bottom-4 { animation-name: slideInFromBottom; }
</style>