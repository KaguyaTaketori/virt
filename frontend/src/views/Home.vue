<template>
  <div class="container mx-auto px-4 py-8">
    <div class="mb-6">
      <h1 class="text-3xl font-bold mb-1">直播列表</h1>
      <p class="text-gray-400 text-sm">VTuber 频道直播状态</p>
    </div>

    <div v-if="orgsQuery.data.value?.length" class="mb-4 flex flex-wrap gap-2 items-center">
      <button
        @click="selectedOrgId = null"
        class="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm transition"
        :class="selectedOrgId === null
          ? 'bg-pink-600 text-white'
          : 'bg-gray-700 text-gray-300 hover:bg-gray-600'"
      >
        全部
      </button>
      <button
        v-for="org in orgsQuery.data.value"
        :key="org.id"
        @click="selectedOrgId = org.id"
        class="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm transition"
        :class="selectedOrgId === org.id
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
        @click="selectedStatus = s.value"
        class="px-4 py-2 rounded-full transition text-sm"
        :class="selectedStatus === s.value
          ? 'bg-pink-600 text-white'
          : 'bg-gray-700 text-gray-300 hover:bg-gray-600'"
      >
        {{ s.label }}
        <span class="ml-1 opacity-70">({{ statusCountMap[s.value] }})</span>
      </button>
    </div>

    <div v-if="streamsQuery.isLoading.value" class="flex justify-center py-16">
      <div class="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-pink-500"></div>
    </div>

    <div v-else-if="streamsQuery.isError.value" class="text-center py-12 text-red-400">
      <p>加载失败：{{ streamsQuery.error.value?.message }}</p>
      <button @click="streamsQuery.refetch()" class="mt-4 px-4 py-2 bg-pink-600 rounded hover:bg-pink-700 text-sm">
        重试
      </button>
    </div>

    <div v-else-if="filteredStreams.length === 0" class="text-center py-16 text-gray-500">
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
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
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

const filteredStreams = computed(() => {
  const streams = currentStreams.value
  if (authStore.canAccessBilibili) return streams
  return streams.filter(s => s.platform !== 'bilibili')
})

const statuses: { value: StreamStatus; label: string }[] = [
  { value: 'live',     label: '直播中' },
  { value: 'upcoming', label: '预约'   },
  { value: 'archive',  label: '录播'   },
  { value: 'offline',  label: '离线'   },
]

const currentStreams = computed(() => {
  const all = streamsQuery.data.value ?? []
  const byStatus = all.filter(s => s.status === selectedStatus.value)
  if (selectedOrgId.value === null) return byStatus
  return byStatus.filter(s => (s as any).org_id === selectedOrgId.value)
})

const statusCountMap = computed<Record<StreamStatus, number>>(() => {
  const all = streamsQuery.data.value ?? []
  return {
    live:     all.filter(s => s.status === 'live' && orgFilter(s)).length,
    upcoming: all.filter(s => s.status === 'upcoming' && orgFilter(s)).length,
    archive:  all.filter(s => s.status === 'archive' && orgFilter(s)).length,
    offline:  all.filter(s => s.status === 'offline' && orgFilter(s)).length,
  }
})

function orgFilter(s: Stream) {
  return selectedOrgId.value === null || (s as any).org_id === selectedOrgId.value
}

const orgCountMap = computed<Record<number, number>>(() => {
  const all = streamsQuery.data.value ?? []
  const byStatus = all.filter(s => s.status === selectedStatus.value)
  const result: Record<number, number> = {}
  for (const org of orgsQuery.data.value ?? []) {
    result[org.id] = byStatus.filter((s) => (s as any).org_id === org.id).length
  }
  return result
})

const emptyDesc = computed(() => {
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

function openMultiView(stream: Stream) {
  if (!stream?.video_id) return
  multiviewStore.addFromVideoId(stream.platform, stream.video_id)
  router.push({ name: 'MultiView' })
}
</script>