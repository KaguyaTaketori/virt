<script setup lang="ts">
import { computed, defineAsyncComponent, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuery } from '@tanstack/vue-query'
import { useRouteQuery } from '@vueuse/router'
import { NSpin, NButton, NEmpty } from 'naive-ui'

import { channelApi } from '@/api'
import ChannelHeader from '@/components/channel/ChannelHeader.vue'

// 1. 动态导入 Feed 组件
const PLATFORM_FEEDS: Record<string, any> = {
  bilibili: defineAsyncComponent(() => import('@/components/channel/BilibiliFeed.vue')),
  youtube: defineAsyncComponent(() => import('@/components/channel/YoutubeFeed.vue')),
}

// 2. Tab 配置映射 (按平台定义不同的 Tab)
const PLATFORM_TABS: Record<string, { value: string; label: string }[]> = {
  bilibili: [
    { value: 'videos', label: '投稿' },
    { value: 'dynamics', label: '动态' },
    { value: 'home', label: '主页' }
  ],
  youtube: [
    { value: 'live', label: '直播' },
    { value: 'videos', label: '视频' },
    { value: 'shorts', label: 'Shorts' },
    { value: 'streams', label: '关于' }
  ]
}

const route = useRoute()
const router = useRouter()
const channelId = computed(() => route.params.id as string)

const { data: channel, isLoading, error: queryError } = useQuery({
  queryKey: ['channel', channelId],
  queryFn: async () => {
    const { data } = await channelApi.get(channelId.value)
    return data
  },
  enabled: computed(() => !!channelId.value),
  staleTime: 300_000
})

const platform = computed(() => channel.value?.platform || 'unknown')
const currentFeedComponent = computed(() => PLATFORM_FEEDS[platform.value])

// 获取当前平台应有的 Tab 列表
const tabs = computed(() => PLATFORM_TABS[platform.value] || [])

// 3. Tab 状态管理 (同步到 URL)
const activeTab = useRouteQuery<string>('tab', 'videos')

// 安全检查：如果切换平台后旧的 tab 不存在于新平台，自动切换到第一个可用 tab
watch(platform, (newPlatform) => {
  const availableTabs = PLATFORM_TABS[newPlatform] || []
  if (availableTabs.length > 0 && !availableTabs.find(t => t.value === activeTab.value)) {
    activeTab.value = availableTabs[0].value
  }
})

const authError = computed(() => {
  const err = queryError.value as any
  if (err?.response?.status === 403 || err?.response?.status === 401) {
    return {
      message: err.response.data?.detail || '访问此平台内容需要登录授权',
      type: 'auth'
    }
  }
  return null
})

function goToLogin() {
  router.push({ name: 'Login', query: { redirect: route.fullPath } })
}
</script>

<template>
  <div class="min-h-screen bg-zinc-950 text-zinc-200">
    <div v-if="isLoading" class="flex justify-center py-24">
      <n-spin size="large" stroke="#ec4899" />
    </div>

    <div v-else-if="authError" class="flex flex-col items-center justify-center py-24">
      <div class="bg-zinc-900 p-8 rounded-xl border border-zinc-800 max-w-md text-center">
        <h3 class="text-xl font-bold text-yellow-500 mb-3">权限受限</h3>
        <p class="text-zinc-400 mb-6">{{ authError.message }}</p>
        <n-button type="primary" color="#ec4899" @click="goToLogin">前往登录 / 授权</n-button>
      </div>
    </div>

    <div v-else-if="channel">
      <!-- 头部：Banner, 头像, 关注/屏蔽 -->
      <ChannelHeader :channel="channel" />

      <!-- 4. Tab 导航栏 (补全部分) -->
      <div class="sticky top-0 bg-zinc-950/80 backdrop-blur-md z-20 border-b border-zinc-800 px-4 md:px-8">
        <div class="max-w-[1600px] mx-auto">
          <nav class="flex gap-2">
            <button
              v-for="tab in tabs" :key="tab.value"
              @click="activeTab = tab.value"
              :class="[
                'px-4 py-4 text-sm font-medium transition-all relative whitespace-nowrap',
                activeTab === tab.value ? 'text-white' : 'text-zinc-500 hover:text-zinc-300'
              ]"
            >
              {{ tab.label }}
              <!-- 选中时的底部粉色条 -->
              <div 
                v-if="activeTab === tab.value" 
                class="absolute bottom-0 left-0 right-0 h-0.5 bg-pink-500"
              ></div>
            </button>
          </nav>
        </div>
      </div>

      <!-- 内容区 -->
      <main class="max-w-[1600px] mx-auto px-4 md:px-8 py-6">
        <component 
          :is="currentFeedComponent"
          v-if="currentFeedComponent"
          :channel-id="channelId"
          :channel-data="channel"
          v-model:active-tab="activeTab"
        />
        
        <div v-else class="py-24 text-center">
          <n-empty description="该平台组件尚未对接" />
        </div>
      </main>
    </div>

    <div v-else class="text-center py-24 text-zinc-500">
      未找到频道信息或服务器异常
    </div>
  </div>
</template>

<style scoped>
/* 隐藏移动端滚动条但保留滚动功能 */
nav::-webkit-scrollbar {
  display: none;
}
nav {
  -ms-overflow-style: none;
  scrollbar-width: none;
  overflow-x: auto;
}
</style>