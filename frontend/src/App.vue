<template>
  <n-config-provider :theme="themeStore.isDark ? darkTheme : null" :theme-overrides="themeStore.naiveThemeOverrides">
    <n-message-provider>
      <app-layout />
    </n-message-provider>
  </n-config-provider>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { NConfigProvider, NMessageProvider, darkTheme } from 'naive-ui'
import { useThemeStore } from './stores/theme'
import AppLayout from '@/layouts/AppLayout.vue'

const router = useRouter()
const themeStore = useThemeStore()
</script>