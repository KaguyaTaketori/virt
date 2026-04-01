<template>
  <div class="container mx-auto px-4 py-8">
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold mb-2">视频管理</h1>
        <p class="text-gray-400">按时长筛选，并可批量修改视频类别</p>
      </div>
    </div>

    <!-- Filters -->
    <div class="mb-4 flex flex-wrap gap-4 items-end">
      <div class="flex flex-col gap-2">
        <span class="text-xs text-gray-500">频道</span>
        <n-select
          v-model:value="filterChannelId"
          :options="channelOptions"
          placeholder="选择频道"
          style="width: 220px"
          clearable
        />
      </div>

      <div class="flex flex-col gap-2">
        <span class="text-xs text-gray-500">状态</span>
        <n-select
          v-model:value="filterStatus"
          :options="statusOptions"
          placeholder="全部"
          style="width: 200px"
          clearable
        />
      </div>

      <div class="flex flex-col gap-2">
        <span class="text-xs text-gray-500">最短时长（分钟）</span>
        <n-input
          v-model:value="durationMinMinutes"
          type="number"
          min="0"
          step="1"
          placeholder="例如 10"
          style="width: 140px"
        />
      </div>

      <div class="flex flex-col gap-2">
        <span class="text-xs text-gray-500">最长时长（分钟）</span>
        <n-input
          v-model:value="durationMaxMinutes"
          type="number"
          min="0"
          step="1"
          placeholder="例如 60"
          style="width: 140px"
        />
      </div>

      <div class="flex gap-2">
        <n-button type="primary" @click="fetchVideos" :disabled="!filterChannelId">
          查询
        </n-button>
        <n-button @click="resetFilters">
          重置
        </n-button>
      </div>
    </div>

    <!-- Batch Update -->
    <div class="mb-4 flex flex-wrap gap-4 items-center">
      <div class="flex flex-col gap-2">
        <span class="text-xs text-gray-500">批量修改为</span>
        <n-select
          v-model:value="batchNewStatus"
          :options="batchStatusOptions"
          placeholder="选择新类别"
          style="width: 220px"
        />
      </div>

      <div class="flex gap-2">
        <n-button
          type="primary"
          :disabled="selectedIds.length === 0"
          @click="applyBatchUpdate"
        >
          批量修改
        </n-button>
        <n-button
          :disabled="selectedIds.length === 0"
          @click="selectedIds = []"
        >
          清空选择
        </n-button>
      </div>

      <div class="text-sm text-gray-500">
        已选 {{ selectedIds.length }} 条
      </div>
    </div>

    <!-- Table -->
    <n-data-table
      :columns="columns"
      :data="videos"
      :loading="loading"
      :bordered="false"
      :row-key="(row: any) => row.id"
      :pagination="false"
      v-model:checkedRowKeys="selectedIds"
    />

    <div v-if="total > 0" class="flex justify-center mt-4">
      <n-pagination
        v-model:page="currentPage"
        :page-count="Math.ceil(total / pageSize)"
        :page-sizes="[24, 48, 96]"
        @update:page="fetchVideos"
        @update:page-size="(ps: number) => { pageSize.value = ps; currentPage = 1; fetchVideos() }"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, h } from 'vue'
import { NButton, NSelect, NInput, NDataTable, NTag, NPagination } from 'naive-ui'
import { channelApi, adminVideosApi, type Video, type Channel } from '../api'

type VideoStatus = 'live' | 'upcoming' | 'archive' | 'upload' | 'short'

const loading = ref(false)
const videos = ref<Video[]>([])
const currentPage = ref(1)
const pageSize = ref(24)
const total = ref(0)

const channels = ref<Channel[]>([])
const filterChannelId = ref<number | null>(null)
const filterStatus = ref<string | null>(null)

// duration in minutes (UI)
const durationMinMinutes = ref<number | null>(null)
const durationMaxMinutes = ref<number | null>(null)

const batchNewStatus = ref<VideoStatus>('archive')

const selectedIds = ref<string[]>([])

const channelOptions = computed(() =>
  channels.value.map(ch => ({
    label: `${ch.name} (#${ch.id})`,
    value: ch.id,
  })),
)

const statusOptions = [
  { label: 'live', value: 'live' },
  { label: 'upcoming', value: 'upcoming' },
  { label: 'archive', value: 'archive' },
  { label: 'upload', value: 'upload' },
  { label: 'short', value: 'short' },
]

const batchStatusOptions = statusOptions

const columns: any = [
  {
    type: 'selection',
  },
  {
    title: '封面',
    key: 'thumbnail_url',
    width: 90,
    render: (row: Video) =>
      row.thumbnail_url
        ? h('img', {
            src: row.thumbnail_url,
            class: 'w-16 h-10 object-cover rounded',
            referrerpolicy: 'no-referrer',
          })
        : null,
  },
  {
    title: 'video_id',
    key: 'id',
    width: 180,
    render: (row: Video) =>
      h('code', { style: 'font-size: 12px; color: #888;' }, row.id),
  },
  {
    title: '标题',
    key: 'title',
    minWidth: 220,
    render: (row: Video) => row.title || '-',
  },
  {
    title: '类别',
    key: 'status',
    width: 120,
    render: (row: Video) =>
      h(
        NTag,
        {
          type:
            row.status === 'live'
              ? 'error'
              : row.status === 'archive'
                ? 'default'
                : 'info',
          size: 'small',
        },
        { default: () => row.status },
      ),
  },
  {
    title: '时长',
    key: 'duration',
    width: 100,
    render: (row: Video) => row.duration || '-',
  },
  {
    title: '发布时间',
    key: 'published_at',
    minWidth: 180,
    render: (row: Video) => row.published_at || '-',
  },
  {
    title: '观看',
    key: 'view_count',
    width: 100,
    render: (row: Video) => row.view_count ?? 0,
  },
]

function resetFilters() {
  filterStatus.value = null
  durationMinMinutes.value = null
  durationMaxMinutes.value = null
  currentPage.value = 1
  selectedIds.value = []
}

async function fetchVideos() {
  if (!filterChannelId.value) return
  loading.value = true
  try {
    const min = durationMinMinutes.value === null ? null : Math.max(0, Math.floor(durationMinMinutes.value)) * 60
    const max = durationMaxMinutes.value === null ? null : Math.max(0, Math.floor(durationMaxMinutes.value)) * 60

    const { data } = await adminVideosApi.getVideos({
      channel_id: filterChannelId.value,
      status: filterStatus.value,
      duration_min: min,
      duration_max: max,
      page: currentPage.value,
      page_size: pageSize.value,
    })
    videos.value = data.videos
    total.value = data.total
    selectedIds.value = []
  } catch (err) {
    console.error('Failed to fetch videos:', err)
  } finally {
    loading.value = false
  }
}

async function applyBatchUpdate() {
  if (!filterChannelId.value) return
  if (selectedIds.value.length === 0) return

  const ok = confirm(`确定要将 ${selectedIds.value.length} 条视频类别批量修改为：${batchNewStatus.value} 吗？`)
  if (!ok) return

  loading.value = true
  try {
    await adminVideosApi.batchUpdateStatus({
      video_ids: selectedIds.value,
      new_status: batchNewStatus.value,
    })
    selectedIds.value = []
    await fetchVideos()
  } catch (err) {
    console.error('Failed to batch update:', err)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  try {
    const { data } = await channelApi.getAll()
    channels.value = data
    if (channels.value.length > 0) {
      filterChannelId.value = channels.value[0].id
    }
    await fetchVideos()
  } catch (err) {
    console.error('Failed to init channels:', err)
  }
})
</script>

