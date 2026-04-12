<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NSpin, NEmpty, NScrollbar } from 'naive-ui'
import { 
  Radio, 
  Calendar, 
  History, 
  PowerOff, 
  Filter,
  RefreshCw,
  LayoutGrid
} from 'lucide-vue-next'

import { useAllStreams, useOrganizations } from '@/queries'
import { useAuthStore } from '@/stores/auth'
import { useMultiviewStore } from '@/stores/multiview'
import StreamCard from '@/components/StreamCard.vue'
import type { Stream, StreamStatus } from '@/types'

const router = useRouter()
const multiviewStore = useMultiviewStore()
const authStore = useAuthStore()

const selectedStatus = ref<StreamStatus>('live')
const selectedOrgId = ref<number | null>(null)

const streamsQuery = useAllStreams()
const orgsQuery = useOrganizations()

// 1. 状态配置 (颜色与图标)
const statusConfig = {
  live: { label: '直播中', icon: Radio, color: '#f43f5e', class: 'bg-rose-500' },
  upcoming: { label: '预约', icon: Calendar, color: '#f59e0b', class: 'bg-amber-500' },
  archive: { label: '录播', icon: History, color: '#8b5cf6', class: 'bg-violet-500' },
  offline: { label: '离线', icon: PowerOff, color: '#64748b', class: 'bg-slate-500' },
}

const statuses: { value: StreamStatus; label: string; icon: any }[] = [
  { value: 'live',     ...statusConfig.live },
  { value: 'upcoming', ...statusConfig.upcoming },
  { value: 'archive',  ...statusConfig.archive },
  { value: 'offline',  ...statusConfig.offline },
]

// 2. 过滤逻辑
const filteredStreams = computed(() => {
  let streams = streamsQuery.data.value ?? []
  
  // 基础过滤：状态
  streams = streams.filter(s => s.status === selectedStatus.value)
  
  // 基础过滤：机构
  if (selectedOrgId.value !== null) {
    streams = streams.filter(s => (s as any).org_id === selectedOrgId.value)
  }

  // 权限过滤：B站内容
  if (!authStore.canAccessBilibili) {
    streams = streams.filter(s => s.platform !== 'bilibili')
  }
  
  return streams
})

// 3. 统计逻辑
const statusCountMap = computed(() => {
  const all = streamsQuery.data.value ?? []
  const counts: any = {}
  statuses.forEach(s => {
    counts[s.value] = all.filter(item => {
      const orgMatch = selectedOrgId.value === null || (item as any).org_id === selectedOrgId.value
      return item.status === s.value && orgMatch
    }).length
  })
  return counts
})

const orgCountMap = computed(() => {
  const all = streamsQuery.data.value ?? []
  const byStatus = all.filter(s => s.status === selectedStatus.value)
  const result: Record<number, number> = {}
  orgsQuery.data.value?.forEach(org => {
    result[org.id] = byStatus.filter(s => (s as any).org_id === org.id).length
  })
  return result
})

const emptyDesc = computed(() => {
  // 获取当前选中机构的名称
  const orgName = selectedOrgId.value
    ? (orgsQuery.data.value?.find((o) => o.id === selectedOrgId.value)?.name ?? '')
    : ''
  
  const suffix = orgName ? `（${orgName}）` : ''
  
  const map: Record<StreamStatus, string> = {
    live:     `等待主播开播${suffix}...`,
    upcoming: `暂无预约直播${suffix}`,
    archive:  `暂无录播${suffix}`,
    offline:  `主播当前离线${suffix}`,
  }
  
  return map[selectedStatus.value] ?? ''
})

// 4. 跳转
function openMultiView(stream: Stream) {
  if (!stream?.video_id) return
  multiviewStore.addFromVideoId(stream.platform, stream.video_id)
  router.push({ name: 'MultiView' })
}
</script>

