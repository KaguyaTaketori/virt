<script setup lang="ts">
import { Home, Settings, Sun, Moon, Palette } from 'lucide-vue-next'
import { useRouter } from 'vue-router'

interface Props {
  modelValue: boolean
  isDark: boolean
  currentThemeId: string
  themes: Array<{ id: string; name: string; colors: { primary: string } }>
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'update:modelValue', val: boolean): void
  (e: 'toggleDark'): void
  (e: 'setTheme', id: string): void
}>()

const router = useRouter()

function close() {
  emit('update:modelValue', false)
}

function navigate(path: string) {
  router.push(path)
  close()
}
</script>

<template>
  <!-- Overlay -->
  <Transition
    enter-active-class="transition-opacity duration-300 ease-out"
    enter-from-class="opacity-0"
    enter-to-class="opacity-100"
    leave-active-class="transition-opacity duration-200 ease-in"
    leave-from-class="opacity-100"
    leave-to-class="opacity-0"
  >
    <div
      v-if="modelValue"
      class="fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
      @click="close"
    />
  </Transition>

  <!-- Drawer Panel -->
  <Transition
    enter-active-class="transition-transform duration-300 ease-out"
    enter-from-class="-translate-x-full"
    enter-to-class="translate-x-0"
    leave-active-class="transition-transform duration-200 ease-in"
    leave-from-class="translate-x-0"
    leave-to-class="-translate-x-full"
  >
    <aside
      v-if="modelValue"
      class="fixed top-0 left-0 h-full w-64 z-50 flex flex-col
             bg-zinc-950 border-r border-zinc-800"
    >
      <!-- Logo -->
      <div class="flex items-center gap-3 px-5 py-5 border-b border-zinc-800">
        <div class="w-7 h-7 rounded bg-rose-500 flex items-center justify-center shrink-0">
          <span class="text-white text-xs font-black tracking-tighter">VL</span>
        </div>
        <span class="text-white font-semibold tracking-wide text-sm">VTuber Live</span>
      </div>

      <!-- Nav -->
      <nav class="flex-1 px-3 py-4 space-y-1">
        <button
          @click="navigate('/')"
          class="w-full flex items-center gap-3 px-3 py-2.5 rounded-md text-zinc-400
                 hover:text-white hover:bg-zinc-800 transition-colors text-sm"
        >
          <Home class="w-4 h-4" />
          <span>首页</span>
        </button>
        <button
          @click="navigate('/admin/channels')"
          class="w-full flex items-center gap-3 px-3 py-2.5 rounded-md text-zinc-400
                 hover:text-white hover:bg-zinc-800 transition-colors text-sm"
        >
          <Settings class="w-4 h-4" />
          <span>频道管理</span>
        </button>
      </nav>

      <!-- Bottom: Theme & Dark Mode -->
      <div class="px-3 py-4 border-t border-zinc-800 space-y-4">
        <!-- Dark / Light Toggle -->
        <div class="flex items-center justify-between px-1">
          <span class="text-zinc-500 text-xs uppercase tracking-widest">外观</span>
          <button
            @click="emit('toggleDark')"
            class="flex items-center gap-2 px-2.5 py-1.5 rounded-md text-zinc-400
                   hover:text-white hover:bg-zinc-800 transition-colors text-xs"
          >
            <Moon v-if="isDark" class="w-3.5 h-3.5" />
            <Sun v-else class="w-3.5 h-3.5" />
            <span>{{ isDark ? '深色' : '浅色' }}</span>
          </button>
        </div>

        <!-- Theme Swatches -->
        <div class="px-1">
          <div class="text-zinc-500 text-xs uppercase tracking-widest mb-2 flex items-center gap-1.5">
            <Palette class="w-3 h-3" />主题色
          </div>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="theme in themes.slice(0, 8)"
              :key="theme.id"
              @click="emit('setTheme', theme.id)"
              :title="theme.name"
              class="w-6 h-6 rounded-full border-2 transition-transform hover:scale-110"
              :style="{
                backgroundColor: theme.colors.primary,
                borderColor: currentThemeId === theme.id ? 'white' : 'transparent'
              }"
            />
          </div>
        </div>
      </div>
    </aside>
  </Transition>
</template>