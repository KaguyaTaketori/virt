<template>
  <n-config-provider :theme="themeStore.isDark ? darkTheme : null" :theme-overrides="themeStore.naiveThemeOverrides">
    <app-layout />
    <n-message-provider />
  </n-config-provider>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { NConfigProvider, NMessageProvider, NSelect, NSwitch, NDropdown, NButton, darkTheme } from 'naive-ui'
import { useThemeStore } from './stores/theme'
import AppLayout from '@/layouts/AppLayout.vue'

const router = useRouter()
const themeStore = useThemeStore()

const adminMenuOptions = [
  { label: '频道管理', key: 'channels' },
  { label: '机构管理', key: 'organizations' }
]

function handleAdminMenu(key) {
  router.push(`/admin/${key}`)
}

const themeOptions = computed(() => 
  themeStore.themes.map(t => ({
    label: t.name,
    value: t.id
  }))
)
</script>
