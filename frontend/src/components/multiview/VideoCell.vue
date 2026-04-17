<script setup lang="ts">
import { ref, computed } from 'vue'
import { type GridItem } from '@/types/multiview'
import { Plus, Youtube, Tv, Eraser, X, GripHorizontal, MessageSquare } from 'lucide-vue-next'
import YouTubePlayer from './YouTubePlayer.vue'
import DanmakuOverlay from './DanmakuOverlay.vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

const props = defineProps<{
  item: GridItem
  showDanmaku: boolean
  danmakuSettings: any
}>()

const emit = defineEmits<{
  (e: 'clear', id: string): void
  (e: 'close', id: string): void
  (e: 'requestReplace', id: string): void
  (e: 'toggleDanmaku', nodeId: string): void
}>()

const currentTime = ref(0)
const handleTimeUpdate = (time: number) => {
  currentTime.value = time
}

const isDanmakuEnabled = computed(() => {
  return props.showDanmaku && 
         props.item.channel.platform === 'youtube' && 
         props.item.channel.danmakuEnabled !== false
})

const isDanmakuActive = computed(() => {
  return props.item.channel.danmakuEnabled !== false
})
</script>

<template>
  <div class="relative w-full h-full bg-zinc-950 overflow-hidden group">
    <div 
      v-if="item.channel.platform === 'empty'" 
      class="w-full h-full flex flex-col items-center justify-center bg-zinc-900/50 hover:bg-zinc-800 transition-colors cursor-pointer"
      @click="emit('requestReplace', item.id)"
    >
      <Plus class="w-8 h-8 mb-2 text-zinc-600" />
      <span class="text-xs text-zinc-500">点击添加视频，或拖拽视频至此</span>
    </div>

    <template v-else>
      <YouTubePlayer 
        v-if="item.channel.platform === 'youtube'" 
        :video-id="item.channel.id" 
        @time-update="handleTimeUpdate" 
        :key="item.channel.id"
      />
      <template v-else-if="item.channel.platform === 'bilibili' && authStore.canAccessBilibili">
        <iframe 
          v-if="item.channel.id.startsWith('BV')" 
          :src="`https://player.bilibili.com/player.html?bvid=${item.channel.id}&autoplay=1`" 
          class="absolute inset-0 w-full h-full" 
          frameborder="0" 
          allowfullscreen 
        />
        <iframe 
          v-else 
          :src="`https://www.bilibili.com/blackboard/live/live-activity-player.html?cid=${item.channel.id}&quality=0`" 
          class="absolute inset-0 w-full h-full" 
          frameborder="0" 
          allowfullscreen 
        />
      </template>
      <div 
        v-else-if="item.channel.platform === 'bilibili'" 
        class="absolute inset-0 flex items-center justify-center bg-zinc-900 text-zinc-500"
      >
        无B站访问权限
      </div>
      
      <DanmakuOverlay 
        v-if="isDanmakuEnabled" 
        :video-id="item.channel.id" 
        :platform="item.channel.platform" 
        :enabled="item.channel.danmakuEnabled !== false" 
        :settings="danmakuSettings" 
        :current-time="currentTime" 
      />
    </template>

    <div class="absolute top-0 left-0 right-0 h-8 bg-gradient-to-b from-black/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none flex justify-center pt-1 z-20">
      <div class="drag-handle p-1 cursor-grab active:cursor-grabbing hover:bg-white/10 rounded-md pointer-events-auto">
        <GripHorizontal class="w-5 h-5 text-white/70" />
      </div>
    </div>

    <div class="absolute bottom-0 left-0 right-0 px-3 py-2 bg-gradient-to-t from-black/90 via-black/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-center justify-between pointer-events-none z-20">
      <div class="flex items-center gap-1.5">
        <template v-if="item.channel.platform !== 'empty'">
          <component 
            :is="item.channel.platform === 'youtube' ? Youtube : Tv" 
            class="w-3 h-3 shrink-0" 
            :class="item.channel.platform === 'youtube' ? 'text-red-400' : 'text-blue-400'" 
          />
          <span class="text-white text-xs font-mono opacity-80 truncate max-w-[100px]">{{ item.channel.id }}</span>
        </template>
      </div>

      <div class="flex items-center gap-1 pointer-events-auto">
        <button 
          v-if="item.channel.platform === 'youtube'" 
          @click.stop="emit('toggleDanmaku', item.id)" 
          :class="isDanmakuActive ? 'text-green-400' : 'text-zinc-500'"
          :title="isDanmakuActive ? '关闭此窗弹幕' : '开启此窗弹幕'"
        >
          <MessageSquare class="w-3.5 h-3.5" />
        </button>
        <template v-if="item.channel.platform !== 'empty'">
          <div class="w-px h-4 bg-zinc-600 mx-1"></div>
          <button 
            @click.stop="emit('clear', item.id)" 
            class="p-1.5 rounded text-zinc-300 hover:text-yellow-400 hover:bg-white/20" 
            title="清空并保留网格"
          >
            <Eraser class="w-3.5 h-3.5" />
          </button>
        </template>
        <button 
          @click.stop="emit('close', item.id)" 
          class="p-1.5 rounded text-zinc-300 hover:text-red-500 hover:bg-white/20 ml-1" 
          title="彻底关闭"
        >
          <X class="w-4 h-4" />
        </button>
      </div>
    </div>
  </div>
</template>