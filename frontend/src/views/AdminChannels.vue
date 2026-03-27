<template>
  <div class="container mx-auto px-4 py-8">
    <div class="mb-8 flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold mb-2">频道管理</h1>
        <p class="text-gray-400">管理 VTuber 频道信息</p>
      </div>
      <button
        @click="showAddModal = true"
        class="px-4 py-2 bg-pink-600 rounded hover:bg-pink-700 transition"
      >
        添加频道
      </button>
    </div>

    <!-- 筛选 -->
    <div class="mb-6 flex flex-wrap gap-4">
      <select v-model="filterPlatform" class="bg-gray-700 border border-gray-600 rounded px-3 py-2">
        <option value="">全部平台</option>
        <option value="youtube">YouTube</option>
        <option value="bilibili">Bilibili</option>
      </select>
      <select v-model="filterActive" class="bg-gray-700 border border-gray-600 rounded px-3 py-2">
        <option value="">全部状态</option>
        <option value="true">启用</option>
        <option value="false">禁用</option>
      </select>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="flex justify-center py-12">
      <div class="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-pink-500"></div>
    </div>

    <!-- 频道列表 -->
    <div v-else class="bg-gray-800 rounded-lg overflow-hidden">
      <table class="w-full">
        <thead class="bg-gray-700">
          <tr>
            <th class="px-4 py-3 text-left text-sm font-medium text-gray-300">头像</th>
            <th class="px-4 py-3 text-left text-sm font-medium text-gray-300">名称</th>
            <th class="px-4 py-3 text-left text-sm font-medium text-gray-300">平台</th>
            <th class="px-4 py-3 text-left text-sm font-medium text-gray-300">Channel ID</th>
            <th class="px-4 py-3 text-left text-sm font-medium text-gray-300">状态</th>
            <th class="px-4 py-3 text-left text-sm font-medium text-gray-300">操作</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-700">
          <tr v-for="channel in filteredChannels" :key="channel.id" class="hover:bg-gray-750">
            <td class="px-4 py-3">
              <img
                v-if="channel.avatar_url"
                :src="channel.avatar_url"
                :alt="channel.name"
                class="w-10 h-10 rounded-full object-cover"
                referrerpolicy="no-referrer"
              />
              <div v-else class="w-10 h-10 rounded-full bg-gray-600 flex items-center justify-center text-gray-300">
                {{ channel.name.charAt(0).toUpperCase() }}
              </div>
            </td>
            <td class="px-4 py-3 text-gray-100">{{ channel.name }}</td>
            <td class="px-4 py-3">
              <span
                class="text-xs px-2 py-1 rounded font-medium"
                :class="channel.platform === 'youtube' ? 'bg-red-600/20 text-red-400' : 'bg-blue-600/20 text-blue-400'"
              >
                {{ channel.platform === 'youtube' ? 'YouTube' : 'Bilibili' }}
              </span>
            </td>
            <td class="px-4 py-3 text-gray-400 text-sm font-mono">{{ channel.channel_id }}</td>
            <td class="px-4 py-3">
              <span
                class="text-xs px-2 py-1 rounded"
                :class="channel.is_active ? 'bg-green-600/20 text-green-400' : 'bg-gray-600/20 text-gray-400'"
              >
                {{ channel.is_active ? '启用' : '禁用' }}
              </span>
            </td>
            <td class="px-4 py-3">
              <button
                @click="editChannel(channel)"
                class="text-blue-400 hover:text-blue-300 mr-3"
              >
                编辑
              </button>
              <button
                @click="deleteChannel(channel.id)"
                class="text-red-400 hover:text-red-300"
              >
                删除
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="filteredChannels.length === 0" class="text-center py-12 text-gray-500">
        暂无频道数据
      </div>
    </div>

    <!-- 添加/编辑弹窗 -->
    <div v-if="showAddModal || showEditModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50" @click.self="closeModal">
      <div class="bg-gray-800 rounded-lg p-6 w-full max-w-md">
        <h2 class="text-xl font-bold mb-4">{{ showEditModal ? '编辑频道' : '添加频道' }}</h2>
        
        <form @submit.prevent="submitForm" class="space-y-4">
          <div>
            <label class="block text-sm text-gray-400 mb-1">平台</label>
            <select v-model="formData.platform" class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2">
              <option value="youtube">YouTube</option>
              <option value="bilibili">Bilibili</option>
            </select>
          </div>
          
          <div>
            <label class="block text-sm text-gray-400 mb-1">Channel ID / @用户名 / URL</label>
            <input
              v-model="formData.channel_id"
              type="text"
              class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2"
              placeholder="UC... / @用户名 / https://youtube.com/@..."
              required
            />
          </div>
          
          <div>
            <label class="block text-sm text-gray-400 mb-1">名称（可选，自动获取）</label>
            <input
              v-model="formData.name"
              type="text"
              class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2"
              placeholder="不填则自动获取"
            />
          </div>
          
          <div>
            <label class="block text-sm text-gray-400 mb-1">头像 URL</label>
            <input
              v-model="formData.avatar_url"
              type="text"
              class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2"
              placeholder="https://..."
            />
          </div>

          <div v-if="showEditModal">
            <label class="flex items-center gap-2 cursor-pointer">
              <input v-model="formData.is_active" type="checkbox" class="w-4 h-4 accent-pink-500">
              <span class="text-sm text-gray-300">启用</span>
            </label>
          </div>
          
          <div class="flex justify-end gap-3 mt-6">
            <button
              type="button"
              @click="closeModal"
              class="px-4 py-2 bg-gray-700 rounded hover:bg-gray-600 transition"
            >
              取消
            </button>
            <button
              type="submit"
              class="px-4 py-2 bg-pink-600 rounded hover:bg-pink-700 transition"
            >
              {{ showEditModal ? '保存' : '添加' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { channelApi, type Channel } from '../api'

const channels = ref<Channel[]>([])
const loading = ref(false)
const filterPlatform = ref('')
const filterActive = ref('')

const showAddModal = ref(false)
const showEditModal = ref(false)
const editingId = ref<number | null>(null)

const formData = ref({
  platform: 'youtube' as 'youtube' | 'bilibili',
  channel_id: '',
  name: '',
  avatar_url: '',
  is_active: true
})

const filteredChannels = computed(() => {
  return channels.value.filter(ch => {
    if (filterPlatform.value && ch.platform !== filterPlatform.value) return false
    if (filterActive.value && ch.is_active !== (filterActive.value === 'true')) return false
    return true
  })
})

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

function editChannel(channel: Channel) {
  editingId.value = channel.id
  formData.value = {
    platform: channel.platform,
    channel_id: channel.channel_id,
    name: channel.name,
    avatar_url: channel.avatar_url || '',
    is_active: channel.is_active
  }
  showEditModal.value = true
}

async function deleteChannel(id: number) {
  if (!confirm('确定要删除这个频道吗？')) return
  
  try {
    await channelApi.delete(id)
    await fetchChannels()
  } catch (err) {
    console.error('Failed to delete channel:', err)
    alert('删除失败')
  }
}

function closeModal() {
  showAddModal.value = false
  showEditModal.value = false
  editingId.value = null
  formData.value = {
    platform: 'youtube',
    channel_id: '',
    name: '',
    avatar_url: '',
    is_active: true
  }
}

async function submitForm() {
  try {
    const data = {
      platform: formData.value.platform,
      channel_id: formData.value.channel_id,
      name: formData.value.name,
      avatar_url: formData.value.avatar_url || null,
      is_active: formData.value.is_active
    }

    if (showEditModal.value && editingId.value) {
      await channelApi.update(editingId.value, data)
    } else {
      await channelApi.create(data)
    }
    
    await fetchChannels()
    closeModal()
  } catch (err: any) {
    console.error('Failed to save channel:', err)
    alert(err.response?.data?.detail || '保存失败')
  }
}

onMounted(() => {
  fetchChannels()
})
</script>
