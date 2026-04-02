<template>
  <div class="container mx-auto px-4 py-8">
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold mb-2">用户管理</h1>
        <p class="text-gray-400">管理系统用户和角色分配</p>
      </div>
      <n-button @click="refresh">
        <template #icon>
          <RefreshCw class="w-4 h-4" />
        </template>
        刷新
      </n-button>
    </div>

    <!-- 表格 -->
    <n-data-table
      :columns="columns"
      :data="users"
      :loading="loading"
      :row-key="(row: UserWithRoles) => row.id"
      :pagination="pagination"
      :bordered="false"
    />

    <!-- 分配角色弹窗 -->
    <n-modal
      v-model:show="showRoleModal"
      preset="card"
      title="分配角色"
      style="width: 400px"
    >
      <div class="py-4">
        <p class="mb-4 text-gray-400">为用户 <strong>{{ selectedUser?.username }}</strong> 分配角色</p>
        <n-checkbox-group v-model:value="selectedRoleIds">
          <div class="flex flex-col gap-2">
            <n-checkbox
              v-for="role in roles"
              :key="role.id"
              :value="role.id"
              :label="role.name"
            />
          </div>
        </n-checkbox-group>
      </div>
      <template #footer>
        <div class="flex justify-end gap-2">
          <n-button @click="showRoleModal = false">取消</n-button>
          <n-button type="primary" :loading="saving" @click="saveRoles">保存</n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, h, onMounted } from 'vue'
import { NButton, NTag, NDataTable, NModal, NCheckboxGroup, NCheckbox, useMessage } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import { adminPermissionsApi, type UserWithRoles, type Role } from '@/api'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const message = useMessage()

const users = ref<UserWithRoles[]>([])
const roles = ref<Role[]>([])
const loading = ref(false)
const saving = ref(false)
const showRoleModal = ref(false)
const selectedUser = ref<UserWithRoles | null>(null)
const selectedRoleIds = ref<number[]>([])

const pagination = { pageSize: 20 }

const columns: DataTableColumns<UserWithRoles> = [
  { title: 'ID', key: 'id', width: 80 },
  { title: '用户名', key: 'username' },
  { title: '邮箱', key: 'email' },
  { title: '注册时间', key: 'created_at', render: (row) => new Date(row.created_at).toLocaleString() },
  { 
    title: '角色', 
    key: 'roles',
    render: (row) => h('div', { class: 'flex gap-1 flex-wrap' }, 
      row.roles.map(r => h(NTag, { type: r === 'superadmin' ? 'error' : r === 'admin' ? 'warning' : 'info', size: 'small' }, () => r))
    )
  },
  {
    title: '操作',
    key: 'actions',
    width: 120,
    render: (row) => h('div', { class: 'flex gap-2' }, [
      h(NButton, { size: 'small', onClick: () => openRoleModal(row) }, () => '分配角色')
    ])
  }
]

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
  try {
    const { data } = await adminPermissionsApi.getRoles()
    roles.value = data
  } catch (e) {
    message.error('获取角色失败')
  }
}

function openRoleModal(user: UserWithRoles) {
  selectedUser.value = user
  selectedRoleIds.value = roles.value.filter(r => user.roles.includes(r.name)).map(r => r.id)
  showRoleModal.value = true
}

async function saveRoles() {
  if (!selectedUser.value) return
  saving.value = true
  try {
    await adminPermissionsApi.updateUserRoles(selectedUser.value.id, selectedRoleIds.value)
    message.success('角色分配成功')
    showRoleModal.value = false
    await fetchUsers()
    if (authStore.user?.id === selectedUser.value.id) {
      await authStore.fetchUserInfo()
    }
  } catch (e) {
    message.error('保存失败')
  } finally {
    saving.value = false
  }
}

function refresh() {
  fetchUsers()
}

onMounted(() => {
  fetchUsers()
  fetchRoles()
})
</script>