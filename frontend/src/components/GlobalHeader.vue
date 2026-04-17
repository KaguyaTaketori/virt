<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { 
  Menu, Search, SlidersHorizontal, Bell, 
  ChevronDown, LogOut, 
  Settings, X, ShieldAlert, MonitorDot
} from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'
import { onClickOutside } from '@vueuse/core'

interface Props {
  isSidebarCollapsed: boolean
}

defineProps<Props>()

const emit = defineEmits<{
  (e: 'toggleSidebar'): void
}>()

const authStore = useAuthStore()
const searchQuery = ref('')
const showUserMenu = ref(false)
const userMenuRef = ref(null)

// 点击外部关闭菜单
onClickOutside(userMenuRef, () => {
  showUserMenu.value = false
})

function toggleUserMenu() {
  showUserMenu.value = !showUserMenu.value
}

function handleLogout() {
  authStore.logout()
  showUserMenu.value = false
}

onMounted(() => {
  authStore.init()
})
</script>

<template>
  <header
    class="h-14 shrink-0 flex items-center gap-4 px-4
           bg-zinc-950/80 backdrop-blur-md border-b border-zinc-900 sticky top-0 z-40"
  >
    <div class="flex items-center gap-3 shrink-0">
      <button
        @click="emit('toggleSidebar')"
        class="p-2 rounded-xl text-zinc-400 hover:text-white hover:bg-zinc-900 
               transition-all active:scale-90"
        :title="isSidebarCollapsed ? '展开导航' : '收起导航'"
      >
        <Menu class="w-5 h-5" />
      </button>

      <router-link to="/" class="flex items-center gap-2.5 group">
        <div
          class="w-8 h-8 rounded-xl bg-gradient-to-br from-rose-500 to-rose-700 
                 flex items-center justify-center shadow-lg shadow-rose-900/20
                 group-hover:rotate-6 transition-transform duration-300"
        >
          <MonitorDot class="w-5 h-5 text-white" />
        </div>
        <div class="flex flex-col leading-none sm:flex">
          <span class="text-white font-bold text-sm tracking-tight">VTUBER LIVE</span>
          <span class="text-[10px] text-rose-500 font-black tracking-widest">DEX</span>
        </div>
      </router-link>
    </div>

    <div class="flex-1 max-w-2xl mx-auto flex items-center gap-2 px-4">
      <div class="relative flex-1 group">
        <Search
          class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500
                 group-focus-within:text-rose-500 transition-colors pointer-events-none"
        />
        <input
          v-model="searchQuery"
          type="text"
          placeholder="搜索主播、直播间、平台..."
          class="w-full bg-zinc-900/50 border border-zinc-800 rounded-xl
                 pl-10 pr-10 py-2 text-sm text-white placeholder-zinc-600
                 outline-none focus:border-zinc-700 focus:bg-zinc-900
                 transition-all shadow-inner"
        />
        <button 
          v-if="searchQuery"
          @click="searchQuery = ''"
          class="absolute right-3 top-1/2 -translate-y-1/2 p-0.5 rounded-full hover:bg-zinc-700 text-zinc-500"
        >
          <X class="w-3.5 h-3.5" />
        </button>
      </div>

      <button
        class="p-2.5 rounded-xl bg-zinc-900 border border-zinc-800 text-zinc-400
               hover:text-white hover:border-zinc-700 transition-all shrink-0 active:scale-95"
        title="筛选"
      >
        <SlidersHorizontal class="w-4 h-4" />
      </button>
    </div>

    <div class="flex items-center gap-2 shrink-0">
      <button
        class="p-2 rounded-xl text-zinc-400 hover:text-white hover:bg-zinc-900
               transition-all relative group"
        title="通知"
      >
        <Bell class="w-5 h-5 group-hover:rotate-12 transition-transform" />
        <span class="absolute top-2 right-2 w-2 h-2 bg-rose-500 rounded-full border-2 border-zinc-950"></span>
      </button>

      <div v-if="authStore.isLoggedIn" class="relative" ref="userMenuRef">
        <button
          @click="toggleUserMenu"
          class="flex items-center gap-2 px-1.5 py-1.5 rounded-xl
                 hover:bg-zinc-900 border border-transparent hover:border-zinc-800 transition-all"
        >
          <div
            class="w-8 h-8 rounded-lg bg-gradient-to-tr from-zinc-800 to-zinc-700
                   border border-zinc-700 flex items-center justify-center 
                   text-xs font-bold text-white shadow-inner overflow-hidden"
          >
             <span v-if="!authStore.user?.avatar">{{ authStore.user?.username?.charAt(0).toUpperCase() }}</span>
             <img v-else :src="authStore.user.avatar" class="w-full h-full object-cover" />
          </div>
          <div class="flex-col items-start hidden md:flex leading-tight pr-1">
            <span class="text-[13px] font-bold text-zinc-100">{{ authStore.user?.username }}</span>
            <span class="text-[10px] text-zinc-500 font-medium">在线</span>
          </div>
          <ChevronDown class="w-3.5 h-3.5 text-zinc-500 transition-transform duration-300" :class="{'rotate-180': showUserMenu}" />
        </button>

        <transition name="dropdown">
          <div
            v-if="showUserMenu"
            class="absolute right-0 top-full mt-2 w-56 bg-zinc-900/95 backdrop-blur-xl 
                   border border-zinc-800 rounded-2xl shadow-2xl py-2 z-50 overflow-hidden"
          >
            <div class="px-4 py-3 border-b border-zinc-800/50 mb-1">
              <p class="text-sm font-bold text-white">{{ authStore.user?.username }}</p>
              <div class="flex flex-wrap gap-1 mt-1">
                <span v-for="role in authStore.user?.roles" :key="role" 
                      class="text-[9px] px-1.5 py-0.5 bg-zinc-800 text-zinc-400 rounded-md font-bold uppercase tracking-tighter">
                  {{ role }}
                </span>
              </div>
            </div>

            <router-link
              v-if="authStore.isAdmin"
              to="/admin/users"
              class="flex items-center gap-3 px-4 py-2.5 text-sm text-zinc-400 
                     hover:bg-zinc-800 hover:text-white transition-colors"
              @click="showUserMenu = false"
            >
              <ShieldAlert class="w-4 h-4 text-blue-500" />
              <span>用户管理</span>
            </router-link>

            <router-link
              to="/settings"
              class="flex items-center gap-3 px-4 py-2.5 text-sm text-zinc-400 
                     hover:bg-zinc-800 hover:text-white transition-colors"
              @click="showUserMenu = false"
            >
              <Settings class="w-4 h-4 text-zinc-400" />
              <span>个人设置</span>
            </router-link>

            <div class="h-px bg-zinc-800/50 my-1"></div>

            <button
              @click="handleLogout"
              class="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-rose-500 
                     hover:bg-rose-500/10 transition-colors"
            >
              <LogOut class="w-4 h-4" />
              <span class="font-bold">退出登录</span>
            </button>
          </div>
        </transition>
      </div>

      <router-link
        v-else
        to="/login"
        class="px-5 py-2 rounded-xl bg-rose-600 text-white text-sm font-bold
               hover:bg-rose-500 transition-all active:scale-95 shadow-lg shadow-rose-900/20"
      >
        登录
      </router-link>
    </div>
  </header>
</template>

<style scoped>
/* 下拉菜单动画 */
.dropdown-enter-active, .dropdown-leave-active {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}
.dropdown-enter-from {
  opacity: 0;
  transform: translateY(-8px) scale(0.95);
}
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-4px) scale(0.98);
}

/* 搜索框内阴影 */
.shadow-inner {
  box-shadow: inset 0 2px 4px 0 rgba(0, 0, 0, 0.05);
}
</style>