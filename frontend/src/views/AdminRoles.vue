<template>
  <div class="container mx-auto px-4 py-8">
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold mb-2">角色与权限</h1>
        <p class="text-gray-400">管理系统角色和权限分配</p>
      </div>
      <div class="flex gap-2">
        <n-button type="primary" @click="showRoleModal = true">
          <template #icon>
            <Plus class="w-4 h-4" />
          </template>
          新建角色
        </n-button>
        <n-button @click="showPermModal = true">
          <template #icon>
            <Shield class="w-4 h-4" />
          </template>
          新建权限
        </n-button>
      </div>
    </div>

    <!-- 角色管理 -->
    <div class="mb-8">
      <h2 class="text-xl font-bold mb-4">角色</h2>
      <n-space vertical>
        <n-card v-for="role in roles" :key="role.id" size="small">
          <div class="flex items-center justify-between">
            <div>
              <n-tag :type="role.name === 'superadmin' ? 'error' : role.name === 'admin' ? 'warning' : 'info'">
                {{ role.name }}
              </n-tag>
              <span class="ml-2 text-gray-400">{{ role.description }}</span>
            </div>
            <n-button size="small" :disabled="role.name === 'superadmin'" @click="openAssignPermModal(role)">
              {{ role.name === 'superadmin' ? '拥有全部权限' : '分配权限' }}
            </n-button>
          </div>
        </n-card>
      </n-space>
    </div>

    <!-- 权限管理 -->
    <div>
      <h2 class="text-xl font-bold mb-4">权限列表</h2>
      <n-data-table
        :columns="permColumns"
        :data="permissions"
        :loading="loading"
        :row-key="(row: Permission) => row.id"
        :pagination="{ pageSize: 15 }"
        :bordered="false"
      />
    </div>

    <!-- 新建角色弹窗 -->
    <n-modal
      v-model:show="showRoleModal"
      preset="card"
      title="新建角色"
      style="width: 400px"
    >
      <n-form ref="roleFormRef" :model="roleForm">
        <n-form-item label="角色名称" path="name">
          <n-input v-model:value="roleForm.name" placeholder="如: operator" />
        </n-form-item>
        <n-form-item label="描述" path="description">
          <n-input v-model:value="roleForm.description" type="textarea" placeholder="角色描述" />
        </n-form-item>
      </n-form>
      <template #footer>
        <div class="flex justify-end gap-2">
          <n-button @click="showRoleModal = false">取消</n-button>
          <n-button type="primary" :loading="saving" @click="createRole">创建</n-button>
        </div>
      </template>
    </n-modal>

    <!-- 新建权限弹窗 -->
    <n-modal
      v-model:show="showPermModal"
      preset="card"
      title="新建权限"
      style="width: 450px"
    >
      <n-form ref="permFormRef" :model="permForm">
        <n-form-item label="权限名称" path="name">
          <n-input v-model:value="permForm.name" placeholder="如: channel.manage" />
        </n-form-item>
        <n-form-item label="描述" path="description">
          <n-input v-model:value="permForm.description" placeholder="权限描述" />
        </n-form-item>
        <n-form-item label="资源" path="resource">
          <n-input v-model:value="permForm.resource" placeholder="如: channel, user, system" />
        </n-form-item>
        <n-form-item label="操作" path="action">
          <n-input v-model:value="permForm.action" placeholder="如: create, read, update, delete, manage" />
        </n-form-item>
      </n-form>
      <template #footer>
        <div class="flex justify-end gap-2">
          <n-button @click="showPermModal = false">取消</n-button>
          <n-button type="primary" :loading="saving" @click="createPermission">创建</n-button>
        </div>
      </template>
    </n-modal>

    <!-- 分配权限弹窗 -->
    <n-modal
      v-model:show="showAssignPermModal"
      preset="card"
      title="分配权限"
      style="width: 500px"
    >
      <div class="py-4">
        <p class="mb-4 text-gray-400">为角色 <strong>{{ selectedRole?.name }}</strong> 分配权限</p>
        <n-checkbox-group v-model:value="selectedPermIds">
          <div class="grid grid-cols-2 gap-2">
            <n-checkbox
              v-for="perm in permissions"
              :key="perm.id"
              :value="perm.id"
              :label="`${perm.resource}.${perm.action}`"
            />
          </div>
        </n-checkbox-group>
      </div>
      <template #footer>
        <div class="flex justify-end gap-2">
          <n-button @click="showAssignPermModal = false">取消</n-button>
          <n-button type="primary" :loading="saving" @click="saveRolePermissions">保存</n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, h, onMounted } from 'vue'
