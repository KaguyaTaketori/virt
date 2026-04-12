<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { NPagination, NSpin, NEmpty, NTag } from 'naive-ui'
import { Play, Calendar, PlayCircle } from 'lucide-vue-next'

import { useChannelVideos } from '@/queries'
import { useChannelActions } from '@/composables/useChannelActions'
import { formatCount, formatPubDate } from '@/utils/format'

interface Props {
  channelId: number
  activeTab: string
  channelData: any 
}

const props = defineProps<Props>()

const uploadPage = ref(1)
const shortsPage = ref(1)
const livePage = ref(1)

const uploadQuery = useChannelVideos(computed(() => props.channelId), {
  page: uploadPage,
  pageSize: 24,
  status: 'upload',
  enabled: computed(() => props.activeTab === 'videos')
})

const shortsQuery = useChannelVideos(computed(() => props.channelId), {
  page: shortsPage,
  pageSize: 40,
  status: 'short',
  enabled: computed(() => props.activeTab === 'shorts')
})

const liveQuery = useChannelVideos(computed(() => props.channelId), {
  page: livePage,
  pageSize: 24,
  status: 'live,upcoming,archive',
  enabled: computed(() => props.activeTab === 'live')
})

const sortedLiveVideos = computed(() => {
  const items = [...(liveQuery.data.value?.videos || [])]
  return items.sort((a, b) => {
    const statusOrder: Record<string, number> = { live: 0, upcoming: 1, archive: 2 }
    return (statusOrder[a.status] ?? 3) - (statusOrder[b.status] ?? 3)
  })
})

const { addToMultiview } = useChannelActions(computed(() => null) as any)

watch(() => props.channelId, () => {
  uploadPage.value = 1
  shortsPage.value = 1
  livePage.value = 1
})

const isInitialLoading = (query: any) => query.isLoading.value && !query.data.value
</script>

