<script setup lang="ts">
import { useRouter } from 'vue-router'
import { Menu, Settings, HelpCircle } from 'lucide-vue-next'
import DrawerNavSection from './drawer/DrawerNavSection.vue'
import DrawerThemeSection from './drawer/DrawerThemeSection.vue'

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

const close = () => emit('update:modelValue', false)

const navigate = (path: string) => {
  router.push(path)
  close()
}
</script>

<template>
  <!-- 遮罩层 -->
  <Transition name="fade">
    <div v-if="modelValue" class="fixed inset-0 bg-black/60 backdrop-blur-sm z-40" @click="close" />
  </Transition>

  <!-- 侧边面板 -->
  <Transition name="slide">
    <aside v-if="modelValue" class="fixed top-0 left-0 h-full w-64 z-50 flex flex-col bg-zinc-950 border-r border-zinc-800 shadow-2xl">
      
      <!-- 头部: Logo -->
      <div class="flex items-center gap-3 px-4 py-4 border-b border-zinc-800">
        <button @click="close" class="p-2 -ml-2 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors">
          <Menu class="w-5 h-5" />
        </button>
        <router-link to="/" class="flex items-center gap-2 group" @click="close">
          <div class="w-7 h-7 rounded-md bg-rose-600 flex items-center justify-center group-hover:bg-rose-500 transition-colors">
            <span class="text-white text-[11px] font-black tracking-tighter">VL</span>
          </div>
          <span class="text-white font-semibold text-sm">VTuber Live</span>
        </router-link>
      </div>

      <!-- 中间: 导航列表 (子组件) -->
      <DrawerNavSection @navigate="navigate" />

      <!-- 底部: 主题与辅助 (子组件) -->
      <div class="px-3 py-4 border-t border-zinc-800 space-y-4">
        <DrawerThemeSection 
          :is-dark="isDark"
          :current-theme-id="currentThemeId"
          :themes="themes"
          @toggle-dark="emit('toggleDark')"
          @set-theme="id => emit('setTheme', id)"
        />

        <!-- 辅助功能 -->
        <div class="flex items-center gap-2 px-1 pt-2 border-t border-zinc-800">
          <button @click="navigate('/help')" class="flex-1 footer-btn">
            <HelpCircle class="w-4 h-4" /> <span>帮助</span>
          </button>
          <button @click="navigate('/settings')" class="flex-1 footer-btn">
            <Settings class="w-4 h-4" /> <span>设置</span>
          </button>
        </div>
      </div>
    </aside>
  </Transition>
</template>

<style scoped>
.footer-btn {
  @apply flex items-center gap-2 px-3 py-2 rounded-md text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors text-sm;
}

/* 动画定义 */
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.slide-enter-active { transition: transform 0.3s ease-out; }
.slide-leave-active { transition: transform 0.2s ease-in; }
.slide-enter-from, .slide-leave-to { transform: translateX(-100%); }
</style>