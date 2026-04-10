<template>
  <AdminCrudTable
    ref="tableRef"
    title="角色与权限"
    description="管理系统角色和权限分配"
    add-label="新建权限"
    :columns="permColumns"
    :data="permissions"
    :loading="loading"
    :row-key="(row: Permission) => row.id"
    :pagination="{ pageSize: 15 }"
    @add="tableRef.value.openAdd()"
    @submit="createPermission"
  >
    <!-- 1. 角色管理部分放在 filters 插槽内 -->
    <template #filters>
      <div class="mb-10">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-xl font-bold flex items-center gap-2">
            <Shield class="w-5 h-5 text-primary" /> 角色管理
          </h2>
          <n-button secondary type="primary" @click="showRoleModal = true">
            <template #icon><Plus class="w-4 h-4" /></template>
            新建角色
          </n-button>
        </div>
        
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <n-card v-for="role in roles" :key="role.id" size="small" hoverable>
            <div class="flex items-center justify-between">
              <div class="flex flex-col">
                <n-tag 
                  :type="role.name === 'superadmin' ? 'error' : role.name === 'admin' ? 'warning' : 'info'"
                  round
                  class="w-fit"
                >
                  {{ role.name }}
                </n-tag>
                <span class="mt-2 text-xs text-gray-500">{{ role.description }}</span>
              </div>
              <n-button 
                size="small" 
                quaternary
                type="primary"
                :disabled="role.name === 'superadmin'" 
                @click="openAssignPermModal(role)"
              >
                {{ role.name === 'superadmin' ? '全权限' : '分配权限' }}
              </n-button>
            </div>
          </n-card>
        </div>
      </div>

      <!-- 分隔线，引出下方的权限列表 -->
      <h2 class="text-xl font-bold mb-4">权限列表</h2>
    </template>

    <!-- 2. 新建权限的表单 -->
    <template #form>
      <n-form :model="permForm" label-placement="left" label-width="80">
        <n-form-item label="名称" path="name">
          <n-input v-model:value="permForm.name" placeholder="如: channel.manage" />
        </n-form-item>
        <n-form-item label="描述" path="description">
          <n-input v-model:value="permForm.description" placeholder="权限描述" />
        </n-form-item>
        <n-form-item label="资源" path="resource">
          <n-input v-model:value="permForm.resource" placeholder="如: channel" />
        </n-form-item>
        <n-form-item label="操作" path="action">
          <n-input v-model:value="permForm.action" placeholder="如: manage" />
        </n-form-item>
      </n-form>
    </template>
  </AdminCrudTable>

  <!-- 角色相关的弹窗（由于 AdminCrudTable 只接管一个主体的弹窗，这里的两个我们手动维护） -->
  <n-modal v-model:show="showRoleModal" preset="card" title="新建角色" style="width: 400px">
    <n-form :model="roleForm">
      <n-form-item label="角色名称"><n-input v-model:value="roleForm.name" /></n-form-item>
      <n-form-item label="描述"><n-input v-model:value="roleForm.description" type="textarea" /></n-form-item>
    </n-form>
    <template #footer>
      <n-space justify="end">
        <n-button @click="showRoleModal = false">取消</n-button>
        <n-button type="primary" :loading="saving" @click="createRole">创建</n-button>
      </n-space>
    </template>
  </n-modal>

  <n-modal v-model:show="showAssignPermModal" preset="card" title="分配权限" style="width: 500px">
    <div class="py-2">
      <p class="mb-4">为角色 <n-tag size="small" type="primary">{{ selectedRole?.name }}</n-tag> 分配权限</p>
      <n-checkbox-group v-model:value="selectedPermIds">
        <div class="grid grid-cols-2 gap-3">
          <n-checkbox v-for="p in permissions" :key="p.id" :value="p.id" :label="`${p.resource}.${p.action}`" />
        </div>
      </n-checkbox-group>
    </div>
    <template #footer>
      <n-space justify="end">
        <n-button @click="showAssignPermModal = false">取消</n-button>
        <n-button type="primary" :loading="saving" @click="saveRolePermissions">保存</n-button>
      </n-space>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, h, onMounted } from 'vue'
import { NButton, NTag, NModal, NForm, NFormItem, NInput, NCard, NSpace, NCheckboxGroup, NCheckbox, useMessage, type DataTableColumns } from 'naive-ui'
import { Plus, Shield } from 'lucide-vue-next'
import AdminCrudTable from '@/components/AdminCrudTable.vue'
import { adminPermissionsApi, type Role, type Permission } from '@/api'

const message = useMessage()
const tableRef = ref()

// 数据状态
const roles = ref<Role[]>([])
const permissions = ref<Permission[]>([])
const loading = ref(false)
const saving = ref(false)

// 弹窗状态
const showRoleModal = ref(false)
const showAssignPermModal = ref(false)
const selectedRole = ref<Role | null>(null)
const selectedPermIds = ref<number[]>([])

// 表单状态
const roleForm = ref({ name: '', description: '' })
const permForm = ref({ name: '', description: '', resource: '', action: '' })

// 权限表格列
const permColumns: DataTableColumns<Permission> = [
  { title: 'ID', key: 'id', width: 60 },
  { title: '权限名称', key: 'name', render: (row) => h(NTag, { type: 'info', size: 'small' }, () => row.name) },
  { title: '描述', key: 'description' },
  { title: '资源', key: 'resource', width: 100 },
  { title: '操作', key: 'action', width: 100 },
]

// --- 逻辑 ---

async function fetchRoles() {
  const { data } = await adminPermissionsApi.getRoles()
  roles.value = data
}

async function fetchPermissions() {
  loading.value = true
  try {
    const { data } = await adminPermissionsApi.getPermissions()
    permissions.value = data
  } finally {
    loading.value = false
  }
}

// 创建权限（接管 AdminCrudTable 的 submit）
async function createPermission() {
  saving.value = true
  try {
    await adminPermissionsApi.createPermission(permForm.value)
    message.success('权限创建成功')
    tableRef.value.closeAdd()
    permForm.value = { name: '', description: '', resource: '', action: '' }
    fetchPermissions()
  } finally {
    saving.value = false
  }
}

async function createRole() {
  saving.value = true
  try {
    await adminPermissionsApi.createRole(roleForm.value)
    message.success('角色创建成功')
    showRoleModal.value = false
    roleForm.value = { name: '', description: '' }
    fetchRoles()
  } finally {
    saving.value = false
  }
}

async function openAssignPermModal(role: Role) {
  selectedRole.value = role
  const { data } = await adminPermissionsApi.getRolePermissions(role.id)
  selectedPermIds.value = data
  showAssignPermModal.value = true
}

async function saveRolePermissions() {
  if (!selectedRole.value) return
  saving.value = true
  try {
    await adminPermissionsApi.assignPermissionsToRole(selectedRole.value.id, selectedPermIds.value)
    message.success('权限分配成功')
    showAssignPermModal.value = false
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  fetchRoles()
  fetchPermissions()
})
</script>