<template>
  <div class="youtube-feed min-h-[400px]">
    
    <!-- 1. 普通视频 Tab -->
    <div v-if="activeTab === 'videos'" class="animate-in fade-in duration-500">
      <div v-if="isInitialLoading(uploadQuery)" class="flex justify-center py-20">
        <n-spin stroke="#ff0000" />
      </div>
      <template v-else-if="uploadQuery.data.value?.videos.length">
        <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-x-5 gap-y-10">
          <div 
            v-for="video in uploadQuery.data.value.videos" :key="video.id" 
            class="group cursor-pointer flex flex-col"
            @click="addToMultiview(video.id)"
          >
            <div class="aspect-video relative rounded-xl overflow-hidden bg-zinc-900 mb-3 shadow-md group-hover:shadow-red-500/10 transition-all border border-zinc-800/50 group-hover:border-red-500/30">
              <img :src="video.thumbnail_url" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" loading="lazy" />
              <span v-if="video.duration" class="absolute bottom-2 right-2 bg-black/80 text-white text-[10px] px-1.5 py-0.5 rounded font-medium backdrop-blur-sm">
                {{ video.duration }}
              </span>
            </div>
            <h4 class="text-sm font-medium text-zinc-100 line-clamp-2 leading-snug group-hover:text-red-500 transition-colors h-10">
              {{ video.title }}
            </h4>
            <div class="flex items-center gap-2 mt-3 text-[11px] text-zinc-500">
              <span>{{ formatCount(video.view_count) }} 次观看</span>
              <span class="w-1 h-1 bg-zinc-700 rounded-full"></span>
              <span>{{ video.published_at }}</span>
            </div>
          </div>
        </div>
        <div class="flex justify-center mt-12 mb-8">
          <n-pagination v-model:page="uploadPage" :page-count="uploadQuery.data.value.total_pages" />
        </div>
      </template>
      <n-empty v-else description="暂无视频" class="py-20" />
    </div>

    <!-- 2. 直播 Tab -->
    <div v-if="activeTab === 'live'" class="animate-in slide-in-from-bottom-4 duration-500">
      <div v-if="isInitialLoading(liveQuery)" class="flex justify-center py-20">
        <n-spin stroke="#ff0000" />
      </div>
      <template v-else-if="sortedLiveVideos.length">
        <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-x-5 gap-y-10">
          <div 
            v-for="video in sortedLiveVideos" :key="video.id" 
            class="group cursor-pointer"
            @click="addToMultiview(video.id)"
          >
            <div class="aspect-video relative rounded-xl overflow-hidden bg-zinc-900 mb-3 border border-zinc-800/50 group-hover:border-red-500/30 transition-all">
              <img :src="video.thumbnail_url" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
              
              <!-- 状态标签增强 -->
              <div class="absolute top-2 left-2 flex flex-col gap-1">
                <n-tag v-if="video.status === 'live'" size="small" type="error" :bordered="false" class="!font-bold shadow-lg">
                  <template #icon><span class="w-1.5 h-1.5 bg-white rounded-full animate-pulse mr-1"></span></template>
                  直播中
                </n-tag>
                <n-tag v-else-if="video.status === 'upcoming'" size="small" type="warning" :bordered="false" class="shadow-lg">
                  预约
                </n-tag>
              </div>
              
              <span v-if="video.duration" class="absolute bottom-2 right-2 bg-black/80 text-white text-[10px] px-1.5 py-0.5 rounded font-medium">
                {{ video.duration }}
              </span>
            </div>
            <h4 class="text-sm font-medium text-zinc-100 line-clamp-2 leading-snug group-hover:text-red-500 transition-colors h-10">
              {{ video.title }}
            </h4>
          </div>
        </div>
        <div class="flex justify-center mt-12 mb-8">
          <n-pagination v-model:page="livePage" :page-count="liveQuery.data.value?.total_pages" />
        </div>
      </template>
      <n-empty v-else description="暂无直播记录" class="py-20" />
    </div>

    <!-- 3. Shorts Tab (9:16) -->
    <div v-if="activeTab === 'shorts'" class="animate-in fade-in duration-500">
      <div v-if="isInitialLoading(shortsQuery)" class="flex justify-center py-20">
        <n-spin stroke="#ff0000" />
      </div>
      <template v-else-if="shortsQuery.data.value?.videos.length">
        <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-5">
          <div 
            v-for="video in shortsQuery.data.value.videos" :key="video.id" 
            class="group cursor-pointer"
            @click="addToMultiview(video.id)"
          >
            <div class="aspect-[9/16] relative rounded-2xl overflow-hidden bg-zinc-900 mb-3 border border-zinc-800/50 group-hover:border-red-500/30 transition-all shadow-sm">
              <img :src="video.thumbnail_url" class="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700" loading="lazy" />
              <div class="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-all duration-300 flex items-end p-4">
                <Play class="text-white w-8 h-8 opacity-90 scale-75 group-hover:scale-100 transition-transform" />
              </div>
            </div>
            <h4 class="text-xs font-medium text-zinc-200 line-clamp-2 leading-snug group-hover:text-red-400 transition-colors px-1">
              {{ video.title }}
            </h4>
            <p class="text-[10px] text-zinc-500 mt-2 px-1 flex items-center gap-1">
              <PlayCircle class="w-3 h-3" /> {{ formatCount(video.view_count) }}
            </p>
          </div>
        </div>
        <div class="flex justify-center mt-12 mb-8">
          <n-pagination v-model:page="shortsPage" :page-count="shortsQuery.data.value.total_pages" />
        </div>
      </template>
      <n-empty v-else description="暂无 Shorts" class="py-20" />
    </div>

    <!-- 4. 简介 Tab -->
    <div v-if="activeTab === 'streams'" class="max-w-4xl mx-auto animate-in fade-in duration-700">
      <div class="bg-zinc-900/40 border border-zinc-800/50 rounded-2xl p-8 shadow-xl">
        <h3 class="text-xl font-bold text-white mb-6 flex items-center gap-2">
           关于频道
        </h3>
        <div v-if="channelData.description" class="text-zinc-300 text-[15px] leading-loose whitespace-pre-wrap font-light tracking-wide">
          {{ channelData.description }}
        </div>
        <n-empty v-else description="该频道主没有填写详细介绍" />
        
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-8 mt-12 pt-8 border-t border-zinc-800/50">
          <div class="flex flex-col gap-2">
            <span class="text-zinc-500 text-xs uppercase tracking-widest">加入日期</span>
            <span class="text-zinc-100 font-medium flex items-center gap-2">
              <Calendar class="w-4 h-4 text-red-500" />
              {{ formatPubDate(channelData.published_at) }}
            </span>
          </div>
          <!-- 统计指标预留 -->
          <div class="flex flex-col gap-2">
            <span class="text-zinc-500 text-xs uppercase tracking-widest">平台</span>
            <span class="text-zinc-100 font-medium">YouTube</span>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<style scoped>
/* 深度修改 Naive UI 分页器样式以契合 YouTube 风格 */
:deep(.n-pagination-item--active) {
  border-color: #ff0000 !important;
  color: #ff0000 !important;
  background-color: rgba(255, 0, 0, 0.05) !important;
}

:deep(.n-pagination-item:hover) {
  color: #ff0000 !important;
}

/* 进入动画定义 */
.animate-in {
  animation-duration: 0.4s;
  animation-fill-mode: both;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideInFromBottom {
  from { transform: translateY(15px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

.fade-in { animation-name: fadeIn; }
.slide-in-from-bottom-4 { animation-name: slideInFromBottom; }
</style>