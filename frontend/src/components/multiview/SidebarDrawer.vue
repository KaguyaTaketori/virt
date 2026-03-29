<script setup lang="ts">
import { ref } from 'vue'
import { 
  Home, Settings, Sun, Moon, Palette, 
  Search, SlidersHorizontal, Bell, ChevronDown,
  LayoutGrid, Captions
} from 'lucide-vue-next'
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
const searchQuery = ref('')

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
      class="fixed top-0 left-0 h-full w-72 z-50 flex flex-col
             bg-zinc-950 border-r border-zinc-800"
    >
      <!-- Header: Logo + Search -->
      <div class="border-b border-zinc-800">
        <!-- Logo -->
        <div class="flex items-center gap-3 px-4 py-4">
          <button
            @click="close"
            class="p-2 -ml-2 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <router-link to="/" class="flex items-center gap-2 group" @click="close">
            <div class="w-7 h-7 rounded-md bg-rose-600 flex items-center justify-center group-hover:bg-rose-500 transition-colors shrink-0">
              <span class="text-white text-[11px] font-black tracking-tighter">VL</span>
            </div>
            <span class="text-white font-semibold text-sm">VTuber Live</span>
          </router-link>
        </div>

        <!-- Search -->
        <div class="px-4 pb-4">
          <div class="relative">
            <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500 pointer-events-none" />
            <input
              v-model="searchQuery"
              type="text"
              placeholder="搜索"
              class="w-full bg-zinc-800 border border-zinc-700 rounded-lg pl-9 pr-4 py-2 text-sm text-white placeholder-zinc-500 outline-none focus:border-zinc-500 focus:ring-1 focus:ring-zinc-500/30 transition-colors"
            />
          </div>
        </div>
      </div>

      <!-- Nav -->
      <nav class="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <button
          @click="navigate('/')"
          class="w-full flex items-center gap-3 px-3 py-2.5 rounded-md text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors text-sm"
        >
          <Home class="w-4 h-4" />
          <span>首页</span>
        </button>
        <button
          @click="navigate('/multiview')"
          class="w-full flex items-center gap-3 px-3 py-2.5 rounded-md text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors text-sm"
        >
          <LayoutGrid class="w-4 h-4" />
          <span>多视图</span>
        </button>
        <button
          @click="navigate('/admin/channels')"
          class="w-full flex items-center gap-3 px-3 py-2.5 rounded-md text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors text-sm"
        >
          <Settings class="w-4 h-4" />
          <span>频道管理</span>
        </button>
      </nav>

      <!-- Bottom: Theme & Settings -->
      <div class="px-3 py-4 border-t border-zinc-800 space-y-4">
        <!-- Quick Settings -->
        <div class="flex items-center gap-2 px-1">
          <button
            class="p-2 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors"
            title="筛选"
          >
            <SlidersHorizontal class="w-4 h-4" />
          </button>
          <button
            class="p-2 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors relative"
            title="通知"
          >
            <Bell class="w-4 h-4" />
            <span class="absolute top-1 right-1 w-2 h-2 bg-rose-500 rounded-full"></span>
          </button>
        </div>

        <!-- Dark / Light Toggle -->
        <div class="flex items-center justify-between px-1">
          <span class="text-zinc-500 text-xs uppercase tracking-widest">外观</span>
          <button
            @click="emit('toggleDark')"
            class="flex items-center gap-2 px-2.5 py-1.5 rounded-md text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors text-xs"
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

        <!-- User -->
        <div class="flex items-center gap-2 px-1 pt-2 border-t border-zinc-800">
          <div class="w-8 h-8 rounded-full bg-gradient-to-br from-rose-500 to-violet-600 flex items-center justify-center text-xs font-bold text-white">
            U
          </div>
          <div class="flex-1">
            <div class="text-sm text-white">用户</div>
            <div class="text-xs text-zinc-500">VIP</div>
          </div>
          <button class="p-1 rounded text-zinc-400 hover:text-white">
            <ChevronDown class="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  </Transition>
</template>