import {
  NButton, NTag, NDataTable, NModal, NForm, NFormItem,
  NInput, NCard, NSpace, NCheckboxGroup, NCheckbox,
  useMessage,
} from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import { Plus, Shield } from 'lucide-vue-next'
import { adminPermissionsApi, type Role, type Permission } from '@/api'

const message = useMessage()

const roles = ref<Role[]>([])
const permissions = ref<Permission[]>([])
const loading = ref(false)
const saving = ref(false)

const showRoleModal = ref(false)
const showPermModal = ref(false)
const showAssignPermModal = ref(false)
const selectedRole = ref<Role | null>(null)
const selectedPermIds = ref<number[]>([])

const roleForm = ref({ name: '', description: '' })
const permForm = ref({ name: '', description: '', resource: '', action: '' })

const permColumns: DataTableColumns<Permission> = [
  { title: 'ID', key: 'id', width: 60 },
  { title: '权限名称', key: 'name', render: (row) => h(NTag, { type: 'info', size: 'small' }, () => row.name) },
  { title: '描述', key: 'description' },
  { title: '资源', key: 'resource', width: 100 },
  { title: '操作', key: 'action', width: 100 },
]

async function fetchRoles() {
  try {
    const { data } = await adminPermissionsApi.getRoles()
    roles.value = data
  } catch (e) {
    message.error('获取角色失败')
  }
}

async function fetchPermissions() {
  loading.value = true
  try {
    const { data } = await adminPermissionsApi.getPermissions()
    permissions.value = data
  } catch (e) {
    message.error('获取权限失败')
  } finally {
    loading.value = false
  }
}

async function createRole() {
  if (!roleForm.value.name) return
  saving.value = true
  try {
    await adminPermissionsApi.createRole(roleForm.value)
    message.success('角色创建成功')
    showRoleModal.value = false
    roleForm.value = { name: '', description: '' }
    await fetchRoles()
  } catch (e) {
    message.error('创建失败')
  } finally {
    saving.value = false
  }
}

async function createPermission() {
  if (!permForm.value.name || !permForm.value.resource || !permForm.value.action) return
  saving.value = true
  try {
    await adminPermissionsApi.createPermission(permForm.value)
    message.success('权限创建成功')
    showPermModal.value = false
    permForm.value = { name: '', description: '', resource: '', action: '' }
    await fetchPermissions()
  } catch (e) {
    message.error('创建失败')
  } finally {
    saving.value = false
  }
}

async function openAssignPermModal(role: Role) {
  if (role.name === 'superadmin') return
  selectedRole.value = role
  try {
    const { data } = await adminPermissionsApi.getRolePermissions(role.id)
    selectedPermIds.value = data
  } catch (e) {
    selectedPermIds.value = []
  }
  showAssignPermModal.value = true
}

async function saveRolePermissions() {
  if (!selectedRole.value) return
  saving.value = true
  try {
    await adminPermissionsApi.assignPermissionsToRole(selectedRole.value.id, selectedPermIds.value)
    message.success('权限分配成功')
    showAssignPermModal.value = false
  } catch (e) {
    message.error('保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  fetchRoles()
  fetchPermissions()
})
</script>