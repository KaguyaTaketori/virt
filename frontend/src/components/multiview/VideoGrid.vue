<script setup lang="ts">
import { computed, ref } from 'vue'
import { Plus, Youtube, Tv, LayoutGrid, MessageSquare } from 'lucide-vue-next'
import DanmakuOverlay from './DanmakuOverlay.vue'
import YouTubePlayer from './YouTubePlayer.vue'

interface Channel {
  platform: 'youtube' | 'bilibili'
  id: string
  danmakuEnabled?: boolean
}

interface Layout {
  name: string
  label: string
  cols: number
  cells: number
}

interface Props {
  channels: Channel[]
  selectedLayout: string
  layouts: Layout[]
  showDanmaku: boolean
  danmakuSettings?: {
    fontSize: number
    speed: number
    opacity: number
    color: string
    strokeEnabled: boolean
    strokeColor: string
    strokeWidth: number
  }
}

const props = defineProps<Props>()
const emit = defineEmits<{ 
  (e: 'requestAdd'): void
  (e: 'toggleDanmaku', channelId: string, enabled: boolean): void
}>()

const currentLayout = computed<Layout>(
  () => props.layouts.find(l => l.name === props.selectedLayout) ?? props.layouts[2]
)

const gridStyle = computed(() => ({
  gridTemplateColumns: `repeat(${currentLayout.value.cols}, 1fr)`,
}))

const emptyCellCount = computed<number>(() =>
  Math.max(0, currentLayout.value.cells - props.channels.length)
)

const videoTimes = ref<Record<string, number>>({})

function handleTimeUpdate(videoId: string, time: number) {
  videoTimes.value[videoId] = time
}

function isDanmakuEnabled(ch: Channel): boolean {
  return props.showDanmaku && ch.platform === 'youtube' && ch.danmakuEnabled !== false
}
</script>

<template>
  <!--
    flex-1    → 在 flex-col 父容器中占满剩余高度（替代 height 计算）
    min-h-0   → 允许 flex 子项收缩到低于其内容高度，防止撑破父容器
    overflow-hidden → 阻止内部格子溢出到 viewport
  -->
  <div class="flex-1 min-h-0 w-full overflow-hidden bg-zinc-950">
    <div
      v-if="channels.length > 0 || emptyCellCount > 0"
      class="grid w-full h-full gap-0.5 bg-zinc-800"
      :style="gridStyle"
    >
      <TransitionGroup
        enter-active-class="transition-all duration-300 ease-out"
        enter-from-class="opacity-0 scale-95"
        enter-to-class="opacity-100 scale-100"
        leave-active-class="transition-all duration-200 ease-in"
        leave-from-class="opacity-100 scale-100"
        leave-to-class="opacity-0 scale-95"
      >
        <div
          v-for="ch in channels"
          :key="ch.id"
          class="relative bg-zinc-950 overflow-hidden group"
        >
          <YouTubePlayer
            v-if="ch.platform === 'youtube'"
            :video-id="ch.id"
            @time-update="(time) => handleTimeUpdate(ch.id, time)"
          />
          <template v-else-if="ch.platform === 'bilibili'">
            <iframe
              v-if="ch.id.startsWith('BV')"
              :src="`https://player.bilibili.com/player.html?bvid=${ch.id}&autoplay=1`"
              class="absolute inset-0 w-full h-full"
              frameborder="0"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowfullscreen
            />
            <iframe
              v-else
              :src="`https://www.bilibili.com/blackboard/live/live-activity-player.html?cid=${ch.id}&quality=0`"
              class="absolute inset-0 w-full h-full"
              frameborder="0"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowfullscreen
            />
          </template>
          <DanmakuOverlay
            v-if="isDanmakuEnabled(ch)"
            :video-id="ch.id"
            :platform="ch.platform"
            :enabled="isDanmakuEnabled(ch)"
            :settings="danmakuSettings"
            :current-time="videoTimes[ch.id] || 0"
          />
          <div
            class="absolute bottom-0 left-0 right-0 px-3 py-2
                   bg-gradient-to-t from-black/80 to-transparent
                   opacity-0 group-hover:opacity-100 transition-opacity duration-200
                   flex items-center justify-between pointer-events-none"
          >
            <div class="flex items-center gap-1.5">
              <component
                :is="ch.platform === 'youtube' ? Youtube : Tv"
                class="w-3 h-3 shrink-0"
                :class="ch.platform === 'youtube' ? 'text-red-400' : 'text-blue-400'"
              />
              <span class="text-white text-xs font-mono opacity-80 truncate">{{ ch.id }}</span>
            </div>
            <button
              v-if="ch.platform === 'youtube' && showDanmaku"
              class="pointer-events-auto p-1 rounded hover:bg-white/20 transition-colors"
              :class="ch.danmakuEnabled !== false ? 'text-green-400' : 'text-zinc-500'"
              @click.stop="emit('toggleDanmaku', ch.id, ch.danmakuEnabled === false)"
              title="弹幕开关"
            >
              <MessageSquare class="w-4 h-4" />
            </button>
          </div>
        </div>
      </TransitionGroup>

      <button
        v-for="n in emptyCellCount"
        :key="`empty-${n}`"
        @click="emit('requestAdd')"
        class="relative bg-zinc-950 border border-dashed border-zinc-800
               hover:border-zinc-600 hover:bg-zinc-900/50 transition-colors duration-200
               flex flex-col items-center justify-center gap-2
               text-zinc-700 hover:text-zinc-500 group"
      >
        <div
          class="w-10 h-10 rounded-full border border-dashed border-zinc-700
                 group-hover:border-zinc-500 flex items-center justify-center transition-colors"
        >
          <Plus class="w-4 h-4" />
        </div>
        <span class="text-xs">添加视频</span>
      </button>
    </div>

    <div
      v-else
      class="w-full h-full flex flex-col items-center justify-center gap-3 text-zinc-700"
    >
      <LayoutGrid class="w-12 h-12 opacity-20" />
      <p class="text-sm">点击「添加」开始多窗观看</p>
    </div>
  </div>
</template>