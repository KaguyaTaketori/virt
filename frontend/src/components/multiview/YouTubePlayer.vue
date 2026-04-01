<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'

interface YT {
  Player: new (element: HTMLElement, options: any) => any
}

declare global {
  interface Window {
    YT?: YT
    onYouTubeIframeAPIReady?: () => void
  }
}

interface Props {
  videoId: string
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'timeUpdate', time: number): void
  (e: 'ready'): void
}>()

const containerRef = ref<HTMLDivElement | null>(null)
let ytPlayer: any = null
let timeUpdateInterval: ReturnType<typeof setInterval> | null = null

function onYouTubeIframeAPIReady() {
  if (!containerRef.value || !props.videoId || !window.YT) return

  ytPlayer = new window.YT.Player(containerRef.value, {
    videoId: props.videoId,
    playerVars: {
      autoplay: 1,
      enablejsapi: 1,
      origin: window.location.origin,
    },
    events: {
      onReady: () => {
        emit('ready')
        startTimeUpdate()
      },
      onError: (event: any) => {
        console.error('[YouTubePlayer] Error:', event.data)
      }
    }
  })
}

function startTimeUpdate() {
  if (timeUpdateInterval) {
    clearInterval(timeUpdateInterval)
  }
  timeUpdateInterval = setInterval(() => {
    if (ytPlayer && ytPlayer.getCurrentTime) {
      try {
        const currentTime = ytPlayer.getCurrentTime()
        emit('timeUpdate', currentTime)
      } catch (e) {
        console.error('[YouTubePlayer] Get time error:', e)
      }
    }
  }, 500)
}

function loadYouTubeAPI() {
  if (window.YT && window.YT.Player) {
    onYouTubeIframeAPIReady()
    return
  }

  const tag = document.createElement('script')
  tag.src = 'https://www.youtube.com/iframe_api'
  const firstScriptTag = document.getElementsByTagName('script')[0]
  if (firstScriptTag?.parentNode) {
    firstScriptTag.parentNode.insertBefore(tag, firstScriptTag)
  }

  window.onYouTubeIframeAPIReady = onYouTubeIframeAPIReady
}

onMounted(() => {
  loadYouTubeAPI()
})

onUnmounted(() => {
  if (timeUpdateInterval) {
    clearInterval(timeUpdateInterval)
  }
  if (ytPlayer) {
    ytPlayer.destroy()
  }
})

watch(() => props.videoId, (newId) => {
  if (ytPlayer && newId) {
    ytPlayer.loadVideoById(newId)
  }
})
</script>

<template>
  <div ref="containerRef" class="absolute inset-0 w-full h-full"></div>
</template>
