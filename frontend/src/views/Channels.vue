<template>
  <div class="container mx-auto px-4 py-8">
    <div class="mb-6">
      <h1 class="text-3xl font-bold mb-1">频道</h1>
      <p class="text-gray-400 text-sm">VTuber 频道列表</p>
    </div>

    <!-- 机构筛选 -->
    <div v-if="orgStore.organizations.length > 0" class="mb-6 flex flex-wrap gap-2 items-center">
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
        v-for="org in orgStore.organizations"
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
      </button>
    </div>

    <!-- 平台筛选 -->
    <div class="mb-6 flex flex-wrap gap-2">
      <button
        v-for="p in platforms"
        :key="p.value"
        @click="selectedPlatform = p.value"
        class="px-4 py-2 rounded-full transition text-sm"
        :class="selectedPlatform === p.value
          ? 'bg-pink-600 text-white'
          : 'bg-gray-700 text-gray-300 hover:bg-gray-600'"
      >
        {{ p.label }}
      </button>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="flex justify-center py-16">
      <div class="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-pink-500"></div>
    </div>

    <!-- 频道列表 -->
    <div v-else-if="filteredChannels.length > 0" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
      <div
        v-for="channel in filteredChannels"
        :key="channel.id"
        @click="goToChannel(channel)"
        class="group cursor-pointer"
      >
        <div class="relative aspect-square mb-3">
          <img
            :src="channel.avatar_url || '/placeholder-avatar.png'"
            class="w-full h-full object-cover rounded-full border-2 border-transparent group-hover:border-pink-500 transition-colors"
            referrerpolicy="no-referrer"
          />
          <div
            v-if="channel.platform === 'youtube'"
            class="absolute bottom-1 right-1 w-5 h-5 bg-red-600 rounded-full flex items-center justify-center"
          >
            <svg class="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 24 24">
              <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
            </svg>
          </div>
          <div
            v-else
            class="absolute bottom-1 right-1 w-5 h-5 bg-blue-500 rounded-full flex items-center justify-center"
          >
            <span class="text-white text-[10px] font-bold">B</span>
          </div>
        </div>
        <h3 class="text-sm font-medium text-white text-center truncate group-hover:text-pink-400 transition-colors">
          {{ channel.name }}
        </h3>
        <p class="text-xs text-gray-500 text-center truncate mt-0.5">
          {{ getOrgName(channel.org_id) }}
        </p>
      </div>
    </div>

    <div v-else class="text-center py-16 text-gray-500">
      <p class="text-lg">暂无频道数据</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useOrgStore } from '../stores/org'
import { channelApi, type Channel } from '../api'

const router = useRouter()
const orgStore = useOrgStore()

const channels = ref<Channel[]>([])
const loading = ref(false)
const selectedOrgId = ref<number | null>(null)
const selectedPlatform = ref<string>('all')

const platforms = [
  { value: 'all', label: '全部' },
  { value: 'youtube', label: 'YouTube' },
  { value: 'bilibili', label: 'Bilibili' }
]

const filteredChannels = computed(() => {
  return channels.value.filter(ch => {
    if (selectedOrgId.value !== null && ch.org_id !== selectedOrgId.value) return false
    if (selectedPlatform.value !== 'all' && ch.platform !== selectedPlatform.value) return false
    return true
  })
})

function getOrgName(orgId: number | null): string {
  if (!orgId) return '未归属'
  const org = orgStore.organizations.find(o => o.id === orgId)
  return org?.name || '未知机构'
}

function goToChannel(channel: any) {
  router.push(`/channel/${channel.channel_id}`)
}

async function fetchChannels() {
  loading.value = true
  try {
    const { data } = await channelApi.getAll()
    channels.value = data
  } catch (err) {
    console.error('Failed to fetch channels:', err)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await Promise.all([
    fetchChannels(),
    orgStore.fetchOrganizations()
  ])
})
</script>
