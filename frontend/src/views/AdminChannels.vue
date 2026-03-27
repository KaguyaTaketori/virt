<template>
  <div class="container mx-auto px-4 py-8">
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold mb-2">频道管理</h1>
        <p class="text-gray-400">管理 VTuber 频道信息</p>
      </div>
      <n-button type="primary" @click="showAddModal = true">
        添加频道
      </n-button>
    </div>

    <!-- 筛选 -->
    <div class="mb-4 flex flex-wrap gap-4">
      <n-select
        v-model:value="filterPlatform"
        placeholder="全部平台"
        :options="platformOptions"
        clearable
        style="width: 150px"
      />
      <n-select
        v-model:value="filterActive"
        placeholder="全部状态"
        :options="statusOptions"
        clearable
        style="width: 150px"
      />
      <n-input
        v-model:value="searchText"
        placeholder="搜索名称..."
        clearable
        style="width: 200px"
      />
    </div>

    <!-- 表格 -->
    <n-data-table
      :columns="columns"
      :data="filteredChannels"
      :loading="loading"
      :row-key="(row: Channel) => row.id"
      :pagination="pagination"
      :bordered="false"
    />

    <!-- 添加/编辑弹窗 -->
    <n-modal
      v-model:show="showAddModal"
      preset="card"
      title="添加频道"
      style="width: 500px"
    >
      <n-form ref="formRef" :model="formData" :rules="formRules">
        <n-form-item label="平台" path="platform">
          <n-select v-model:value="formData.platform" :options="platformOptions" />
        </n-form-item>
        <n-form-item label="Channel ID" path="channel_id">
          <n-input v-model:value="formData.channel_id" placeholder="UC... / @用户名 / URL" />
        </n-form-item>
        <n-form-item label="名称（可选，自动获取）">
          <n-input v-model:value="formData.name" placeholder="不填则自动获取" />
        </n-form-item>
        <n-form-item label="头像 URL">
          <n-input v-model:value="formData.avatar_url" placeholder="https://..." />
        </n-form-item>
        <n-form-item label="头像形状">
          <n-radio-group v-model:value="formData.avatar_shape">
            <n-space>
              <n-radio value="circle">圆形</n-radio>
              <n-radio value="square">方形</n-radio>
            </n-space>
          </n-radio-group>
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showAddModal = false">取消</n-button>
          <n-button type="primary" @click="submitForm">添加</n-button>
        </n-space>
      </template>
    </n-modal>

    <n-modal
      v-model:show="showEditModal"
      preset="card"
      title="编辑频道"
      style="width: 500px"
    >
      <n-form ref="formRef" :model="formData" :rules="formRules">
        <n-form-item label="平台" path="platform">
          <n-select v-model:value="formData.platform" :options="platformOptions" />
        </n-form-item>
        <n-form-item label="Channel ID" path="channel_id">
          <n-input v-model:value="formData.channel_id" placeholder="UC..." />
        </n-form-item>
        <n-form-item label="名称">
          <n-input v-model:value="formData.name" />
        </n-form-item>
        <n-form-item label="头像 URL">
          <n-input v-model:value="formData.avatar_url" />
        </n-form-item>
        <n-form-item label="头像形状">
          <n-radio-group v-model:value="formData.avatar_shape">
            <n-space>
              <n-radio value="circle">圆形</n-radio>
              <n-radio value="square">方形</n-radio>
            </n-space>
          </n-radio-group>
        </n-form-item>
        <n-form-item>
          <n-checkbox v-model:checked="formData.is_active">启用</n-checkbox>
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="closeModal">取消</n-button>
          <n-button type="primary" @click="submitForm">保存</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, h } from 'vue'
import { NButton, NSelect, NInput, NModal, NForm, NFormItem, NSpace, NCheckbox, NTag, NRadio, NRadioGroup, type DataTableColumns } from 'naive-ui'
import { channelApi, type Channel } from '../api'

const channels = ref<Channel[]>([])
const loading = ref(false)
const filterPlatform = ref<string | null>(null)
const filterActive = ref<string | null>(null)
const searchText = ref('')

const showAddModal = ref(false)
const showEditModal = ref(false)
const editingId = ref<number | null>(null)

const formData = ref({
  platform: 'youtube' as 'youtube' | 'bilibili',
  channel_id: '',
  name: '',
  avatar_url: '',
  is_active: true,
  avatar_shape: 'circle'
})

const formRules = {
  channel_id: { required: true, message: '请输入 Channel ID', trigger: 'blur' }
}

const platformOptions = [
  { label: 'YouTube', value: 'youtube' },
  { label: 'Bilibili', value: 'bilibili' }
]

const statusOptions = [
  { label: '启用', value: 'true' },
  { label: '禁用', value: 'false' }
]

const pagination = {
  pageSize: 20
}

const filteredChannels = computed(() => {
  return channels.value.filter(ch => {
    if (filterPlatform.value && ch.platform !== filterPlatform.value) return false
    if (filterActive.value && String(ch.is_active) !== filterActive.value) return false
    if (searchText.value && !ch.name.toLowerCase().includes(searchText.value.toLowerCase())) return false
    return true
  })
})

const columns: DataTableColumns<Channel> = [
  {
    title: '头像',
    key: 'avatar_url',
    width: 80,
    render: (row) => h('img', {
      src: row.avatar_url || '',
      style: row.avatar_shape === 'square'
        ? 'width: 40px; height: 40px; border-radius: 8px; object-fit: contain;'
        : 'width: 40px; height: 40px; border-radius: 50%; object-fit: cover;',
      referrerPolicy: 'no-referrer'
    })
  },
  {
    title: '名称',
    key: 'name',
    sorter: (a, b) => a.name.localeCompare(b.name)
  },
  {
    title: '平台',
    key: 'platform',
    width: 120,
    sorter: (a, b) => a.platform.localeCompare(b.platform),
    render: (row) => h(NTag, {
      type: row.platform === 'youtube' ? 'error' : 'info',
      size: 'small'
    }, { default: () => row.platform === 'youtube' ? 'YouTube' : 'Bilibili' })
  },
  {
    title: 'Channel ID',
    key: 'channel_id',
    render: (row) => h('code', { style: 'font-size: 12px; color: #888;' }, row.channel_id)
  },
  {
    title: '状态',
    key: 'is_active',
    width: 100,
    sorter: (a, b) => (a.is_active ? 1 : 0) - (b.is_active ? 1 : 0),
    render: (row) => h(NTag, {
      type: row.is_active ? 'success' : 'default',
      size: 'small'
    }, { default: () => row.is_active ? '启用' : '禁用' })
  },
  {
    title: '操作',
    key: 'actions',
    width: 150,
    render: (row) => h(NSpace, { size: 'small' }, {
      default: () => [
        h(NButton, {
          size: 'small',
          type: 'info',
          onClick: () => editChannel(row)
        }, { default: () => '编辑' }),
        h(NButton, {
          size: 'small',
          type: 'error',
          onClick: () => deleteChannel(row.id)
        }, { default: () => '删除' })
      ]
    })
  }
]

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
    is_active: channel.is_active,
    avatar_shape: channel.avatar_shape || 'circle'
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
    is_active: true,
    avatar_shape: 'circle'
  }
}

async function submitForm() {
  try {
    const data = {
      platform: formData.value.platform,
      channel_id: formData.value.channel_id,
      name: formData.value.name,
      avatar_url: formData.value.avatar_url || null,
      is_active: formData.value.is_active,
      avatar_shape: formData.value.avatar_shape
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
