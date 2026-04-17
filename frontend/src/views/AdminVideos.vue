<template>
  <AdminCrudTable
    title="视频管理"
    description="按时长筛选，并可批量修改视频类别"
    :columns="columns"
    :data="videos"
    :loading="loading"
    :row-key="(row: Video) => row.id"
    :pagination="pagination"
    v-model:checked-row-keys="selectedIds"
  >
    <!-- 所有的筛选和批量操作都放在 filters 插槽 -->
    <template #filters>
      <div class="flex flex-col gap-6 mb-6">
        <!-- 过滤器行 -->
        <div class="flex flex-wrap gap-4 items-end bg-gray-800/30 p-4 rounded-lg">
          <div class="flex flex-col gap-2">
            <span class="text-xs text-gray-500">频道</span>
            <n-select v-model:value="filterChannelId" :options="channelOptions" style="width: 200px" clearable />
          </div>
          <div class="flex flex-col gap-2">
            <span class="text-xs text-gray-500">状态</span>
            <n-select v-model:value="filterStatus" :options="statusOptions" style="width: 150px" clearable />
          </div>
          <div class="flex flex-col gap-2">
            <span class="text-xs text-gray-500">时长(分)</span>
            <div class="flex items-center gap-2">
              <n-input-number v-model:value="durationMinMinutes" placeholder="Min" style="width: 100px" />
              <span class="text-gray-600">-</span>
              <n-input-number v-model:value="durationMaxMinutes" placeholder="Max" style="width: 100px" />
            </div>
          </div>
          <div class="flex gap-2">
            <n-button type="primary" @click="fetchVideos" :disabled="!filterChannelId">查询</n-button>
            <n-button @click="resetFilters">重制</n-button>
          </div>
        </div>

        <!-- 批量操作行 -->
        <div class="flex items-center justify-between bg-blue-500/5 border border-blue-500/20 p-4 rounded-lg">
          <div class="flex items-center gap-4">
            <span class="text-sm font-medium">批量操作 (已选 {{ selectedIds.length }} 条):</span>
            <n-select v-model:value="batchNewStatus" :options="batchStatusOptions" style="width: 180px" />
            <n-button type="primary" secondary :disabled="selectedIds.length === 0" @click="applyBatchUpdate">
              确认修改
            </n-button>
          </div>
          <n-button size="small" quaternary :disabled="selectedIds.length === 0" @click="selectedIds = []">
            取消全选
          </n-button>
        </div>
      </div>
    </template>
  </AdminCrudTable>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, h } from 'vue'
import { NTag, NButton, DataTableColumns } from 'naive-ui'
import AdminCrudTable from '../components/AdminCrudTable.vue'
import { channelApi, adminVideosApi, type Video, type Channel } from '../api'

const loading = ref(false)
const videos = ref<Video[]>([])
const channels = ref<Channel[]>([])
const selectedIds = ref<string[]>([])

const filterChannelId = ref<string | null>(null)
const filterStatus = ref<string | null>(null)
const durationMinMinutes = ref<number | undefined>(undefined)
const durationMaxMinutes = ref<number | undefined>(undefined)
const batchNewStatus = ref('archive')

const page = ref(1)
const pageSize = ref(24)
const total = ref(0)

const pagination = computed(() => ({
  page: page.value,
  pageSize: pageSize.value,
  itemCount: total.value,
  showSizePicker: true,
  pageSizes: [24, 48, 96],
  onChange: (p: number) => {
    page.value = p
    fetchVideos()
  },
  onUpdatePageSize: (ps: number) => {
    pageSize.value = ps
    page.value = 1
    fetchVideos()
  }
}))


const columns: DataTableColumns<Video> = [
  { type: 'selection' },
  {
    title: '封面',
    key: 'thumbnail_url',
    width: 90,
    render: (row: Video) => row.thumbnail_url ? h('img', { src: row.thumbnail_url, class: 'w-16 h-10 object-cover rounded' }) : null
  },
  { title: '标题', key: 'title', minWidth: 200 },
  {
    title: '类别',
    key: 'status',
    width: 100,
    render: (row: Video) => h(NTag, { type: row.status === 'live' ? 'error' : 'info', size: 'small' }, { default: () => row.status })
  },
  { title: '时长', key: 'duration', width: 100 },
  { title: '发布时间', key: 'published_at', width: 180 },
]

const channelOptions = computed(() => channels.value.map(ch => ({ label: ch.name, value: ch.id })))
const statusOptions = ['live', 'upcoming', 'archive', 'upload', 'short'].map(s => ({ label: s, value: s }))
const batchStatusOptions = statusOptions

async function fetchVideos() {
  if (!filterChannelId.value) return
  loading.value = true
  try {
    const { data } = await adminVideosApi.getVideos({
      channel_id: filterChannelId.value,
      status: filterStatus.value,
      duration_min: durationMinMinutes.value ? durationMinMinutes.value * 60 : null,
      duration_max: durationMaxMinutes.value ? durationMaxMinutes.value * 60 : null,
      page: page.value,
      page_size: pageSize.value
    })
    videos.value = data.videos
    total.value = data.total
    selectedIds.value = []
  } finally {
    loading.value = false
  }
}

async function applyBatchUpdate() {
  if (selectedIds.value.length === 0) return
  if (!confirm(`确定修改 ${selectedIds.value.length} 个视频为 ${batchNewStatus.value}？`)) return
  
  loading.value = true
  try {
    await adminVideosApi.batchUpdateStatus({
      video_ids: selectedIds.value,
      new_status: batchNewStatus.value
    })
    await fetchVideos()
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filterStatus.value = null
  durationMinMinutes.value = undefined
  durationMaxMinutes.value = undefined
  page.value = 1
  fetchVideos()
}

onMounted(async () => {
  const { data } = await channelApi.getAll()
  channels.value = data
  if (data.length > 0) {
    filterChannelId.value = data[0].id
    fetchVideos()
  }
})
</script>