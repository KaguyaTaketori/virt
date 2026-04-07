<template>
  <AdminCrudTable
    ref="tableRef"
    title="用户管理"
    description="管理系统用户和角色分配"
    :columns="columns"
    :data="users"
    :loading="loading"
    :row-key="(row: UserWithRoles) => row.id"
    :pagination="pagination"
    @submit="saveRoles"
  >
    <!-- 1. 顶部操作区插槽 -->
    <template #filters>
      <div class="mb-4 flex justify-end">
        <n-button secondary @click="fetchUsers">
          <template #icon><RefreshCw class="w-4 h-4" /></template>
          刷新数据
        </n-button>
      </div>
    </template>

    <!-- 2. 分配角色的表单插槽 -->
    <template #form>
      <div class="py-2">
        <p class="mb-4 text-gray-500">
          为用户 <strong class="text-primary">{{ selectedUser?.username }}</strong> 分配系统角色：
        </p>
        <n-checkbox-group v-model:value="selectedRoleIds">
          <div class="flex flex-col gap-3 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
            <n-checkbox
              v-for="role in roles"
              :key="role.id"
              :value="role.id"
              :label="role.name"
            />
          </div>
        </n-checkbox-group>
      </div>
    </template>
  </AdminCrudTable>
</template>

<script setup lang="ts">
import { ref, h, onMounted } from 'vue'
import { NButton, NTag, NCheckboxGroup, NCheckbox, useMessage, type DataTableColumns } from 'naive-ui'
import { RefreshCw } from 'lucide-vue-next'
import AdminCrudTable from '@/components/AdminCrudTable.vue'
import { adminPermissionsApi, type UserWithRoles, type Role } from '@/api'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const message = useMessage()
const tableRef = ref()

// --- 数据状态 ---
const users = ref<UserWithRoles[]>([])
const roles = ref<Role[]>([])
const loading = ref(false)

const selectedUser = ref<UserWithRoles | null>(null)
const selectedRoleIds = ref<number[]>([])

const pagination = { pageSize: 20 }

// --- 表格列定义 ---
const columns: DataTableColumns<UserWithRoles> = [
  { title: 'ID', key: 'id', width: 80 },
  { title: '用户名', key: 'username', sorter: 'default' },
  { title: '邮箱', key: 'email' },
  { 
    title: '注册时间', 
    key: 'created_at', 
    render: (row) => new Date(row.created_at).toLocaleString() 
  },
  { 
    title: '角色', 
    key: 'roles',
    render: (row) => h('div', { class: 'flex gap-1 flex-wrap' }, 
      row.roles.map(r => h(NTag, { 
        type: r === 'superadmin' ? 'error' : r === 'admin' ? 'warning' : 'info', 
        size: 'small',
        round: true
      }, () => r))
    )
  },
  {
    title: '操作',
    key: 'actions',
    width: 120,
    render: (row) => h(NButton, { 
      size: 'small', 
      type: 'primary',
      secondary: true,
      onClick: () => openRoleModal(row) 
    }, () => '分配角色')
  }
]

// --- 逻辑函数 ---

async function fetchUsers() {
  loading.value = true
  try {
    const { data } = await adminPermissionsApi.getUsers()
    users.value = data
  } catch (e) {
    message.error('获取用户失败')
  } finally {
    loading.value = false
  }
}

async function fetchRoles() {
  const { data } = await adminPermissionsApi.getRoles()
  roles.value = data
}

function openRoleModal(user: UserWithRoles) {
  selectedUser.value = user
  selectedRoleIds.value = roles.value
    .filter(r => user.roles.includes(r.name))
    .map(r => r.id)
  tableRef.value.openEdit()
}

async function saveRoles() {
  if (!selectedUser.value) return
  
  try {
    await adminPermissionsApi.updateUserRoles(selectedUser.value.id, selectedRoleIds.value)
    message.success('角色分配成功')
    
    tableRef.value.closeAll()
    
    await fetchUsers()
    
    if (authStore.user?.id === selectedUser.value.id) {
      await authStore.fetchUserInfo()
    }
  } catch (e) {
    message.error('保存失败')
  }
}

onMounted(() => {
  fetchUsers()
  fetchRoles()
})
</script>