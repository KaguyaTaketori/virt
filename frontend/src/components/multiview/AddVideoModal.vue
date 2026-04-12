<script setup lang="ts">
import { ref, watch, nextTick, useTemplateRef } from 'vue'
import { X, Youtube, Tv, Link, AlertCircle } from 'lucide-vue-next'

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
const inputRef = useTemplateRef<HTMLInputElement>('inputRef')

// 1. 自动聚焦逻辑
watch(() => props.modelValue, async (val) => {
  if (val) {
    platform.value = 'youtube'
    videoId.value = ''
    error.value = ''
    // 确保 DOM 渲染后聚焦
    await nextTick()
    inputRef.value?.focus()
  }
})

// 2. 增强型解析逻辑
function parseYouTubeId(input: string): string {
  const raw = input.trim()
  try {
    // 匹配常见的 YouTube 各种格式 (v=, shorts/, live/, youtu.be/)
    const youtubeRegex = /(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?|shorts|live)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})/
    const match = raw.match(youtubeRegex)
    return match ? match[1] : raw
  } catch {
    return raw
  }
}

function parseBilibiliId(input: string): string {
  const raw = input.trim()
  // 匹配 live.bilibili.com/数字
  const biliRegex = /live\.bilibili\.com\/(\d+)/
  const match = raw.match(biliRegex)
  return match ? match[1] : raw
}

function close() {
  emit('update:modelValue', false)
}

function submit() {
  const raw = videoId.value.trim()
  if (!raw) {
    error.value = '请填写房间号、ID 或完整链接'
    return
  }

  let finalId = ''
  if (platform.value === 'youtube') {
    finalId = parseYouTubeId(raw)
    // 校验 YouTube ID 长度通常为 11 位
    if (finalId.length < 5) {
      error.value = '无效的 YouTube ID'
      return
    }
  } else {
    finalId = parseBilibiliId(raw)
    // 校验 B站 ID 是否为纯数字
    if (!/^\d+$/.test(finalId)) {
      error.value = 'B站直播间号必须为纯数字'
      return
    }
  }

  emit('add', { platform: platform.value, id: finalId })
  close()
}

