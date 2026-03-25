<template>
  <div class="container mx-auto px-4 py-8">
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold">多窗播放</h1>
        <p class="text-gray-400 text-sm mt-1">同时观看多个直播</p>
      </div>
      <button 
        @click="$router.back()" 
        class="px-4 py-2 bg-gray-700 rounded hover:bg-gray-600 transition"
      >
        返回
      </button>
    </div>

    <div class="bg-gray-800 rounded-lg p-4 mb-6">
      <div class="flex flex-wrap gap-4 items-center">
        <div class="flex-1 min-w-[200px]">
          <label class="block text-sm text-gray-400 mb-2">添加频道</label>
          <div class="flex gap-2">
            <select v-model="newChannel.platform" class="bg-gray-700 border border-gray-600 rounded px-3 py-2">
              <option value="youtube">YouTube</option>
              <option value="bilibili">Bilibili</option>
            </select>
            <input 
              v-model="newChannel.id" 
              type="text" 
              placeholder="视频ID/房间ID"
              class="bg-gray-700 border border-gray-600 rounded px-3 py-2 flex-1"
            />
            <button 
              @click="addChannel" 
              class="px-4 py-2 bg-pink-600 rounded hover:bg-pink-700 transition"
            >
              添加
            </button>
          </div>
        </div>
      </div>

      <div class="mt-4 flex flex-wrap gap-2">
        <span 
          v-for="(ch, idx) in channels" 
          :key="idx"
          class="inline-flex items-center gap-2 px-3 py-1 bg-gray-700 rounded-full"
        >
          <span class="text-sm">{{ ch.platform }}: {{ ch.id }}</span>
          <button 
            @click="removeChannel(idx)" 
            class="text-gray-400 hover:text-red-400"
          >
            ×
          </button>
        </span>
      </div>
    </div>

    <div 
      class="grid gap-4"
      :style="gridStyle"
    >
      <div 
        v-for="(ch, idx) in channels" 
        :key="idx"
        class="relative bg-black rounded-lg overflow-hidden"
        style="aspect-ratio: 16/9;"
      >
        <iframe
          v-if="getEmbedUrl(ch)"
          :src="getEmbedUrl(ch)"
          class="absolute inset-0 w-full h-full"
          frameborder="0"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowfullscreen
        ></iframe>
        <div v-else class="flex items-center justify-center h-full text-gray-500">
          无效的嵌入链接
        </div>
      </div>
    </div>

    <div v-if="channels.length === 0" class="text-center py-12 text-gray-500">
      <p class="text-xl">添加频道开始多窗观看</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const newChannel = ref({
  platform: 'youtube',
  id: ''
})

const channels = ref([])

const gridStyle = computed(() => {
  const count = channels.value.length
  if (count <= 1) return { gridTemplateColumns: '1fr' }
  if (count <= 2) return { gridTemplateColumns: 'repeat(2, 1fr)' }
  if (count <= 4) return { gridTemplateColumns: 'repeat(2, 1fr)' }
  return { gridTemplateColumns: 'repeat(3, 1fr)' }
})

function getEmbedUrl(ch) {
  if (ch.platform === 'youtube') {
    return `https://www.youtube.com/embed/${ch.id}`
  } else if (ch.platform === 'bilibili') {
    return `https://player.bilibili.com/player.html?roomid=${ch.id}&autoplay=1`
  }
  return null
}

function addChannel() {
  if (!newChannel.value.id) return
  channels.value.push({ ...newChannel.value })
  newChannel.value.id = ''
}

function removeChannel(idx) {
  channels.value.splice(idx, 1)
}

onMounted(() => {
  const { platform, ids } = route.params
  if (platform && ids) {
    const idList = ids.split(',')
    idList.forEach(id => {
      channels.value.push({ platform, id: id.trim() })
    })
  }
})
</script>