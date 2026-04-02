<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Menu, Search, SlidersHorizontal, Bell, ChevronDown, LogOut, User as UserIcon, Settings } from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

interface Props {
  isSidebarCollapsed: boolean
}

defineProps<Props>()

const emit = defineEmits<{
  (e: 'toggleSidebar'): void
}>()

const router = useRouter()
const authStore = useAuthStore()

const searchQuery = ref('')
const showUserMenu = ref(false)

function toggleUserMenu() {
  showUserMenu.value = !showUserMenu.value
}

function closeUserMenu() {
  showUserMenu.value = false
}

function handleLogout() {
  authStore.logout()
  closeUserMenu()
}

onMounted(() => {
  authStore.init()
})
</script>

<template>
  <header
    class="h-14 shrink-0 flex items-center gap-3 px-4
           bg-zinc-950 border-b border-zinc-800 z-20"
  >
    <div class="flex items-center gap-3 shrink-0">
      <button
        @click="emit('toggleSidebar')"
        class="p-2 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800
               transition-colors"
        :title="isSidebarCollapsed ? '展开导航' : '收起导航'"
      >
        <Menu class="w-5 h-5" />
      </button>

      <router-link to="/" class="flex items-center gap-2 group">
        <div
          class="w-7 h-7 rounded-md bg-rose-600 flex items-center justify-center
                 group-hover:bg-rose-500 transition-colors shrink-0"
        >
          <span class="text-white text-[11px] font-black tracking-tighter">VL</span>
        </div>
        <span class="text-white font-semibold text-sm hidden sm:block">VTuber Live</span>
      </router-link>
    </div>

    <div class="flex-1 max-w-xl mx-auto flex items-center gap-2">
      <div class="relative flex-1">
        <Search
          class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500
                 pointer-events-none"
        />
        <input
          v-model="searchQuery"
          type="text"
          placeholder="搜索"
          class="w-full bg-zinc-800 border border-zinc-700 rounded-lg
                 pl-9 pr-4 py-2 text-sm text-white placeholder-zinc-500
                 outline-none focus:border-zinc-500 focus:ring-1 focus:ring-zinc-500/30
                 transition-colors"
        />
      </div>
      <button
        class="p-2 rounded-lg bg-zinc-800 border border-zinc-700 text-zinc-400
               hover:text-white hover:border-zinc-600 transition-colors shrink-0"
        title="筛选"
      >
        <SlidersHorizontal class="w-4 h-4" />
      </button>
    </div>

    <div class="flex items-center gap-2 shrink-0">
      <button
        class="p-2 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800
               transition-colors relative"
        title="通知"
      >
        <Bell class="w-5 h-5" />
      </button>

      <!-- 已登录用户菜单 -->
      <div v-if="authStore.isLoggedIn" class="relative">
        <button
          @click="toggleUserMenu"
          class="flex items-center gap-1.5 px-2 py-1.5 rounded-lg
                 hover:bg-zinc-800 transition-colors"
        >
          <div
            class="w-7 h-7 rounded-full bg-gradient-to-br from-rose-500 to-violet-600
                   flex items-center justify-center text-xs font-bold text-white shrink-0"
          >
            {{ authStore.user?.username?.charAt(0).toUpperCase() || 'U' }}
          </div>
          <span class="text-sm text-white hidden md:block">{{ authStore.user?.username }}</span>
          <ChevronDown class="w-3.5 h-3.5 text-zinc-400" />
        </button>

        <!-- 下拉菜单 -->
        <div
          v-if="showUserMenu"
          class="absolute right-0 top-full mt-2 w-48 bg-zinc-800 border border-zinc-700 
                 rounded-lg shadow-lg py-1 z-50"
          @click="closeUserMenu"
        >
          <div class="px-3 py-2 border-b border-zinc-700">
            <p class="text-sm font-medium text-white">{{ authStore.user?.username }}</p>
            <p class="text-xs text-zinc-400">{{ authStore.user?.roles?.join(', ') || '无角色' }}</p>
          </div>
          <router-link
            v-if="authStore.isAdmin"
            to="/admin/users"
            class="flex items-center gap-2 px-3 py-2 text-sm text-zinc-300 
                   hover:bg-zinc-700 hover:text-white"
          >
            <UserIcon class="w-4 h-4" />
            用户管理
          </router-link>
          <router-link
            v-if="authStore.isSuperAdmin"
            to="/admin/roles"
            class="flex items-center gap-2 px-3 py-2 text-sm text-zinc-300 
                   hover:bg-zinc-700 hover:text-white"
          >
            <Settings class="w-4 h-4" />
            角色与权限
          </router-link>
          <button
            @click="handleLogout"
            class="w-full flex items-center gap-2 px-3 py-2 text-sm text-zinc-300 
                   hover:bg-zinc-700 hover:text-white"
          >
            <LogOut class="w-4 h-4" />
            退出登录
          </button>
        </div>
      </div>

      <!-- 未登录 -->
      <router-link
        v-else
        to="/login"
        class="px-3 py-1.5 rounded-lg bg-pink-600 text-white text-sm 
               hover:bg-pink-500 transition-colors"
      >
        登录
      </router-link>
    </div>
  </header>
</template>