<script setup lang="ts">
import { CirclePlus } from 'lucide-vue-next'
import { NTooltip } from 'naive-ui'
import type { Stream } from '@/api'

const props = defineProps<{
  members: Stream[]
  hasSelectedGroup: boolean
}>()

const emit = defineEmits(['add', 'openAddModal'])

function formatLiveDuration(startedAt: string | null): string {
  if (!startedAt) return ''
  const diffMins = Math.floor((new Date().getTime() - new Date(startedAt).getTime()) / 60000)
  return diffMins < 60 ? `${diffMins}m` : `${Math.floor(diffMins / 60)}h`
}
</script>

<template>
  <div class="flex-1 min-w-0 flex items-center overflow-x-auto scrollbar-none gap-2">
    <n-tooltip v-for="member in members.slice(0, 15)" :key="member.id" placement="bottom">
      <template #trigger>
        <button @click="emit('add', member)" class="relative shrink-0 group">
          <img v-if="member.channel_avatar" :src="member.channel_avatar" class="w-10 h-10 rounded-full border-2 border-transparent group-hover:border-rose-500 transition-all object-cover" referrerpolicy="no-referrer" />
          <div v-else class="w-10 h-10 rounded-full bg-zinc-800 flex items-center justify-center text-zinc-500 font-bold">?</div>
          <span v-if="member.started_at" class="absolute -top-1 -right-1 bg-rose-500 text-white text-[9px] px-1.5 rounded-full shadow-sm">{{ formatLiveDuration(member.started_at) }}</span>
        </button>
      </template>
      <span class="text-xs">{{ member.channel_name }}</span>
    </n-tooltip>

    <button @click="emit('openAddModal')" class="p-1.5 rounded-md text-rose-400 hover:bg-zinc-800 transition-colors shrink-0">
      <CirclePlus class="w-5 h-5" />
    </button>

    <div v-if="!hasSelectedGroup" class="text-xs text-zinc-600 italic whitespace-nowrap">选择分组查看成员</div>
    <div v-else-if="members.length === 0" class="text-xs text-zinc-600 italic whitespace-nowrap">暂无直播</div>
  </div>
</template>