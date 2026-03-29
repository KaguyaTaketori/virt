<!-- frontend/src/views/Home.vue -->
<template>
  <div class="container mx-auto px-4 py-8">
    <div class="mb-6">
      <h1 class="text-3xl font-bold mb-1">直播列表</h1>
      <p class="text-gray-400 text-sm">VTuber 频道直播状态</p>
    </div>

    <!-- 机构筛选 -->
    <div v-if="orgStore.organizations.length > 0" class="mb-4 flex flex-wrap gap-2 items-center">
      <button
        @click="store.setOrg(null)"
        class="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm transition"
        :class="store.currentOrgId === null
          ? 'bg-pink-600 text-white'
          : 'bg-gray-700 text-gray-300 hover:bg-gray-600'"
      >
        全部
      </button>
      <button
        v-for="org in orgStore.organizations"
        :key="org.id"
        @click="store.setOrg(org.id)"
        class="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm transition"
        :class="store.currentOrgId === org.id
          ? 'bg-pink-600 text-white'
          : 'bg-gray-700 text-gray-300 hover:bg-gray-600'"
      >
        <img
          v-if="org.logo_url"
          :src="org.logo_url"
          class="w-4 h-4 object-cover flex-shrink-0"
          :style="org.logo_shape === 'square' ? 'border-radius:3px' : 'border-radius:50%'"
          referrerpolicy="no-referrer"
        />
        <span>{{ org.name }}</span>
        <span class="opacity-60 text-xs">({{ getOrgCount(org.id) }})</span>
      </button>
    </div>

    <!-- Status 标签 -->
    <div class="mb-6 flex flex-wrap gap-2">
      <button
        v-for="s in statuses"
        :key="s.value"
        @click="store.setStatus(s.value)"
        class="px-4 py-2 rounded-full transition text-sm"
        :class="store.currentStatus === s.value
          ? 'bg-pink-600 text-white'
          : 'bg-gray-700 text-gray-300 hover:bg-gray-600'"
      >
        {{ s.label }}
        <span class="ml-1 opacity-70">({{ getStatusCount(s.value) }})</span>
      </button>
    </div>

    <!-- 加载 / 错误 / 空状态 -->
    <div v-if="store.loading" class="flex justify-center py-16">
      <div class="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-pink-500"></div>
    </div>

    <div v-else-if="store.error" class="text-center py-12 text-red-400">
      <p>加载失败：{{ store.error }}</p>
      <button @click="store.fetchStreams(true)" class="mt-4 px-4 py-2 bg-pink-600 rounded hover:bg-pink-700 text-sm">
        重试
      </button>
    </div>

    <div v-else-if="store.currentStreams.length === 0" class="text-center py-16 text-gray-500">
      <p class="text-lg">暂无数据</p>
      <p class="mt-1 text-sm">{{ emptyDesc }}</p>
    </div>

    <div v-else class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-5">
      <StreamCard
        v-for="(stream, index) in store.currentStreams"
        :key="stream.id ?? `stream-${index}`"
        :stream="stream"
        @click="openMultiView"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useStreamStore, type StreamStatus, type Stream } from '../stores/stream'
import { useOrgStore } from '../stores/org'
import StreamCard from '../components/StreamCard.vue'

const store    = useStreamStore()
const orgStore = useOrgStore()
const router   = useRouter()

const statuses: { value: StreamStatus; label: string }[] = [
  { value: 'live',     label: '直播中' },
  { value: 'upcoming', label: '预约'   },
  { value: 'archive',  label: '录播'   },
  { value: 'offline',  label: '离线'   },
]

const emptyDesc = computed(() => {
  const orgName = store.currentOrgId
    ? orgStore.organizations.find(o => o.id === store.currentOrgId)?.name ?? ''
    : ''
  const suffix = orgName ? `（${orgName}）` : ''
  switch (store.currentStatus) {
    case 'live':     return `等待主播开播${suffix}...`
    case 'upcoming': return `暂无预约直播${suffix}`
    case 'archive':  return `暂无录播${suffix}`
    case 'offline':  return `主播当前离线${suffix}`
    default:         return ''
  }
})

// 带 org 过滤的各 status 计数
function getStatusCount(status: StreamStatus): number {
  const orgId = store.currentOrgId
  const filter = (s: Stream) => orgId === null || (s as any).org_id === orgId
  switch (status) {
    case 'live':     return store.liveStreams.filter(filter).length
    case 'upcoming': return store.upcomingStreams.filter(filter).length
    case 'archive':  return store.archiveStreams.filter(filter).length
    case 'offline':  return store.offlineStreams.filter(filter).length
    default:         return 0
  }
}

// 各机构在当前 status tab 下的直播数
function getOrgCount(orgId: number): number {
  const base = store.streams.filter(s => s.status === store.currentStatus)
  return base.filter(s => (s as any).org_id === orgId).length
}

onMounted(async () => {
  await store.fetchStreams()
  await orgStore.fetchOrganizations()
})

function openMultiView(stream: Stream) {
  if (!stream?.video_id) return
  const channels = [{ platform: stream.platform, id: stream.video_id }]
  localStorage.setItem('multiview_channels', JSON.stringify(channels))
  router.push({ name: 'MultiView' })
}
</script>