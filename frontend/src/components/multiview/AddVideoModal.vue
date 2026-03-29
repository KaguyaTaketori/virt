<script setup lang="ts">
import { ref, watch } from 'vue'
import { X, Youtube, Tv } from 'lucide-vue-next'

interface Props {
  modelValue: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'update:modelValue', val: boolean): void
  (e: 'add', channel: { platform: 'youtube' | 'bilibili'; id: string }): void
}>()

const platform = ref<'youtube' | 'bilibili'>('youtube')
const videoId = ref('')
const error = ref('')

// Reset on open
watch(() => props.modelValue, (val) => {
  if (val) {
    platform.value = 'youtube'
    videoId.value = ''
    error.value = ''
  }
})

function close() {
  emit('update:modelValue', false)
}

function parseYouTubeId(input: string): string {
  try {
    const url = new URL(input)
    if (url.hostname.includes('youtube.com')) return url.searchParams.get('v') ?? input
    if (url.hostname.includes('youtu.be')) return url.pathname.slice(1)
  } catch {
    return input
  }
  return input
}

function submit() {
  const raw = videoId.value.trim()
  if (!raw) {
    error.value = '请输入房间号或 Video ID'
    return
  }
  const id = platform.value === 'youtube' ? parseYouTubeId(raw) : raw
  if (!id) {
    error.value = '无法解析 Video ID，请直接输入 ID'
    return
  }
  emit('add', { platform: platform.value, id })
  close()
}

function handleKey(e: KeyboardEvent) {
  if (e.key === 'Enter') submit()
  if (e.key === 'Escape') close()
}
</script>

<template>
  <!-- Backdrop -->
  <Transition
    enter-active-class="transition-opacity duration-250 ease-out"
    enter-from-class="opacity-0"
    enter-to-class="opacity-100"
    leave-active-class="transition-opacity duration-200 ease-in"
    leave-from-class="opacity-100"
    leave-to-class="opacity-0"
  >
    <div
      v-if="modelValue"
      class="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center px-4"
      @click.self="close"
    >
      <!-- Panel -->
      <Transition
        appear
        enter-active-class="transition-all duration-250 ease-out"
        enter-from-class="opacity-0 scale-95 translate-y-2"
        enter-to-class="opacity-100 scale-100 translate-y-0"
        leave-active-class="transition-all duration-150 ease-in"
        leave-from-class="opacity-100 scale-100"
        leave-to-class="opacity-0 scale-95"
      >
        <div
          v-if="modelValue"
          class="w-full max-w-md bg-zinc-900 border border-zinc-700 rounded-xl shadow-2xl
                 shadow-black/60 overflow-hidden"
          @keydown="handleKey"
        >
          <!-- Header -->
          <div class="flex items-center justify-between px-5 py-4 border-b border-zinc-800">
            <div>
              <h2 class="text-white font-semibold text-sm">添加直播窗</h2>
              <p class="text-zinc-500 text-xs mt-0.5">输入 Video ID 或完整链接</p>
            </div>
            <button
              @click="close"
              class="p-1.5 rounded-lg text-zinc-500 hover:text-white hover:bg-zinc-800 transition-colors"
            >
              <X class="w-4 h-4" />
            </button>
          </div>

          <!-- Body -->
          <div class="px-5 py-5 space-y-4">
            <!-- Platform Selector -->
            <div class="flex gap-2">
              <button
                v-for="p in (['youtube', 'bilibili'] as const)"
                :key="p"
                @click="platform = p; error = ''"
                class="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg
                       border text-sm font-medium transition-all"
                :class="platform === p
                  ? p === 'youtube'
                    ? 'bg-red-500/10 border-red-500/50 text-red-400'
                    : 'bg-blue-500/10 border-blue-500/50 text-blue-400'
                  : 'border-zinc-700 text-zinc-500 hover:border-zinc-600 hover:text-zinc-300'"
              >
                <component :is="p === 'youtube' ? Youtube : Tv" class="w-4 h-4" />
                <span>{{ p === 'youtube' ? 'YouTube' : 'Bilibili' }}</span>
              </button>
            </div>

            <!-- ID Input -->
            <div>
              <label class="block text-zinc-400 text-xs mb-1.5 font-medium">
                {{ platform === 'youtube' ? 'Video ID 或 YouTube 链接' : 'Bilibili 直播间 ID' }}
              </label>
              <input
                v-model="videoId"
                :placeholder="platform === 'youtube' ? 'dQw4w9WgXcQ 或 https://youtube.com/watch?v=...' : '12345678'"
                @input="error = ''"
                class="w-full bg-zinc-800 border rounded-lg px-3 py-2.5 text-sm text-white
                       placeholder-zinc-600 outline-none transition-colors font-mono
                       focus:ring-1"
                :class="error
                  ? 'border-red-500/60 focus:ring-red-500/40'
                  : 'border-zinc-700 focus:border-zinc-500 focus:ring-zinc-500/30'"
                autofocus
              />
              <Transition
                enter-active-class="transition-all duration-200"
                enter-from-class="opacity-0 -translate-y-1"
                enter-to-class="opacity-100 translate-y-0"
              >
                <p v-if="error" class="text-red-400 text-xs mt-1.5">{{ error }}</p>
              </Transition>
            </div>
          </div>

          <!-- Footer -->
          <div class="flex items-center justify-end gap-2 px-5 py-4 border-t border-zinc-800">
            <button
              @click="close"
              class="px-4 py-2 rounded-lg text-sm text-zinc-400 hover:text-white
                     hover:bg-zinc-800 transition-colors"
            >
              取消
            </button>
            <button
              @click="submit"
              class="px-4 py-2 rounded-lg text-sm font-medium bg-rose-600 hover:bg-rose-500
                     text-white transition-colors"
            >
              确认添加
            </button>
          </div>
        </div>
      </Transition>
    </div>
  </Transition>
</template>