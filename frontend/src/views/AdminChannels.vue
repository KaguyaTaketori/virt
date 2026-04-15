<template>
  <AdminCrudTable
    ref="tableRef"
    title="频道管理"
    description="管理 VTuber 频道信息"
    add-label="添加频道"
    :columns="columns"
    :data="filteredChannels"
    :loading="loading"
    :row-key="(row: Channel) => row.id"
    :pagination="pagination"
    @add="openAddModal"
    @submit="handleConfirm"
  >
    <!-- 1. 筛选插槽 -->
    <template #filters>
      <div class="mb-4 flex flex-wrap gap-4 bg-gray-800/20 p-4 rounded-lg">
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
    </template>

    <!-- 2. 表单插槽 (添加和编辑共用) -->
    <template #form="{ mode }">
      <n-form ref="formRef" :model="formData" :rules="formRules" label-placement="left" label-width="100">
        <n-form-item label="平台" path="platform">
          <n-select v-model:value="formData.platform" :options="platformOptions" />
        </n-form-item>
        <n-form-item label="Channel ID" path="channel_id">
          <n-input v-model:value="formData.channel_id" placeholder="UC... / @用户名" />
        </n-form-item>
        <n-form-item label="名称">
          <n-input v-model:value="formData.name" :placeholder="mode === 'add' ? '不填则自动获取' : ''" />
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
        <!-- 只有在编辑模式下才显示“启用”勾选框 -->
        <n-form-item v-if="mode === 'edit'" label="状态">
          <n-checkbox v-model:checked="formData.is_active">启用该频道</n-checkbox>
        </n-form-item>
      </n-form>
    </template>
  </AdminCrudTable>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, h } from 'vue'
import { NButton, NSelect, NInput, NForm, NFormItem, NSpace, NCheckbox, NTag, NRadio, NRadioGroup, type DataTableColumns } from 'naive-ui'
import AdminCrudTable from '@/components/AdminCrudTable.vue'
import { channelApi, type Channel } from '@/api'
import { useApiError } from '@/composables/useApiError'
import { useAuthStore } from '../stores/auth'

const { handleError } = useApiError()
const authStore = useAuthStore()

// --- 状态 ---
const tableRef = ref()
const channels = ref<Channel[]>([])
const loading = ref(false)
const editingId = ref<number | null>(null)

// 筛选状态
const filterPlatform = ref<string | null>(null)
const filterActive = ref<string | null>(null)
const searchText = ref('')

const formData = ref<Partial<Channel>>({
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

const pagination = { pageSize: 20 }

// --- 选项配置 ---
const platformOptions = computed(() => {
  const opts = [{ label: 'YouTube', value: 'youtube' }]
  if (authStore.canAccessBilibili) opts.push({ label: 'Bilibili', value: 'bilibili' })
  return opts
})

const statusOptions = [
  { label: '启用', value: 'true' },
  { label: '禁用', value: 'false' }
]

// --- 计算属性 ---
const filteredChannels = computed(() => {
  return channels.value.filter(ch => {
    if (filterPlatform.value && ch.platform !== filterPlatform.value) return false
    if (filterActive.value && String(ch.is_active) !== filterActive.value) return false
    if (searchText.value && !ch.name.toLowerCase().includes(searchText.value.toLowerCase())) return false
    return true
  })
})

// --- 表格列定义 ---
const columns: DataTableColumns<Channel> = [
  {
    title: '头像',
    key: 'avatar_url',
    width: 80,
    render: (row) => h('img', {
      src: row.avatar_url || '',
      style: row.avatar_shape === 'square'
        ? 'width: 40px; height: 40px; border-radius: 8px;'
        : 'width: 40px; height: 40px; border-radius: 50%;',
      referrerPolicy: 'no-referrer'
    })
  },
  { title: '名称', key: 'name', sorter: 'default' },
  {
    title: '平台',
    key: 'platform',
    width: 100,
    render: (row) => h(NTag, { type: row.platform === 'youtube' ? 'error' : 'info' }, { default: () => row.platform })
  },
  {
    title: '状态',
    key: 'is_active',
    width: 80,
    render: (row) => h(NTag, { type: row.is_active ? 'success' : 'default' }, { default: () => row.is_active ? '启用' : '禁用' })
  },
  {
    title: '操作',
    key: 'actions',
    width: 150,
    render: (row) => h(NSpace, {}, {
      default: () => [
        h(NButton, { size: 'small', onClick: () => openEditModal(row) }, { default: () => '编辑' }),
        h(NButton, { size: 'small', type: 'error', onClick: () => handleDelete(row.id) }, { default: () => '删除' })
      ]
    })
  }
]

// --- 逻辑函数 ---
async function fetchChannels() {
  loading.value = true
  try {
    const { data } = await channelApi.getAll()
    channels.value = data
  } finally {
    loading.value = false
  }
}

function resetForm() {
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

function openAddModal() {
  resetForm()
  tableRef.value.openAdd()  
}

function openEditModal(channel: Channel) {
  editingId.value = channel.id
  formData.value = { ...channel } as any
  tableRef.value.openEdit()
}

async function handleDelete(id: string) {
  if (!confirm('确定删除吗？')) return
  try {
    await channelApi.delete(id)
    fetchChannels()
  } catch (err) {
    handleError(err, '删除失败')
  }
}

async function handleConfirm(mode: 'add' | 'edit') {
  try {
    if (mode === 'edit' && editingId.value) {
      await channelApi.update(editingId.value, formData.value)
    } else {
      await channelApi.create(formData.value)
    }
    tableRef.value.closeAll()
    fetchChannels()
  } catch (err) {
    handleError(err, '保存失败')
  }
}

onMounted(fetchChannels)
</script>