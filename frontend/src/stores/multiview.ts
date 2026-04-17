import { defineStore } from 'pinia'
import { computed } from 'vue'
import { debounceFilter, useLocalStorage } from '@vueuse/core'
import { type GridItem, type LayoutChannel, type PresetId } from '@/types/multiview'
import { PRESET_GENERATORS } from '@/utils/presetLayouts'
import { DEFAULT_DANMAKU_SETTINGS, type DanmakuSettings } from '@/types/danmaku'

const STORAGE_KEY = 'multiview_items'
const DANMAKU_SETTINGS_KEY = 'danmaku_settings'
const GRID_COLS = 12

function generateId() {
  return Math.random().toString(36).substring(2, 9)
}

function createEmptyChannel(): LayoutChannel {
  return { platform: 'empty', id: `empty-${generateId()}` }
}


export const useMultiviewStore = defineStore('multiview', () => {
  const items = useLocalStorage<GridItem[]>(STORAGE_KEY, [], {
  })

  const activeChannels = computed<LayoutChannel[]>(() => 
    items.value
      .filter(i => i.channel.platform !== 'empty')
      .map(i => i.channel)
  )


  const danmakuSettings = useLocalStorage<DanmakuSettings>(
    DANMAKU_SETTINGS_KEY,
    DEFAULT_DANMAKU_SETTINGS,
    { eventFilter: debounceFilter(500) }
  )

  function updateDanmakuSettings(partial: Partial<DanmakuSettings>) {
    danmakuSettings.value = { ...danmakuSettings.value, ...partial }
  }

  function resetDanmakuSettings() {
    danmakuSettings.value = { ...DEFAULT_DANMAKU_SETTINGS }
  }

  function findEmptyPosition(w: number, h: number): { x: number, y: number } | null {
    const occupied = new Set<string>()
    items.value.forEach(item => {
      for (let dx = 0; dx < item.w; dx++) {
        for (let dy = 0; dy < item.h; dy++) {
          occupied.add(`${item.x + dx},${item.y + dy}`)
        }
      }
    })

    for (let y = 0; y <= 12 - h; y++) {
      for (let x = 0; x <= GRID_COLS - w; x++) {
        let fits = true
        for (let dx = 0; dx < w && fits; dx++) {
          for (let dy = 0; dy < h && fits; dy++) {
            if (occupied.has(`${x + dx},${y + dy}`)) {
              fits = false
            }
          }
        }
        if (fits) return { x, y }
      }
    }
    return null
  }

function addChannel(channel: LayoutChannel) {
    const currentItems = items.value.filter(i => i.channel.platform !== 'empty');
    const channels = [...currentItems.map(i => i.channel), channel];
    
    const autoPresets: Record<number, PresetId> = {
      1: '1-s', 2: '2-h', 3: '3-1+2', 4: '4-grid',
    };

    const presetId = autoPresets[channels.length];

    if (presetId && PRESET_GENERATORS[presetId]) {
      const newLayout = PRESET_GENERATORS[presetId](channels);
      
      items.value = newLayout.map((newItem, index) => {
        if (index < currentItems.length) {
          return { ...newItem, id: currentItems[index].id };
        }
        return newItem;
      });
    } else {
      const pos = findEmptyPosition(4, 4);
      items.value = [...items.value, { 
        id: generateId(), 
        x: pos?.x ?? 0, 
        y: pos?.y ?? 0, 
        w: 4, 
        h: 4, 
        channel 
      }];
    }
  }


  function closeChannel(nodeId: string) {
    const remainingItems = items.value.filter(item => item.id !== nodeId)
    
    if (remainingItems.length === 0) {
      items.value = []
      return
    }

    const remainingChannels = remainingItems
      .filter(i => i.channel.platform !== 'empty')
      .map(i => ({ ...i.channel }))

    const autoPresets: Record<number, PresetId> = {
      1: '1-s',
      2: '2-h',
      3: '3-1+2',
      4: '4-grid',
    }

    const presetId = autoPresets[remainingChannels.length]

    if (presetId && PRESET_GENERATORS[presetId]) {
      items.value = PRESET_GENERATORS[presetId](remainingChannels)
    } else {
      items.value = remainingItems
    }
  }

  function clearChannel(nodeId: string) {
    const item = items.value.find(i => i.id === nodeId)
    if (item) {
      item.channel = createEmptyChannel()
    }
  }

  function replaceChannel(nodeId: string, channel: LayoutChannel) {
    const item = items.value.find(i => i.id === nodeId)
    if (item) {
      item.channel = channel
    }
  }

  function removeByPlatformId(platform: string, id: string) {
    items.value = items.value.filter(item => 
      !(item.channel.platform === platform && item.channel.id === id)
    )
  }

  function applyPreset(id: PresetId) {
    const currentItems = items.value.filter(i => i.channel.platform !== 'empty');
    const activeChannels = currentItems.map(i => ({ ...i.channel }));

    const generator = PRESET_GENERATORS[id];
    if (generator) {
      const newLayout = generator(activeChannels);
      
      items.value = newLayout.map((newItem, index) => {
        return {
          ...newItem,
          id: currentItems[index]?.id || generateId()
        };
      });
    }
  }

  function buildShareCode(): string {
    const data = items.value.map(item => ({
      x: item.x,
      y: item.y,
      w: item.w,
      h: item.h,
      p: item.channel.platform,
      i: item.channel.id,
    }))
    return btoa(JSON.stringify(data))
  }

  async function copyShareUrl(): Promise<void> {
    const code = buildShareCode()
    const url = `${window.location.origin}/multiview?c=${code}`
    await navigator.clipboard.writeText(url)
  }

  function loadFromShareParam(encoded: string): boolean {
    try {
      const data = JSON.parse(atob(encoded)) as Array<{
        x: number
        y: number
        w: number
        h: number
        p: string
        i: string
      }>

      if (!data.length) return false

      items.value = data.map(d => ({
        id: generateId(),
        x: d.x,
        y: d.y,
        w: d.w,
        h: d.h,
        channel: { platform: d.p as LayoutChannel['platform'], id: d.i },
      }))
      return true
    } catch {
      return false
    }
  }

  function addFromVideoId(platform: 'youtube' | 'bilibili', videoId: string) {
    if (!videoId) return
    const channel: LayoutChannel = { platform, id: videoId }
    
    const alreadyAdded = activeChannels.value.some(
      c => c.id === channel.id && c.platform === channel.platform
    )
    
    if (!alreadyAdded) {
      addChannel(channel)
    }
  }

  function updateItemPosition(id: string, x: number, y: number, w: number, h: number) {
    const item = items.value.find(i => i.id === id)
    if (item) {
      if (item.x === x && item.y === y && item.w === w && item.h === h) return

      item.x = x
      item.y = y
      item.w = w
      item.h = h
    }
  }

  function toggleDanmaku(nodeId: string) {
    const item = items.value.find(i => i.id === nodeId)
    if (item && item.channel) {
      const currentState = item.channel.danmakuEnabled !== false
      item.channel.danmakuEnabled = !currentState
    }
  }

  return {
    items,
    activeChannels,
    danmakuSettings,
    updateDanmakuSettings,
    resetDanmakuSettings,
    addChannel,
    closeChannel,
    clearChannel,
    replaceChannel,
    removeByPlatformId,
    applyPreset,
    copyShareUrl,
    loadFromShareParam,
    addFromVideoId,
    updateItemPosition,
    toggleDanmaku,
  }
})