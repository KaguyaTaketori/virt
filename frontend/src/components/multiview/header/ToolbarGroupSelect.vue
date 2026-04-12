<script setup lang="ts">
import { computed } from 'vue'
import { Star, ChevronDown } from 'lucide-vue-next'
import { NPopover } from 'naive-ui'

type GroupType = 'favorites' | number

const props = defineProps<{
  selectedGroup: GroupType | null
  organizationName: string | null
  membersCount: number
}>()

const emit = defineEmits(['select', 'openSelector'])

const groupLabel = computed(() => {
  if (props.selectedGroup === 'favorites') return '收藏夹'
  if (typeof props.selectedGroup === 'number') return props.organizationName || `机构 ${props.selectedGroup}`
  return '选择分组'
})
</script>

<template>
  <n-popover trigger="click" placement="bottom-start" :show-arrow="false">
    <template #trigger>
      <button class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-zinc-800 hover:bg-zinc-700 text-xs text-zinc-300 transition-colors shrink-0">
        <span>{{ groupLabel }}</span>
        <span v-if="selectedGroup" class="text-zinc-500">({{ membersCount }})</span>
        <ChevronDown class="w-3 h-3 opacity-50" />
      </button>
    </template>
    
    <div class="bg-zinc-900 border border-zinc-700 rounded-lg shadow-xl overflow-hidden min-w-[140px]">
      <button @click="emit('select', 'favorites')" class="w-full flex items-center gap-2 px-3 py-2.5 text-left text-sm text-zinc-300 hover:bg-zinc-800 transition-colors border-b border-zinc-800">
        <Star class="w-4 h-4 text-amber-400" />
        <span>收藏夹</span>
      </button>
      <button @click="emit('openSelector')" class="w-full flex items-center gap-2 px-3 py-2.5 text-left text-sm text-zinc-300 hover:bg-zinc-800 transition-colors">
        <div class="w-4 h-4 rounded-full border border-zinc-500" />
        <span>全部机构</span>
      </button>
    </div>
  </n-popover>
</template>