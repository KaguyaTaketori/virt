<script setup lang="ts">
import { Sun, Moon, Palette } from 'lucide-vue-next'

interface Props {
  isDark: boolean
  currentThemeId: string
  themes: Array<{ id: string; name: string; colors: { primary: string } }>
}

defineProps<Props>()
const emit = defineEmits(['toggleDark', 'setTheme'])
</script>

<template>
  <div class="space-y-4 px-1">
    <!-- 深浅色切换 -->
    <div class="flex items-center justify-between">
      <span class="section-title">外观模式</span>
      <button @click="emit('toggleDark')" class="theme-toggle-btn">
        <Moon v-if="isDark" class="w-3.5 h-3.5" />
        <Sun v-else class="w-3.5 h-3.5" />
        <span>{{ isDark ? '深色' : '浅色' }}</span>
      </button>
    </div>

    <!-- 主题色选取 -->
    <div>
      <div class="section-title mb-2 flex items-center gap-1.5">
        <Palette class="w-3 h-3" />主题色彩
      </div>
      <div class="flex flex-wrap gap-2.5">
        <button
          v-for="theme in themes" :key="theme.id"
          @click="emit('setTheme', theme.id)"
          :title="theme.name"
          class="w-6 h-6 rounded-full border-2 transition-all hover:scale-125 active:scale-95"
          :style="{
            backgroundColor: theme.colors.primary,
            borderColor: currentThemeId === theme.id ? 'white' : 'transparent'
          }"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.section-title {
  @apply text-zinc-500 text-[10px] uppercase tracking-widest font-bold;
}
.theme-toggle-btn {
  @apply flex items-center gap-2 px-2.5 py-1.5 rounded-md bg-zinc-900 text-zinc-400 hover:text-white transition-colors text-xs border border-zinc-800;
}
</style>