<template>
  <div
    class="group relative bg-zinc-900/50 rounded-2xl overflow-hidden border border-zinc-800/50 hover:border-pink-500/50 hover:bg-zinc-800/80 transition-all duration-300 shadow-lg hover:shadow-pink-500/10"
    @click="$emit('click', stream)"
  >
    <!-- 1. 封面图区域 -->
    <div class="relative aspect-video bg-zinc-800 overflow-hidden">
      <img
        v-if="stream.thumbnail_url"
        :src="stream.thumbnail_url"
        :alt="stream.title ?? ''"
        class="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110"
        referrerpolicy="no-referrer"
        loading="lazy"
      />
      <!-- 缺省图 -->
      <div v-else class="w-full h-full flex items-center justify-center text-zinc-700">
        <PlayCircle class="w-12 h-12 opacity-20" />
      </div>

      <!-- 顶部状态标签 (毛玻璃效果) -->
      <div 
        class="absolute top-2 left-2 text-[10px] px-2 py-1 rounded-md font-bold flex items-center gap-1.5 backdrop-blur-md shadow-sm border border-white/10"
        :class="statusStyles"
      >
        <span v-if="stream.status === 'live'" class="relative flex h-2 w-2">
          <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-white opacity-75"></span>
          <span class="relative inline-flex rounded-full h-2 w-2 bg-white"></span>
        </span>
        {{ statusText }}
      </div>

      <!-- 底部右侧观看人数/时间 (毛玻璃) -->
      <div 
        v-if="stream.status === 'live'" 
        class="absolute bottom-2 right-2 bg-black/60 backdrop-blur-md text-white text-[10px] px-2 py-1 rounded-md flex items-center gap-1 border border-white/5"
      >
        <Users class="w-3 h-3" />
        {{ formatCount(stream.viewer_count) }}
      </div>
    </div>

    <!-- 2. 信息区域 -->
    <div class="p-4">
      <div class="flex items-start gap-3">
        <!-- 频道头像 -->
        <div class="relative shrink-0">
          <img
            v-if="stream.channel_avatar"
            :src="stream.channel_avatar"
            class="w-10 h-10 object-cover shadow-md border border-zinc-700/50"
            :class="stream.channel_avatar_shape === 'square' ? 'rounded-lg' : 'rounded-full'"
            referrerpolicy="no-referrer"
          />
          <div v-else class="w-10 h-10 rounded-full bg-zinc-800 flex items-center justify-center text-zinc-500 text-xs font-bold border border-zinc-700/50">
            {{ stream.channel_name?.charAt(0).toUpperCase() ?? '?' }}
          </div>
          <!-- 平台小图标 -->
          <div class="absolute -bottom-1 -right-1 rounded-full p-0.5 bg-zinc-900 border border-zinc-800">
             <component :is="platformIcon" class="w-3 h-3" :class="platformColor" />
          </div>
        </div>

        <!-- 文字信息 -->
        <div class="flex-1 min-w-0">
          <h3 class="font-bold text-zinc-100 truncate group-hover:text-pink-400 transition-colors text-sm leading-snug" :title="stream.title">
            {{ stream.title ?? '无标题' }}
          </h3>
          
          <div class="flex items-center gap-1 mt-1">
            <p class="text-[12px] text-zinc-400 truncate font-medium">
              {{ stream.channel_name ?? '未知主播' }}
            </p>
          </div>

          <!-- 额外信息标签 -->
          <div class="flex items-center gap-2 mt-2">
            <span 
              class="text-[10px] px-1.5 py-0.5 rounded-md font-bold uppercase tracking-wider"
              :class="platformTagStyles"
            >
              {{ stream.platform }}
            </span>
            <span v-if="stream.status === 'upcoming'" class="text-[10px] text-zinc-500 italic">
              {{ formatStartTime(stream.scheduled_at) }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { PlayCircle, Users, Youtube, Tv } from 'lucide-vue-next'
import type { Stream } from '@/types'
import { formatCount } from '@/utils/format'

const props = defineProps<{ stream: Stream }>()
defineEmits<{ (e: 'click', stream: Stream): void }>()

// 1. 状态文案
const statusText = computed(() => {
  const map = { live: 'LIVE', upcoming: 'UPCOMING', archive: 'RECORD', offline: 'OFFLINE' }
  return map[props.stream.status] || ''
})

// 2. 状态样式定义
const statusStyles = computed(() => {
  switch (props.stream.status) {
    case 'live': return 'bg-rose-600/80 text-white'
    case 'upcoming': return 'bg-amber-500/80 text-white'
    case 'archive': return 'bg-violet-600/80 text-white'
    default: return 'bg-zinc-700/80 text-zinc-300'
  }
})

// 3. 平台图标与颜色
const platformIcon = computed(() => props.stream.platform === 'youtube' ? Youtube : Tv)
const platformColor = computed(() => props.stream.platform === 'youtube' ? 'text-red-500' : 'text-blue-400')

const platformTagStyles = computed(() => {
  return props.stream.platform === 'youtube' 
    ? 'bg-red-500/10 text-red-500 border border-red-500/20' 
    : 'bg-blue-500/10 text-blue-500 border border-blue-500/20'
})

// 4. 辅助：格式化开始时间 (针对预约)
function formatStartTime(timeStr?: string) {
  if (!timeStr) return ''
  const date = new Date(timeStr)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) + ' 开播'
}
</script>

<style scoped>
/* 可以在这里添加一些只有该组件需要的细微动画 */
.group:hover img {
  filter: brightness(1.1);
}
</style>