<template>
  <div class="min-h-screen bg-zinc-950 text-zinc-100 pb-12">
    <div class="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-8">
      
      <!-- Header: 标题与操作 -->
      <header class="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-8">
        <div>
          <div class="flex items-center gap-3 mb-1">
            <LayoutGrid class="w-8 h-8 text-pink-500" />
            <h1 class="text-3xl font-bold tracking-tight">直播列表</h1>
          </div>
          <p class="text-zinc-500 text-sm">实时监控全网 VTuber 频道状态</p>
        </div>
        
        <div class="flex items-center gap-2">
          <n-button quaternary circle @click="streamsQuery.refetch()">
            <template #icon><RefreshCw class="w-4 h-4" :class="{'animate-spin': streamsQuery.isRefetching.value}" /></template>
          </n-button>
        </div>
      </header>

      <!-- Filter Bar: 状态切换 -->
      <div class="mb-6">
        <div class="flex flex-wrap gap-3">
          <button
            v-for="s in statuses" :key="s.value"
            @click="selectedStatus = s.value"
            :class="[
              'group flex items-center gap-2.5 px-5 py-2.5 rounded-xl transition-all duration-300 border',
              selectedStatus === s.value 
                ? 'bg-zinc-100 text-zinc-950 border-white shadow-[0_0_20px_rgba(255,255,255,0.1)]' 
                : 'bg-zinc-900/50 text-zinc-400 border-zinc-800 hover:border-zinc-700'
            ]"
          >
            <component 
              :is="s.icon" 
              class="w-4 h-4" 
              :class="selectedStatus === s.value ? 'animate-pulse text-pink-600' : ''"
            />
            <span class="font-medium text-sm">{{ s.label }}</span>
            <span 
              :class="[
                'text-[10px] px-1.5 py-0.5 rounded-md font-bold transition-colors',
                selectedStatus === s.value ? 'bg-zinc-200 text-zinc-800' : 'bg-zinc-800 text-zinc-500'
              ]"
            >
              {{ statusCountMap[s.value] }}
            </span>
          </button>
        </div>
      </div>

      <!-- Filter Bar: 机构筛选 (带滚动条) -->
      <div class="mb-10 bg-zinc-900/30 p-4 rounded-2xl border border-zinc-800/50">
        <div class="flex items-center gap-3 mb-3 text-zinc-500 px-1">
          <Filter class="w-3.5 h-3.5" />
          <span class="text-[11px] font-bold uppercase tracking-widest">机构筛选</span>
        </div>
        
        <n-scrollbar x-scrollable>
          <div class="flex gap-2 pb-2">
            <button
              @click="selectedOrgId = null"
              :class="[
                'px-4 py-1.5 rounded-full text-xs font-medium transition-all whitespace-nowrap',
                selectedOrgId === null ? 'bg-pink-600 text-white' : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
              ]"
            >
              全部
            </button>
            
            <button
              v-for="org in orgsQuery.data.value" :key="org.id"
              @click="selectedOrgId = org.id"
              :class="[
                'flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium transition-all whitespace-nowrap border',
                selectedOrgId === org.id 
                  ? 'bg-zinc-100 text-zinc-950 border-white' 
                  : 'bg-zinc-900/80 text-zinc-400 border-zinc-800 hover:bg-zinc-800'
              ]"
            >
              <img
                v-if="org.logo_url"
                :src="org.logo_url"
                class="w-4 h-4 object-cover rounded-sm shadow-sm"
                referrerpolicy="no-referrer"
              />
              <span>{{ org.name }}</span>
              <span class="opacity-50 text-[10px]">({{ orgCountMap[org.id] ?? 0 }})</span>
            </button>
          </div>
        </n-scrollbar>
      </div>

      <!-- Main Content -->
      <div v-if="streamsQuery.isLoading.value" class="flex flex-col items-center justify-center py-32 gap-4">
        <n-spin size="large" stroke="#ec4899" />
        <p class="text-zinc-500 text-sm animate-pulse">正在获取实时流数据...</p>
      </div>

      <div v-else-if="streamsQuery.isError.value" class="max-w-md mx-auto text-center py-20">
        <div class="bg-red-500/10 border border-red-500/20 rounded-2xl p-8">
          <p class="text-red-400 mb-6">数据链路异常: {{ streamsQuery.error.value?.message }}</p>
          <n-button type="error" ghost @click="streamsQuery.refetch()" round>
             重新连接
          </n-button>
        </div>
      </div>

      <div v-else-if="filteredStreams.length === 0" class="py-32">
        <n-empty description="当前环境下空空如也">
          <template #extra>
            <span class="text-zinc-600 text-sm italic">{{ emptyDesc }}</span>
          </template>
        </n-empty>
      </div>

      <div v-else class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
        <transition-group 
          name="staggered-fade" 
          tag="div" 
          class="contents"
        >
          <StreamCard
            v-for="(stream, _index) in filteredStreams"
            :key="stream.id ?? stream.video_id"
            :stream="stream"
            class="hover:-translate-y-1 transition-transform duration-300"
            @click="openMultiView(stream)"
          />
        </transition-group>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 水平滚动条美化 */
:deep(.n-scrollbar-rail.n-scrollbar-rail--horizontal) {
  height: 4px;
}

/* 列表进入动画 */
.staggered-fade-enter-active {
  transition: all 0.5s ease-out;
}
.staggered-fade-enter-from {
  opacity: 0;
  transform: translateY(20px);
}

/* 隐藏滚动条 */
.n-scrollbar :deep(.n-scrollbar-content) {
  display: flex;
}
</style>