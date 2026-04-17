<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { loadYouTubeIframeAPI, YTPlayer } from '@/utils/youtube-loader'

interface Props {
  videoId: string
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'timeUpdate', time: number): void
  (e: 'ready'): void
}>()

const containerRef = ref<HTMLDivElement | null>(null)
let ytPlayer: YTPlayer | null = null 
let timeUpdateInterval: ReturnType<typeof setInterval> | null = null

async function initPlayer() {
  try {
    // 等待全局 API 加载完成
    await loadYouTubeIframeAPI()

    if (!containerRef.value || !props.videoId || !window.YT) return

    // 如果播放器实例已存在，先销毁（防止内存泄露）
    if (ytPlayer) {
      destroyPlayer()
    }

    ytPlayer = new window.YT.Player(containerRef.value, {
      videoId: props.videoId,
      playerVars: {
        autoplay: 1,
        enablejsapi: 1,
        origin: window.location.origin,
        rel: 0, // 不显示相关视频
      },
      events: {
        onReady: () => {
          emit('ready')
          startTimeUpdate()
        },
        onStateChange: (event: any) => {
          // 可以在这里处理播放/暂停状态同步
        },
        onError: (event: any) => {
          console.error('[YouTubePlayer] Player Error:', event.data)
        }
      }
    })
  } catch (error) {
    console.error('[YouTubePlayer] Failed to load YouTube API:', error)
  }
}

function startTimeUpdate() {
  stopTimeUpdate()
  timeUpdateInterval = setInterval(() => {
    if (ytPlayer && typeof ytPlayer.getCurrentTime === 'function') {
      try {
        const currentTime = ytPlayer.getCurrentTime()
        emit('timeUpdate', currentTime)
      } catch (e) {
        // 忽略在销毁瞬间可能产生的错误
      }
    }
  }, 500)
}

function stopTimeUpdate() {
  if (timeUpdateInterval) {
    clearInterval(timeUpdateInterval)
    timeUpdateInterval = null
  }
}

function destroyPlayer() {
  stopTimeUpdate()
  if (ytPlayer) {
    try {
      ytPlayer.destroy()
    } catch (e) {
      console.warn('[YouTubePlayer] Destroy error:', e)
    }
    ytPlayer = null
  }
}

onMounted(() => {
  initPlayer()
})

onUnmounted(() => {
  destroyPlayer()
})

// 监听 ID 变化：如果 ID 变了，直接使用现有实例切歌，比销毁重建更快
watch(() => props.videoId, (newId) => {
  if (ytPlayer && typeof ytPlayer.loadVideoById === 'function' && newId) {
    ytPlayer.loadVideoById(newId)
  } else {
    initPlayer() // 如果实例还没好，走初始化逻辑
  }
})
</script>

<template>
  <div ref="containerRef" class="absolute inset-0 w-full h-full"></div>
</template>