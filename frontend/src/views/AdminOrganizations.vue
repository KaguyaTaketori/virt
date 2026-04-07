<template>
  <AdminCrudTable
    ref="tableRef"
    title="机构管理"
    description="管理 VTuber 所属机构"
    add-label="添加机构"
    :columns="columns"
    :data="organizations"
    :loading="loading"
    :row-key="(row: Organization) => row.id"
    @add="openAddModal"
    @submit="handleConfirm"
  >
    <template #form>
      <n-form ref="formRef" :model="formData" label-placement="left" label-width="80">
        <n-form-item label="名称">
          <n-input v-model:value="formData.name" placeholder="如：Hololive" />
        </n-form-item>
        <n-form-item label="英文名">
          <n-input v-model:value="formData.name_en" placeholder="如：Hololive Production" />
        </n-form-item>
        <n-form-item label="Logo URL">
          <n-input v-model:value="formData.logo_url" placeholder="https://..." />
        </n-form-item>
        <n-form-item label="Logo 形状">
          <n-radio-group v-model:value="formData.logo_shape">
            <n-space>
              <n-radio value="circle">圆形</n-radio>
              <n-radio value="square">方形</n-radio>
            </n-space>
          </n-radio-group>
        </n-form-item>
        <n-form-item label="官网">
          <n-input v-model:value="formData.website" placeholder="https://..." />
        </n-form-item>
      </n-form>
    </template>
  </AdminCrudTable>
</template>

<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { NButton, NForm, NFormItem, NSpace, NRadio, NRadioGroup, NInput, type DataTableColumns } from 'naive-ui'
import AdminCrudTable from '@/components/AdminCrudTable.vue'
import { orgApi, type Organization } from '../api'
import { useOrgStore } from '../stores/org'
import { useApiError } from '@/composables/useApiError'

const { handleError } = useApiError()
const orgStore = useOrgStore()

const tableRef = ref()
const organizations = ref<Organization[]>([])
const loading = ref(false)
const editingId = ref<number | null>(null)

const formData = ref<Partial<Organization>>({
  name: '',
  name_en: '',
  logo_url: '',
  website: '',
  logo_shape: 'circle'
})

const columns: DataTableColumns<Organization> = [
  {
    title: 'Logo',
    key: 'logo_url',
    width: 80,
    render: (row) => h('img', {
      src: row.logo_url || '',
      style: row.logo_shape === 'square' 
        ? 'width: 40px; height: 40px; border-radius: 8px;'
        : 'width: 40px; height: 40px; border-radius: 50%;',
      referrerPolicy: 'no-referrer'
    })
  },
  { title: '名称', key: 'name', sorter: 'default' },
  { title: '英文名', key: 'name_en' },
  {
    title: '官网',
    key: 'website',
    render: (row) => row.website 
      ? h('a', { href: row.website, target: '_blank', class: 'text-blue-500 hover:underline' }, row.website)
      : '-'
  },
  {
    title: '操作',
    key: 'actions',
    width: 150,
    render: (row) => h(NSpace, { size: 'small' }, {
      default: () => [
        h(NButton, { size: 'small', onClick: () => openEditModal(row) }, { default: () => '编辑' }),
        h(NButton, { size: 'small', type: 'error', onClick: () => handleDelete(row.id) }, { default: () => '删除' })
      ]
    })
  }
]

async function fetchOrganizations() {
  loading.value = true
  try {
    const { data } = await orgApi.getAll()
    organizations.value = data
  } finally {
    loading.value = false
  }
}

function resetForm() {
  editingId.value = null
  formData.value = {
    name: '',
    name_en: '',
    logo_url: '',
    website: '',
    logo_shape: 'circle'
  }
}

function openAddModal() {
  resetForm()
  tableRef.value.openAdd()
}

function openEditModal(org: Organization) {
  editingId.value = org.id
  formData.value = { ...org }
  tableRef.value.openEdit()
}

async function handleDelete(id: number) {
  if (!confirm('确定要删除这个机构吗？')) return
  try {
    await orgApi.delete(id)
    await fetchOrganizations()
  } catch (err) {
    handleError(err, '删除失败')
  }
}

async function handleConfirm(mode: 'add' | 'edit') {
  try {
    if (mode === 'edit' && editingId.value) {
      await orgApi.update(editingId.value, formData.value)
    } else {
      await orgApi.create(formData.value as any)
    }
    
    await orgStore.invalidate()
    tableRef.value.closeAll()
    fetchOrganizations()
  } catch (err) {
    handleError(err, '保存失败')
  }
}

onMounted(fetchOrganizations)
</script>