<script setup lang="ts">
import { ref } from 'vue'
import { 
  Home, Heart, Tv2, ListMusic, LayoutGrid, Music2, 
  Settings, Building2, ChevronRight, ChevronDown, ChevronUp 
} from 'lucide-vue-next'

const emit = defineEmits(['navigate'])
const showAdminMenu = ref(false)

const navItems = [
  { label: '首页', icon: Home, to: '/' },
  { label: '收藏', icon: Heart, to: '/favorites' },
  { label: '频道', icon: Tv2, to: '/channels' },
  { label: '播放列表', icon: ListMusic, to: '/playlist' },
  { label: '多窗播放', icon: LayoutGrid, to: '/multiview' },
  { label: 'Musicdex', icon: Music2, to: '/musicdex' },
]
</script>

<template>
  <nav class="flex-1 px-3 py-4 space-y-1 overflow-y-auto custom-scrollbar">
    <button
      v-for="item in navItems" :key="item.to"
      @click="emit('navigate', item.to)"
      class="nav-item group"
    >
      <component :is="item.icon" class="w-4 h-4" />
      <span>{{ item.label }}</span>
      <ChevronRight class="w-3 h-3 ml-auto opacity-0 group-hover:opacity-50 transition-all" />
    </button>
    
    <div class="my-2 border-t border-zinc-800" />
    
    <!-- 管理员二级菜单 -->
    <button @click="showAdminMenu = !showAdminMenu" class="nav-item">
      <Settings class="w-4 h-4 text-zinc-500" />
      <span class="flex-1">管理控制台</span>
      <ChevronDown v-if="!showAdminMenu" class="w-3 h-3 opacity-50" />
      <ChevronUp v-else class="w-3 h-3 opacity-50" />
    </button>
    
    <div v-if="showAdminMenu" class="ml-4 mt-1 space-y-1 border-l border-zinc-800 pl-2">
      <button @click="emit('navigate', '/admin/channels')" class="nav-item text-xs">
        <Tv2 class="w-3.5 h-3.5" /> <span>频道管理</span>
      </button>
      <button @click="emit('navigate', '/admin/organizations')" class="nav-item text-xs">
        <Building2 class="w-3.5 h-3.5" /> <span>机构管理</span>
      </button>
    </div>
  </nav>
</template>

<style scoped>
.nav-item {
  @apply w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-900 transition-all text-sm;
}
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-thumb { @apply bg-zinc-800 rounded; }
</style>