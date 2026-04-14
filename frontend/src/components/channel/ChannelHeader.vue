<script setup lang="ts">
import { computed } from 'vue'
import { NButton, NTag, NTooltip } from 'naive-ui'
import { 
  Heart, Ban, Youtube, 
  ExternalLink, Globe, Tv 
} from 'lucide-vue-next'

import { useChannelActions } from '@/composables/useChannelActions'
import { useOrganizations } from '@/queries'
import { formatCount } from '@/utils/format'
import { Channel } from '@/types'

interface Props {
  channel: Channel
}

const props = defineProps<Props>()
const orgsQuery = useOrganizations()

const PLATFORM_THEMES: Record<string, { color: string; label: string; icon: any }> = {
  bilibili: { color: '#00aeec', label: 'Bilibili', icon: Tv },
  youtube: { color: '#ff0000', label: 'YouTube', icon: Youtube },
  twitch: { color: '#9146ff', label: 'Twitch', icon: Globe },
  default: { color: '#6366f1', label: 'Unknown', icon: ExternalLink }
}

const theme = computed(() => PLATFORM_THEMES[props.channel.platform] || PLATFORM_THEMES.default)

const { toggleLike, toggleBlock } = useChannelActions(computed(() => props.channel))

const orgName = computed(() => {
  return orgsQuery.data.value?.find(o => o.id === props.channel.org_id)?.name || ''
})

const displaySign = computed(() => {
  return props.channel.bio || props.channel.description || ''
})

const externalUrl = computed(() => {
  if (props.channel.platform === 'bilibili') return `https://space.bilibili.com/${props.channel.channel_id}`
  if (props.channel.youtube_url) return props.channel.youtube_url
  return '#'
})
</script>

<template>
  <div class="relative w-full">
    <div class="h-48 md:h-72 w-full relative overflow-hidden bg-zinc-900">
      <img 
        v-if="channel.banner_url"
        :src="channel.banner_url" 
        class="absolute inset-0 w-full h-full object-cover animate-in fade-in duration-700"
        referrerpolicy="no-referrer"
        alt="banner"
      />
      <div v-else class="absolute inset-0 bg-gradient-to-br from-zinc-800/50 to-zinc-950"></div>
      
      <div class="absolute inset-0 bg-gradient-to-t from-zinc-950 via-zinc-950/20 to-transparent"></div>
    </div>

    <div class="relative px-4 md:px-8 -mt-16 md:-mt-20 pb-4 max-w-[1600px] mx-auto">
      <div class="flex flex-col md:flex-row md:items-end gap-5">
        
        <div class="shrink-0 relative">
          <img
            :src="channel.avatar_url || '/placeholder-avatar.png'"
            class="w-32 h-32 md:w-40 md:h-40 rounded-full border-4 border-zinc-950 object-cover bg-zinc-900 shadow-2xl transition-transform hover:scale-105 duration-300"
            referrerpolicy="no-referrer"
          />
        </div>

        <div class="flex-1 min-w-0 pb-2">
          <div class="flex items-center gap-3 flex-wrap">
            <h1 class="text-2xl md:text-3xl font-bold text-white truncate drop-shadow-md">
              {{ channel.name }}
            </h1>
            <n-tag 
              size="small" 
              round 
              :bordered="false" 
              :style="{ backgroundColor: theme.color, color: '#fff' }"
              class="font-bold shadow-sm"
            >
              <template #icon><component :is="theme.icon" class="w-3 h-3" /></template>
              {{ theme.label }}
            </n-tag>
          </div>

          <div class="flex items-center gap-4 mt-2 text-zinc-400 text-sm flex-wrap">
            <span v-if="orgName" class="flex items-center gap-2 bg-zinc-800/60 px-2 py-0.5 rounded-full border border-zinc-700/50">
              <span class="w-1.5 h-1.5 bg-zinc-500 rounded-full"></span>
              {{ orgName }}
            </span>
            
            <span v-if="channel.platform === 'bilibili' && channel.follower_count" class="flex items-center gap-1">
              粉丝 <strong class="text-zinc-200 font-semibold">{{ formatCount(channel.follower_count) }}</strong>
            </span>

            <span v-if="channel.platform === 'youtube' && channel.subscriber_count" class="flex items-center gap-1">
               订阅 <strong class="text-zinc-200 font-semibold">{{ formatCount(channel.subscriber_count) }}</strong>
            </span>
          </div>

          <p 
            v-if="displaySign" 
            class="mt-4 text-zinc-500 text-sm line-clamp-2 max-w-3xl leading-relaxed italic"
            :title="displaySign"
          >
            {{ displaySign }}
          </p>
        </div>

        <div class="flex items-center gap-2 pb-2 mt-4 md:mt-0">
          <n-button 
            round
            strong
            :type="channel.is_liked ? 'primary' : 'default'" 
            @click="toggleLike"
            class="!px-8 shadow-lg transition-all"
            :color="channel.is_liked ? '#ec4899' : undefined"
          >
            <template #icon>
              <Heart class="w-4 h-4" :class="{ 'fill-current': channel.is_liked }" />
            </template>
            {{ channel.is_liked ? '已喜欢' : '喜欢' }}
          </n-button>

          <n-tooltip trigger="hover">
            <template #trigger>
              <n-button 
                circle 
                secondary 
                :type="channel.is_blocked ? 'error' : 'default'" 
                @click="toggleBlock"
                class="shadow-md"
              >
                <Ban class="w-4 h-4" />
              </n-button>
            </template>
            {{ channel.is_blocked ? '移出黑名单' : '屏蔽该频道' }}
          </n-tooltip>

          <n-tooltip trigger="hover">
            <template #trigger>
              <n-button 
                circle 
                secondary 
                tag="a" 
                :href="externalUrl" 
                target="_blank" 
                class="shadow-md"
              >
                <ExternalLink class="w-4 h-4" />
              </n-button>
            </template>
            在平台打开
          </n-tooltip>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.animate-in {
  animation: fadeIn 0.8s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@media (max-width: 768px) {
  .md\:-mt-20 {
    margin-top: -4rem;
  }
}
</style>