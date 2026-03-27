<template>
  <div class="container mx-auto px-4 py-8">
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold mb-2">机构管理</h1>
        <p class="text-gray-400">管理 VTuber 所属机构</p>
      </div>
      <n-button type="primary" @click="showAddModal = true">
        添加机构
      </n-button>
    </div>

    <!-- 表格 -->
    <n-data-table
      :columns="columns"
      :data="organizations"
      :loading="loading"
      :row-key="(row: Organization) => row.id"
      :bordered="false"
    />

    <!-- 添加/编辑弹窗 -->
    <n-modal
      v-model:show="showAddModal"
      preset="card"
      title="添加机构"
      style="width: 500px"
    >
      <n-form ref="formRef" :model="formData">
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
      title="编辑机构"
      style="width: 500px"
    >
      <n-form ref="formRef" :model="formData">
        <n-form-item label="名称">
          <n-input v-model:value="formData.name" />
        </n-form-item>
        <n-form-item label="英文名">
          <n-input v-model:value="formData.name_en" />
        </n-form-item>
        <n-form-item label="Logo URL">
          <n-input v-model:value="formData.logo_url" />
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
          <n-input v-model:value="formData.website" />
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
import { NButton, NModal, NForm, NFormItem, NSpace, NTag, NDataTable, NRadio, NRadioGroup, type DataTableColumns } from 'naive-ui'
import { orgApi, type Organization } from '../api'

const organizations = ref<Organization[]>([])
const loading = ref(false)

const showAddModal = ref(false)
const showEditModal = ref(false)
const editingId = ref<number | null>(null)

const formData = ref({
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
    title: '英文名',
    key: 'name_en'
  },
  {
    title: '官网',
    key: 'website',
    render: (row) => row.website 
      ? h('a', { href: row.website, target: '_blank', style: 'color: #3b82f6;' }, row.website)
      : '-'
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
          onClick: () => editOrganization(row)
        }, { default: () => '编辑' }),
        h(NButton, {
          size: 'small',
          type: 'error',
          onClick: () => deleteOrganization(row.id)
        }, { default: () => '删除' })
      ]
    })
  }
]

async function fetchOrganizations() {
  loading.value = true
  try {
    const { data } = await orgApi.getAll()
    organizations.value = data
  } catch (err) {
    console.error('Failed to fetch organizations:', err)
  } finally {
    loading.value = false
  }
}

function editOrganization(org: Organization) {
  editingId.value = org.id
  formData.value = {
    name: org.name,
    name_en: org.name_en || '',
    logo_url: org.logo_url || '',
    website: org.website || '',
    logo_shape: org.logo_shape || 'circle'
  }
  showEditModal.value = true
}

async function deleteOrganization(id: number) {
  if (!confirm('确定要删除这个机构吗？')) return
  
  try {
    await orgApi.delete(id)
    await fetchOrganizations()
  } catch (err) {
    console.error('Failed to delete organization:', err)
    alert('删除失败')
  }
}

function closeModal() {
  showAddModal.value = false
  showEditModal.value = false
  editingId.value = null
  formData.value = {
    name: '',
    name_en: '',
    logo_url: '',
    website: '',
    logo_shape: 'circle'
  }
}

async function submitForm() {
  try {
    const data = {
      name: formData.value.name,
      name_en: formData.value.name_en || null,
      logo_url: formData.value.logo_url || null,
      website: formData.value.website || null,
      logo_shape: formData.value.logo_shape
    }

    if (showEditModal.value && editingId.value) {
      await orgApi.update(editingId.value, data)
    } else {
      await orgApi.create(data)
    }
    
    await fetchOrganizations()
    closeModal()
  } catch (err: any) {
    console.error('Failed to save organization:', err)
    alert(err.response?.data?.detail || '保存失败')
  }
}

onMounted(() => {
  fetchOrganizations()
})
</script>