function handleKey(e: KeyboardEvent) {
  if (e.key === 'Enter') submit()
  if (e.key === 'Escape') close()
}
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition-all duration-300 ease-out"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition-all duration-200 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="modelValue"
        class="fixed inset-0 bg-black/80 backdrop-blur-md z-[100] flex items-center justify-center px-4"
        @click.self="close"
      >
        <Transition
          appear
          enter-active-class="transition-all duration-300 cubic-bezier(0.34, 1.56, 0.64, 1)"
          enter-from-class="opacity-0 scale-90 translate-y-4"
          enter-to-class="opacity-100 scale-100 translate-y-0"
          leave-active-class="transition-all duration-200 ease-in"
          leave-from-class="opacity-100 scale-100"
          leave-to-class="opacity-0 scale-95"
        >
          <div
            v-if="modelValue"
            class="w-full max-w-md bg-zinc-900 border border-zinc-800 rounded-2xl shadow-[0_32px_64px_-12px_rgba(0,0,0,0.6)] overflow-hidden"
            role="dialog"
            aria-modal="true"
            @keydown="handleKey"
          >
            <!-- 头部 -->
            <div class="px-6 py-5 border-b border-zinc-800 flex items-center justify-between bg-zinc-900/50">
              <div class="flex items-center gap-3">
                <div class="p-2 bg-rose-500/10 rounded-lg">
                  <Link class="w-5 h-5 text-rose-500" />
                </div>
                <div>
                  <h2 class="text-zinc-100 font-bold text-base leading-none">添加直播窗</h2>
                  <p class="text-zinc-500 text-[11px] mt-1.5 font-medium uppercase tracking-wider">Add New Source</p>
                </div>
              </div>
              <button
                @click="close"
                class="p-2 rounded-xl text-zinc-500 hover:text-white hover:bg-zinc-800 transition-all active:scale-90"
              >
                <X class="w-5 h-5" />
              </button>
            </div>

            <!-- 主体 -->
            <div class="p-6 space-y-6">
              <!-- 平台选择 -->
              <div class="grid grid-cols-2 gap-3">
                <button
                  v-for="p in (['youtube', 'bilibili'] as const)"
                  :key="p"
                  @click="platform = p; error = ''"
                  class="relative flex flex-col items-center gap-2 py-4 rounded-xl border-2 transition-all duration-300 group"
                  :class="platform === p
                    ? p === 'youtube'
                      ? 'bg-red-500/5 border-red-600/50 text-red-500 shadow-[0_0_20px_rgba(220,38,38,0.1)]'
                      : 'bg-blue-500/5 border-blue-600/50 text-blue-500 shadow-[0_0_20px_rgba(37,99,235,0.1)]'
                    : 'bg-zinc-800/50 border-zinc-800 text-zinc-500 hover:border-zinc-700 hover:text-zinc-300'"
                >
                  <component :is="p === 'youtube' ? Youtube : Tv" class="w-6 h-6 transition-transform group-hover:scale-110" />
                  <span class="text-xs font-bold uppercase tracking-widest">{{ p }}</span>
                  <!-- 选中指示器 -->
                  <div v-if="platform === p" class="absolute top-2 right-2 w-1.5 h-1.5 rounded-full" :class="p === 'youtube' ? 'bg-red-500' : 'bg-blue-500'"></div>
                </button>
              </div>

              <!-- 输入框 -->
              <div class="space-y-2">
                <div class="flex items-center justify-between px-1">
                  <label class="text-[11px] font-bold text-zinc-500 uppercase tracking-widest">
                    {{ platform === 'youtube' ? 'Source ID / URL' : 'Room ID / URL' }}
                  </label>
                  <span v-if="error" class="text-[10px] font-bold text-red-500 flex items-center gap-1 animate-pulse">
                    <AlertCircle class="w-3 h-3" /> {{ error }}
                  </span>
                </div>
                
                <div class="relative group">
                  <input
                    ref="inputRef"
                    v-model="videoId"
                    :placeholder="platform === 'youtube' ? '输入视频 ID 或链接...' : '输入直播间号或链接...'"
                    @input="error = ''"
                    class="w-full bg-zinc-950 border-2 rounded-xl px-4 py-3.5 text-sm text-white
                           placeholder-zinc-700 outline-none transition-all font-mono"
                    :class="error
                      ? 'border-red-600/50'
                      : platform === 'youtube' 
                        ? 'border-zinc-800 focus:border-red-600/30' 
                        : 'border-zinc-800 focus:border-blue-600/30'"
                  />
                </div>
                <p class="text-[10px] text-zinc-600 px-1 italic">
                  支持直接粘贴地址栏 URL，系统将自动提取 ID。
                </p>
              </div>
            </div>

            <!-- 底部操作 -->
            <div class="px-6 py-5 bg-zinc-900/80 border-t border-zinc-800 flex items-center gap-3">
              <button
                @click="close"
                class="flex-1 py-3 rounded-xl text-sm font-bold text-zinc-500 hover:text-zinc-200 
                       hover:bg-zinc-800 transition-all active:scale-95"
              >
                取消
              </button>
              <button
                @click="submit"
                class="flex-[2] py-3 rounded-xl text-sm font-bold text-white transition-all 
                       active:scale-95 shadow-lg shadow-rose-900/20"
                :class="platform === 'youtube' ? 'bg-red-600 hover:bg-red-500' : 'bg-blue-600 hover:bg-blue-500'"
              >
                确认添加
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
/* 简单的 Spring 动画贝塞尔曲线 */
.cubic-bezier {
  transition-timing-function: cubic-bezier(0.34, 1.56, 0.64, 1);
}
</style>