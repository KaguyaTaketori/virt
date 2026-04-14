<script setup lang="ts">
import { ref, watch, onUnmounted } from 'vue'
import { useScriptTag, useIntervalFn } from '@vueuse/core'

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

const { pause, resume } = useIntervalFn(() => {
  if (ytPlayer?.getCurrentTime) {
    try {
      emit('timeUpdate', ytPlayer.getCurrentTime())
    } catch (e) {
      console.error('[YouTubePlayer] Get time error:', e)
    }
  }
}, 500, { immediate: false })

function initPlayer() {
  if (!containerRef.value || !props.videoId || !window.YT) return

  if (ytPlayer) {
    ytPlayer.loadVideoById(props.videoId)
    return
  }

  ytPlayer = new window.YT.Player(containerRef.value, {
    width: '100%',
    height: '100%',
    videoId: props.videoId,
    playerVars: {
      autoplay: 1,
      enablejsapi: 1,
      origin: window.location.origin,
      rel: 0,
      modestbranding: 1
    },
    events: {
      onReady: () => {
        emit('ready')
        resume()
      },
      onStateChange: (event: any) => {
        if (event.data === 1) resume()
        else pause()
      },
      onError: (event: any) => {
        console.error('[YouTubePlayer] Error:', event.data)
      }
    }
  })
}

useScriptTag(
  'https://www.youtube.com/iframe_api',
  () => {
    if (window.YT && window.YT.Player) {
      initPlayer()
    } else {
      window.onYouTubeIframeAPIReady = initPlayer
    }
  }
)

watch(() => props.videoId, (newId) => {
  if (ytPlayer?.loadVideoById && newId) {
    ytPlayer.loadVideoById(newId)
  }
})

onUnmounted(() => {
  if (ytPlayer?.destroy) {
    ytPlayer.destroy()
  }
})
</script>

<template>
  <div class="absolute inset-0 w-full h-full bg-black overflow-hidden">
    <div ref="containerRef" class="w-full h-full"></div>
  </div>
</template>

<style scoped>
:deep(iframe) {
  width: 100% !important;
  height: 100% !important;
  display: block;
}
</style>