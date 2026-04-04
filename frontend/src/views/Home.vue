<template>
  <div class="container mx-auto px-4 py-8">
    <div class="mb-6">
      <h1 class="text-3xl font-bold mb-1">直播列表</h1>
      <p class="text-gray-400 text-sm">VTuber 频道直播状态</p>
    </div>

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
        <span class="opacity-60 text-xs">({{ orgCountMap[org.id] ?? 0 }})</span>
      </button>
    </div>

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
        <span class="ml-1 opacity-70">({{ statusCountMap[s.value] }})</span>
      </button>
    </div>

    <div v-if="store.loading" class="flex justify-center py-16">
      <div class="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-pink-500"></div>
    </div>

    <div v-else-if="store.error" class="text-center py-12 text-red-400">
      <p>加载失败：{{ store.error }}</p>
      <button @click="store.fetchStreams()" class="mt-4 px-4 py-2 bg-pink-600 rounded hover:bg-pink-700 text-sm">
        重试
      </button>
    </div>

    <div v-else-if="store.currentStreams.length === 0" class="text-center py-16 text-gray-500">
      <p class="text-lg">暂无数据</p>
      <p class="mt-1 text-sm">{{ emptyDesc }}</p>
    </div>

    <div v-else class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-5">
      <StreamCard
        v-for="(stream, index) in filteredStreams"
        :key="stream.id ?? `stream-${index}`"
        :stream="stream"
        @click="openMultiView(stream)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useStreamStore, type StreamStatus, type Stream } from '@/stores/stream'
import { useOrgStore } from '@/stores/org'
import { useAuthStore } from '@/stores/auth'
import { useMultiviewStore } from '@/stores/multiview'
import StreamCard from '@/components/StreamCard.vue'


const store    = useStreamStore()
const multiviewStore = useMultiviewStore()
const orgStore = useOrgStore()
const authStore = useAuthStore()
const router   = useRouter()

const filteredStreams = computed(() => {
  const streams = store.currentStreams
  if (authStore.canAccessBilibili) return streams
  return streams.filter(s => s.platform !== 'bilibili')
})

const statuses: { value: StreamStatus; label: string }[] = [
  { value: 'live',     label: '直播中' },
  { value: 'upcoming', label: '预约'   },
  { value: 'archive',  label: '录播'   },
  { value: 'offline',  label: '离线'   },
]

const statusCountMap = computed<Record<StreamStatus, number>>(() => {
  const orgId = store.currentOrgId
  const byOrg = (s: Stream) => orgId === null || (s as any).org_id === orgId
 
  return {
    live:     store.liveStreams.filter(byOrg).length,
    upcoming: store.upcomingStreams.filter(byOrg).length,
    archive:  store.archiveStreams.filter(byOrg).length,
    offline:  store.offlineStreams.filter(byOrg).length,
  }
})
 
const orgCountMap = computed<Record<number, number>>(() => {
  const base = store.streams.filter((s) => s.status === store.currentStatus)
  const result: Record<number, number> = {}
  for (const org of orgStore.organizations) {
    result[org.id] = base.filter((s) => (s as any).org_id === org.id).length
  }
  return result
})

const emptyDesc = computed(() => {
  const orgName = store.currentOrgId
    ? orgStore.organizations.find((o) => o.id === store.currentOrgId)?.name ?? ''
    : ''
  const suffix = orgName ? `（${orgName}）` : ''
  const map: Record<StreamStatus, string> = {
    live:     `等待主播开播${suffix}...`,
    upcoming: `暂无预约直播${suffix}`,
    archive:  `暂无录播${suffix}`,
    offline:  `主播当前离线${suffix}`,
  }
  return map[store.currentStatus] ?? ''
})

onMounted(async () => {
  await store.fetchStreams()
  await orgStore.fetchOrganizations()
})

function openMultiView(stream: Stream) {
  if (!stream?.video_id) return
  multiviewStore.addFromVideoId(stream.platform, stream.video_id)
  router.push({ name: 'MultiView' })
}
</script>