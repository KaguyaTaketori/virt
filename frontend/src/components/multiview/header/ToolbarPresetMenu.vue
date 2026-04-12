<script setup lang="ts">
import { computed } from 'vue'
import { LayoutTemplate, Maximize2 } from 'lucide-vue-next'
import { NPopover } from 'naive-ui'
import { type PresetId, PRESET_META } from '@/utils/presetLayouts'

const props = defineProps<{ channelCount: number }>()
const emit = defineEmits(['apply', 'openLibrary'])

const recommendations = computed(() => {
  const n = props.channelCount
  let ids: PresetId[] = n <= 1 ? ['1-s'] : n === 2 ? ['2-h', '2-v'] : n === 3 ? ['3-1+2', '3-cols'] : ['4-grid', '4-1+3']
  return ids.map(id => ({ id, label: PRESET_META[id].label }))
})
</script>

<template>
  <n-popover trigger="click" placement="bottom" style="background-color: #18181b; border: 1px solid #3f3f46; color: white; width: 220px;">
    <template #trigger>
      <button class="flex items-center gap-1 p-2 rounded-md text-zinc-400 hover:text-rose-400 hover:bg-zinc-800 transition-all">
        <LayoutTemplate class="w-4 h-4" />
        <span class="text-[10px] font-bold">布局预设</span>
      </button>
    </template>
    
    <div class="p-2 space-y-1">
      <div class="text-[9px] text-zinc-500 font-bold mb-2 uppercase tracking-tighter">适合当前 ({{ channelCount }}) 窗</div>
      
      <button v-for="opt in recommendations" :key="opt.id" @click="emit('apply', opt.id)" class="w-full flex items-center gap-3 px-2 py-2 rounded hover:bg-zinc-800 text-zinc-400 hover:text-white transition-colors text-left">
        <div class="w-8 h-5 bg-zinc-900 border border-zinc-700 rounded flex p-0.5 gap-0.5">
            <div class="flex-1 bg-zinc-600/50"></div>
            <div v-if="opt.id !== '1-s'" class="flex-1 bg-zinc-600/50"></div>
        </div>
        <span class="text-xs">{{ opt.label }}</span>
      </button>

      <div class="h-px bg-zinc-800 my-2"></div>
      <button @click="emit('openLibrary')" class="w-full flex items-center justify-center gap-2 py-2 text-[10px] text-zinc-500 hover:text-white hover:bg-zinc-800 rounded border border-dashed border-zinc-700 transition-all">
        <Maximize2 class="w-3 h-3" />
        <span>预设库</span>
      </button>
    </div>
  </n-popover>
</template>