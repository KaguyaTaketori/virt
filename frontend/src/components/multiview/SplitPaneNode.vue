<script setup lang="ts">
import { inject, ref } from 'vue'
import { LayoutNode } from '@/utils/layoutEngine'
import { Plus, Youtube, Tv, Eraser, X, GripHorizontal, MessageSquare} from 'lucide-vue-next'
import YouTubePlayer from './YouTubePlayer.vue'
import DanmakuOverlay from './DanmakuOverlay.vue'
import { useAuthStore } from '@/stores/auth'
// 注意引入 naive-ui 的 n-split
import { NSplit } from 'naive-ui'

const authStore = useAuthStore() 

const props = defineProps<{ node: LayoutNode }>()

const emit = defineEmits<{
  (e: 'clear', id: string): void
  (e: 'close', id: string): void
  (e: 'requestReplace', id: string): void
}>()

const currentTime = ref(0)
const handleTimeUpdate = (time: number) => {
  currentTime.value = time
}

// 全局状态注入
const showDanmaku = inject('showDanmaku') as { value: boolean }
const danmakuSettings = inject('danmakuSettings') as any
const onDragStartGlobal = inject('onDragStart') as (e: DragEvent, id: string) => void
const onDropGlobal = inject('onDrop') as (id: string) => void
const toggleDanmaku = inject('toggleDanmaku') as (id: string, enabled: boolean) => void

function isDanmakuEnabled(ch: any): boolean {
  return showDanmaku.value && ch.platform === 'youtube' && ch.danmakuEnabled !== false
}
</script>

<template>
  <div class="w-full h-full">
    <n-split
      v-if="node.type === 'split'"
      :direction="node.direction"
      v-model:size="node.ratio"
      :min="0.1"
      :max="0.9"
      class="w-full h-full"
    >
      <template #1>
        <SplitPaneNode :node="node.children![0]" @clear="emit('clear', $event)" @close="emit('close', $event)" @requestReplace="emit('requestReplace', $event)" />
      </template>
      <template #2>
        <SplitPaneNode :node="node.children![1]" @clear="emit('clear', $event)" @close="emit('close', $event)" @requestReplace="emit('requestReplace', $event)" />
      </template>
    </n-split>

    <div
      v-else-if="node.type === 'leaf' && node.channel"
      class="relative w-full h-full bg-zinc-950 overflow-hidden group"
      draggable="true"
      @dragstart="onDragStartGlobal($event, node.id)"
      @dragover.prevent
      @dragenter.prevent
      @drop="onDropGlobal(node.id)"
    >
      <!-- 空位状态 -->
      <div v-if="node.channel.platform === 'empty'" class="w-full h-full flex flex-col items-center justify-center bg-zinc-900/50 hover:bg-zinc-800 transition-colors cursor-pointer" @click="emit('requestReplace', node.id)">
        <Plus class="w-8 h-8 mb-2 text-zinc-600" />
        <span class="text-xs text-zinc-500">点击添加视频，或拖拽视频至此</span>
      </div>

      <!-- 视频播放器 -->
      <template v-else>
        <YouTubePlayer v-if="node.channel.platform === 'youtube'" :video-id="node.channel.id" @time-update="handleTimeUpdate" :key="node.channel.id"/>
        <template v-else-if="node.channel.platform === 'bilibili' && authStore.canAccessBilibili">
          <iframe v-if="node.channel.id.startsWith('BV')" :src="`https://player.bilibili.com/player.html?bvid=${node.channel.id}&autoplay=1`" class="absolute inset-0 w-full h-full" frameborder="0" allowfullscreen />
          <iframe v-else :src="`https://www.bilibili.com/blackboard/live/live-activity-player.html?cid=${node.channel.id}&quality=0`" class="absolute inset-0 w-full h-full" frameborder="0" allowfullscreen />
        </template>
        <div v-else-if="node.channel.platform === 'bilibili'" class="absolute inset-0 flex items-center justify-center bg-zinc-900 text-zinc-500">
          无B站访问权限
        </div>
        
        <DanmakuOverlay v-if="isDanmakuEnabled(node.channel)" :video-id="node.channel.id" :platform="node.channel.platform" :enabled="true" :settings="danmakuSettings" :current-time="currentTime" />
      </template>

      <!-- 顶部拖拽手柄 -->
      <div class="absolute top-0 left-0 right-0 h-8 bg-gradient-to-b from-black/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none flex justify-center pt-1 z-20">
        <GripHorizontal class="w-5 h-5 text-white/50 cursor-grab active:cursor-grabbing pointer-events-auto" />
      </div>

      <!-- 底部控制栏 -->
      <div class="absolute bottom-0 left-0 right-0 px-3 py-2 bg-gradient-to-t from-black/90 via-black/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-center justify-between pointer-events-none z-20">
        <div class="flex items-center gap-1.5">
          <template v-if="node.channel.platform !== 'empty'">
            <component :is="node.channel.platform === 'youtube' ? Youtube : Tv" class="w-3 h-3 shrink-0" :class="node.channel.platform === 'youtube' ? 'text-red-400' : 'text-blue-400'" />
            <span class="text-white text-xs font-mono opacity-80 truncate max-w-[100px]">{{ node.channel.id }}</span>
          </template>
        </div>

        <div class="flex items-center gap-1 pointer-events-auto">
          <button v-if="node.channel.platform === 'youtube'" @click.stop="toggleDanmaku(node.channel.id, node.channel.danmakuEnabled === false)" class="p-1.5 rounded hover:bg-white/20 transition-colors text-green-400" title="弹幕开关">
            <MessageSquare class="w-3.5 h-3.5" />
          </button>
          <template v-if="node.channel.platform !== 'empty'">
            <div class="w-px h-4 bg-zinc-600 mx-1"></div>
            <!-- 清空按钮保留占位符 -->
            <button @click.stop="emit('clear', node.id)" class="p-1.5 rounded text-zinc-300 hover:text-yellow-400 hover:bg-white/20" title="清空并保留网格">
              <Eraser class="w-3.5 h-3.5" />
            </button>
          </template>
          <!-- 彻底关闭并吞并 -->
          <button @click.stop="emit('close', node.id)" class="p-1.5 rounded text-zinc-300 hover:text-red-500 hover:bg-white/20 ml-1" title="彻底关闭">
            <X class="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>