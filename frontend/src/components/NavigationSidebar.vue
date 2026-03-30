<script setup lang="ts">
/**
 * NavigationSidebar.vue — 可折叠侧边导航栏
 *
 * 宽度通过 Tailwind 动态类 + CSS transition 平滑过渡：
 *   展开 → w-52 (208px)
 *   收缩 → w-14 (56px，仅显示图标)
 *
 * overflow-hidden 配合固定宽度：文字在收缩时被裁剪而非换行，
 * 搭配 opacity transition 实现淡出效果。
 */
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Home, Heart, Tv2, ListVideo,
  LayoutGrid, Music, HelpCircle, Settings,
  SlidersHorizontal, Building2, ChevronDown, ChevronUp
} from 'lucide-vue-next'

// ── 类型定义 ──────────────────────────────────────────────────────────────────

interface NavItem {
  label: string
  icon: any          // Lucide component
  to: string
  badge?: number     // 可选角标数字（如在播数量）
}

interface NavSection {
  items: NavItem[]
  separator?: boolean
}

// ── Props ─────────────────────────────────────────────────────────────────────

interface Props {
  /** true = 仅显示图标的收缩模式 */
  isCollapsed: boolean
}

const props = defineProps<Props>()
const showAdminMenu = ref(false)

// 导航数据

const navSections: NavSection[] = [
  {
    items: [
      { label: '主页',       icon: Home,       to: '/'                   },
      { label: '收藏',       icon: Heart,       to: '/favorites'          },
      { label: '频道',       icon: Tv2,         to: '/channels'          },
      { label: '播放列表',   icon: ListVideo,   to: '/playlists'          },
    ],
  },
  {
    separator: true,
    items: [
      { label: '多窗播放',   icon: LayoutGrid,  to: '/multiview'          },
      { label: 'Musicdex',   icon: Music,       to: '/musicdex'           },
    ],
  },
  {
    separator: true,
    items: [
      { label: '帮助',       icon: HelpCircle,  to: '/help'               },
      { label: '设置',       icon: Settings,    to: '/settings'           },
    ],
  },
  {
    separator: true,
    items: [
      { label: '管理',       icon: Settings,    to: ''                    },
    ],
  },
]

// ── 路由高亮 ──────────────────────────────────────────────────────────────────

const route  = useRoute()
const router = useRouter()

function isActive(to: string): boolean {
  if (to === '/') return route.path === '/'
  return route.path.startsWith(to)
}

function navigate(to: string): void {
  if (to === '') {
    showAdminMenu.value = !showAdminMenu.value
  } else {
    router.push(to)
  }
}

// ── 动态样式 ─────────────────────────────────────────────────────────────────

/** 侧边栏容器宽度：过渡动画由 transition-all duration-300 驱动 */
const sidebarWidthClass = computed<string>(() =>
  props.isCollapsed ? 'w-14' : 'w-52'
)

/** 标签文字：收缩时淡出并隐藏，避免文字溢出破坏布局 */
const labelClass = computed<string>(() =>
  props.isCollapsed
    ? 'opacity-0 w-0 overflow-hidden whitespace-nowrap'
    : 'opacity-100 w-auto'
)
</script>

