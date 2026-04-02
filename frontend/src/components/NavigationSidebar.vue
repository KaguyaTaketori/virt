<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Home, Heart, Tv2, ListVideo,
  LayoutGrid, Music, HelpCircle, Settings,
  SlidersHorizontal, Building2, ChevronDown, ChevronUp
} from 'lucide-vue-next'

interface NavItem {
  label: string
  icon: any
  type: 'link' | 'group'
  to?: string
  badge?: number
}

interface NavSection {
  items: NavItem[]
  separator?: boolean
}

interface Props {
  isCollapsed: boolean
}

const props = defineProps<Props>()
const showAdminMenu = ref(false)

const navSections: NavSection[] = [
  {
    items: [
      { label: '主页',     icon: Home,      type: 'link',  to: '/'          },
      { label: '收藏',     icon: Heart,     type: 'link',  to: '/favorites' },
      { label: '频道',     icon: Tv2,       type: 'link',  to: '/channels'  },
      { label: '播放列表', icon: ListVideo, type: 'link',  to: '/playlists' },
    ],
  },
  {
    separator: true,
    items: [
      { label: '多窗播放', icon: LayoutGrid, type: 'link', to: '/multiview' },
      { label: 'Musicdex', icon: Music,      type: 'link', to: '/musicdex'  },
    ],
  },
  {
    separator: true,
    items: [
      { label: '帮助', icon: HelpCircle, type: 'link', to: '/help'     },
      { label: '设置', icon: Settings,   type: 'link', to: '/settings' },
    ],
  },
  {
    separator: true,
    items: [
      // 修正：使用 type: 'group' 标记，不再用 to: '' 作为"无跳转"的魔法值
      { label: '管理', icon: Settings, type: 'group' },
    ],
  },
]

const route  = useRoute()
const router = useRouter()

function isActive(item: NavItem): boolean {
  if (item.type === 'group' || !item.to) return false
  if (item.to === '/') return route.path === '/'
  return route.path.startsWith(item.to)
}

function navigate(item: NavItem): void {
  if (item.type === 'group') {
    showAdminMenu.value = !showAdminMenu.value
    return
  }
  if (item.to) {
    router.push(item.to)
  }
}

const sidebarWidthClass = computed<string>(() =>
  props.isCollapsed ? 'w-14' : 'w-52'
)

const labelClass = computed<string>(() =>
  props.isCollapsed
    ? 'opacity-0 w-0 overflow-hidden whitespace-nowrap'
    : 'opacity-100 w-auto'
)
</script>

<template>
  <nav
    class="shrink-0 overflow-hidden flex flex-col
           bg-zinc-950 border-r border-zinc-800
           transition-all duration-300 ease-in-out"
    :class="sidebarWidthClass"
  >
    <div class="flex-1 overflow-y-auto overflow-x-hidden py-3 space-y-0.5 px-2">
      <template v-for="(section, si) in navSections" :key="si">

        <div v-if="section.separator" class="my-2 border-t border-zinc-800" />

        <div v-for="item in section.items" :key="item.label">
          <button
            @click="navigate(item)"
            class="w-full flex items-center gap-3 rounded-lg px-2.5 py-2.5
                   text-sm transition-colors duration-150 relative group"
            :class="isActive(item)
              ? 'bg-zinc-800 text-white'
              : 'text-zinc-400 hover:text-white hover:bg-zinc-800/60'"
            :title="isCollapsed ? item.label : undefined"
          >
            <component
              :is="item.icon"
              class="w-4.5 h-4.5 shrink-0"
              :class="isActive(item) ? 'text-rose-400' : ''"
              style="width: 1.125rem; height: 1.125rem;"
            />

            <span
              class="font-medium leading-none transition-all duration-300 ease-in-out"
              :class="labelClass"
            >
              {{ item.label }}
            </span>

            <template v-if="item.type === 'group' && !isCollapsed">
              <component
                :is="showAdminMenu ? ChevronUp : ChevronDown"
                class="w-3 h-3 ml-auto opacity-50"
              />
            </template>

            <span
              v-if="item.badge && !isCollapsed"
              class="ml-auto shrink-0 text-[10px] font-bold px-1.5 py-0.5
                     rounded-full bg-rose-600 text-white leading-none"
            >
              {{ item.badge }}
            </span>

            <span
              v-if="isCollapsed"
              class="absolute left-full ml-2.5 px-2.5 py-1.5 rounded-md
                     bg-zinc-800 border border-zinc-700 text-white text-xs
                     whitespace-nowrap pointer-events-none z-50
                     opacity-0 group-hover:opacity-100 translate-x-1
                     group-hover:translate-x-0 transition-all duration-150
                     shadow-lg shadow-black/40"
            >
              {{ item.label }}
            </span>
          </button>

          <div
            v-if="item.type === 'group' && showAdminMenu && !isCollapsed"
            class="ml-4 mt-1 space-y-0.5"
          >
            <button
              @click="router.push('/admin/channels')"
              class="w-full flex items-center gap-3 rounded-lg px-2.5 py-2
                     text-sm transition-colors duration-150"
              :class="route.path.startsWith('/admin/channels')
                ? 'bg-zinc-800 text-white'
                : 'text-zinc-400 hover:text-white hover:bg-zinc-800/60'"
            >
              <Tv2 style="width: 1.125rem; height: 1.125rem;" class="shrink-0" />
              <span class="font-medium">频道管理</span>
            </button>

            <button
              @click="router.push('/admin/organizations')"
              class="w-full flex items-center gap-3 rounded-lg px-2.5 py-2
                     text-sm transition-colors duration-150"
              :class="route.path.startsWith('/admin/organizations')
                ? 'bg-zinc-800 text-white'
                : 'text-zinc-400 hover:text-white hover:bg-zinc-800/60'"
            >
              <Building2 style="width: 1.125rem; height: 1.125rem;" class="shrink-0" />
              <span class="font-medium">机构管理</span>
            </button>
          </div>
        </div>

      </template>
    </div>

    <div class="shrink-0 border-t border-zinc-800 py-3 px-2">
      <button
        class="w-full flex items-center gap-3 rounded-lg px-2.5 py-2.5
               text-zinc-500 hover:text-white hover:bg-zinc-800/60
               transition-colors text-sm group relative"
        title="偏好设置"
      >
        <SlidersHorizontal style="width: 1.125rem; height: 1.125rem;" class="shrink-0" />
        <span
          class="font-medium leading-none transition-all duration-300 ease-in-out"
          :class="labelClass"
        >
          偏好设置
        </span>
        <span
          v-if="isCollapsed"
          class="absolute left-full ml-2.5 px-2.5 py-1.5 rounded-md
                 bg-zinc-800 border border-zinc-700 text-white text-xs
                 whitespace-nowrap pointer-events-none z-50
                 opacity-0 group-hover:opacity-100 translate-x-1
                 group-hover:translate-x-0 transition-all duration-150
                 shadow-lg shadow-black/40"
        >
          偏好设置
        </span>
      </button>
    </div>
  </nav>
</template>