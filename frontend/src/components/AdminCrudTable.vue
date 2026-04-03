<template>
  <div class="container mx-auto px-4 py-8">
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold mb-2">{{ title }}</h1>
        <p class="text-gray-400">{{ description }}</p>
      </div>
      <n-button type="primary" @click="$emit('add')">
        {{ addLabel }}
      </n-button>
    </div>

    <slot name="filters" />

    <n-data-table
      :columns="columns"
      :data="data"
      :loading="loading"
      :row-key="rowKey"
      :pagination="pagination"
      :bordered="false"
    />

    <n-modal
      v-model:show="showAddModal"
      preset="card"
      :title="addLabel"
      style="width: 500px"
    >
      <slot name="form" :mode="'add'" />
      <template #footer>
        <n-space justify="end">
          <n-button @click="showAddModal = false">取消</n-button>
          <n-button type="primary" @click="$emit('submit', 'add')">添加</n-button>
        </n-space>
      </template>
    </n-modal>

    <n-modal
      v-model:show="showEditModal"
      preset="card"
      title="编辑"
      style="width: 500px"
    >
      <slot name="form" :mode="'edit'" />
      <template #footer>
        <n-space justify="end">
          <n-button @click="showEditModal = false">取消</n-button>
          <n-button type="primary" @click="$emit('submit', 'edit')">保存</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { DataTableColumns } from 'naive-ui'

defineProps<{
  title: string
  description: string
  addLabel: string
  columns: DataTableColumns<any>
  data: any[]
  loading: boolean
  rowKey: (row: any) => any
  pagination?: object
}>()

defineEmits<{
  (e: 'add'): void
  (e: 'submit', mode: 'add' | 'edit'): void
}>()

const showAddModal = ref(false)
const showEditModal = ref(false)

defineExpose({ showAddModal, showEditModal })
</script>