<template>
  <n-config-provider :theme="isDark ? darkTheme : null" :theme-overrides="themeStore.naiveThemeOverrides">
    <app-layout />
    <n-message-provider />
  </n-config-provider>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { NConfigProvider, NMessageProvider, NSelect, NSwitch, NDropdown, NButton, darkTheme } from 'naive-ui'
import { useThemeStore } from './stores/theme'
import AppLayout from '@/layouts/AppLayout.vue'

const router = useRouter()
const themeStore = useThemeStore()
const isDark = ref(true)

const adminMenuOptions = [
  { label: '频道管理', key: 'channels' },
  { label: '机构管理', key: 'organizations' }
]

function handleAdminMenu(key) {
  router.push(`/admin/${key}`)
}

// 从 localStorage 恢复主题设置
onMounted(() => {
  const savedDark = localStorage.getItem('isDark')
  if (savedDark !== null) {
    isDark.value = savedDark === 'true'
  }
})

// 切换时保存
function toggleDark(value) {
  isDark.value = value
  localStorage.setItem('isDark', String(value))
}

const themeOptions = computed(() => 
  themeStore.themes.map(t => ({
    label: t.name,
    value: t.id
  }))
)
</script>
