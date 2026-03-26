<!-- frontend/src/components/StreamCard.vue ← 完整替换 -->
<template>
  <div
    class="bg-gray-800 rounded-lg overflow-hidden cursor-pointer hover:ring-2 hover:ring-pink-500 transition transform hover:-translate-y-1"
    @click="$emit('click', stream)"
  >
    <!-- 缩略图区域 -->
    <div class="relative aspect-video bg-gray-900">
      <img
        v-if="stream.thumbnail_url"
        :src="stream.thumbnail_url"
        :alt="stream.title ?? ''"
        class="w-full h-full object-cover"
      />
      <div v-else class="w-full h-full flex items-center justify-center text-gray-600">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
        </svg>
      </div>

      <!-- LIVE 角标 -->
      <div class="absolute top-2 left-2 bg-red-600 text-white text-xs px-2 py-1 rounded font-bold animate-pulse">
        LIVE
      </div>

      <!-- 观看人数 -->
      <div class="absolute bottom-2 right-2 bg-black/70 text-white text-xs px-2 py-1 rounded flex items-center gap-1">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
          <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
          <path fill-rule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clip-rule="evenodd" />
        </svg>
        {{ formatViewerCount(stream.viewer_count) }}
      </div>
    </div>

    <!-- 信息区域 -->
    <div class="p-4">
      <div class="flex items-start gap-3">
        <!-- 频道头像 -->
        <img
          v-if="stream.channel_avatar"
          :src="stream.channel_avatar"
          :alt="stream.channel_name ?? ''"
          class="w-10 h-10 rounded-full object-cover bg-gray-700 flex-shrink-0"
        />
        <div v-else class="w-10 h-10 rounded-full bg-gray-700 flex items-center justify-center text-gray-400 text-sm font-bold flex-shrink-0">
          {{ stream.channel_name?.charAt(0).toUpperCase() ?? '?' }}
        </div>

        <div class="flex-1 min-w-0">
          <!-- 标题 -->
          <h3 class="font-semibold text-gray-100 truncate hover:text-pink-400 transition text-sm">
            {{ stream.title ?? '无标题' }}
          </h3>
          <!-- 频道名 -->
          <p class="text-xs text-gray-400 truncate mt-1">
            {{ stream.channel_name ?? '未知主播' }}
          </p>
          <!-- 平台标签 -->
          <div class="flex items-center gap-2 mt-2">
            <span
              class="text-xs px-2 py-0.5 rounded font-medium"
              :class="stream.platform === 'youtube'
                ? 'bg-red-600/20 text-red-400'
                : 'bg-blue-600/20 text-blue-400'"
            >
              {{ stream.platform === 'youtube' ? 'YouTube' : 'Bilibili' }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Stream } from '../stores/stream'

defineProps<{ stream: Stream }>()
defineEmits<{ (e: 'click', stream: Stream): void }>()

function formatViewerCount(count: number | null | undefined): string {
  if (!count) return '0'
  if (count >= 10000) return (count / 10000).toFixed(1) + '万'
  if (count >= 1000) return (count / 1000).toFixed(1) + 'k'
  return count.toString()
}
</script>