<template>
  <!--
    侧边栏容器
    ─────────────────────────────────────────────────────────────────────────────
    shrink-0         → 禁止被 flex 父容器压缩（与 GlobalHeader 同级）
    overflow-hidden  → 宽度收缩时裁剪掉溢出的文字，不产生横向滚动条
    transition-all   → 宽度 / 内边距平滑过渡
    ─────────────────────────────────────────────────────────────────────────────
  -->
  <nav
    class="shrink-0 overflow-hidden flex flex-col
           bg-zinc-950 border-r border-zinc-800
           transition-all duration-300 ease-in-out"
    :class="sidebarWidthClass"
  >
    <!-- ── 导航列表 ── -->
    <div class="flex-1 overflow-y-auto overflow-x-hidden py-3 space-y-0.5 px-2">

      <template v-for="(section, si) in navSections" :key="si">

        <!-- 分隔线 -->
        <div
          v-if="section.separator"
          class="my-2 border-t border-zinc-800"
        />

        <!-- 导航项 -->
        <div v-for="item in section.items" :key="item.to">
          <button
            @click="navigate(item.to)"
            class="w-full flex items-center gap-3 rounded-lg px-2.5 py-2.5
                   text-sm transition-colors duration-150 relative group"
            :class="isActive(item.to)
              ? 'bg-zinc-800 text-white'
              : 'text-zinc-400 hover:text-white hover:bg-zinc-800/60'"
            :title="isCollapsed ? item.label : undefined"
          >
            <!-- 图标（始终可见） -->
            <component
              :is="item.icon"
              class="w-4.5 h-4.5 shrink-0"
              :class="isActive(item.to) ? 'text-rose-400' : ''"
              style="width: 1.125rem; height: 1.125rem;"
            />

            <!--
              标签文字
              transition 覆盖 opacity 和 width，实现淡出 + 收缩的双重效果。
              width 过渡搭配 overflow-hidden 确保文字不会溢出或换行。
            -->
            <span
              class="font-medium leading-none transition-all duration-300 ease-in-out"
              :class="labelClass"
            >
              {{ item.label }}
            </span>

            <!-- 角标 -->
            <span
              v-if="item.badge && !isCollapsed"
              class="ml-auto shrink-0 text-[10px] font-bold px-1.5 py-0.5 rounded-full
                     bg-rose-600 text-white leading-none"
            >
              {{ item.badge }}
            </span>
            <component
              v-if="item.to === '' && !isCollapsed"
              :is="showAdminMenu ? ChevronUp : ChevronDown"
              class="w-3 h-3 ml-auto opacity-50"
            />

            <!-- 收缩时：Tooltip 仿原生悬浮提示（纯 CSS，无 JS 依赖）-->
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

          <!-- 管理子菜单 -->
          <div v-if="item.to === '' && showAdminMenu && !isCollapsed" class="ml-4 mt-1 space-y-0.5">
            <button
              @click="navigate('/admin/channels')"
              class="w-full flex items-center gap-3 rounded-lg px-2.5 py-2
                     text-sm transition-colors duration-150 relative group"
              :class="isActive('/admin/channels')
                ? 'bg-zinc-800 text-white'
                : 'text-zinc-400 hover:text-white hover:bg-zinc-800/60'"
            >
              <Tv2 class="w-4 h-4 shrink-0" style="width: 1.125rem; height: 1.125rem;" />
              <span class="font-medium">频道管理</span>
            </button>
            <button
              @click="navigate('/admin/organizations')"
              class="w-full flex items-center gap-3 rounded-lg px-2.5 py-2
                     text-sm transition-colors duration-150 relative group"
              :class="isActive('/admin/organizations')
                ? 'bg-zinc-800 text-white'
                : 'text-zinc-400 hover:text-white hover:bg-zinc-800/60'"
            >
              <Building2 class="w-4 h-4 shrink-0" style="width: 1.125rem; height: 1.125rem;" />
              <span class="font-medium">机构管理</span>
            </button>
          </div>
        </div>

      </template>
    </div>

    <!-- ── 底部：设置项（可选，仿 Nijidex 底部区域）── -->
    <div
      class="shrink-0 border-t border-zinc-800 py-3 px-2"
    >
      <button
        class="w-full flex items-center gap-3 rounded-lg px-2.5 py-2.5
               text-zinc-500 hover:text-white hover:bg-zinc-800/60
               transition-colors text-sm group relative"
        title="筛选偏好"
      >
        <SlidersHorizontal
          style="width: 1.125rem; height: 1.125rem;"
          class="shrink-0"
        />
        <span
          class="font-medium leading-none transition-all duration-300 ease-in-out"
          :class="labelClass"
        >
          偏好设置
        </span>
        <!-- 收缩 Tooltip -->
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