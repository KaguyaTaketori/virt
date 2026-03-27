<template>
  <n-config-provider :theme-overrides="themeStore.naiveThemeOverrides">
    <n-message-provider>
      <div class="min-h-screen bg-gray-900 text-gray-100">
        <header class="bg-gray-800 border-b border-gray-700 sticky top-0 z-50">
          <nav class="container mx-auto px-4 py-4 flex items-center justify-between">
            <router-link to="/" class="text-2xl font-bold hover:opacity-80 transition" :style="{ color: themeStore.currentTheme.colors.primary }">
              VTuber Live
            </router-link>
            <div class="flex items-center gap-4">
              <router-link to="/" class="hover:opacity-80 transition" :style="{ color: themeStore.currentTheme.colors.primary }">首页</router-link>
              <router-link to="/admin/channels" class="hover:opacity-80 transition" :style="{ color: themeStore.currentTheme.colors.primary }">管理</router-link>
              <n-select
                v-model:value="themeStore.currentThemeId"
                :options="themeOptions"
                @update:value="themeStore.setTheme"
                size="small"
                style="width: 130px"
              />
            </div>
          </nav>
        </header>
        
        <main>
          <router-view />
        </main>
        
        <footer class="bg-gray-800 border-t border-gray-700 mt-12 py-6">
          <div class="container mx-auto px-4 text-center text-gray-500">
            <p>VTuber Live Aggregator</p>
          </div>
        </footer>
      </div>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup>
import { computed } from 'vue'
import { NConfigProvider, NMessageProvider, NSelect } from 'naive-ui'
import { useThemeStore } from './stores/theme'

const themeStore = useThemeStore()

const themeOptions = computed(() => 
  themeStore.themes.map(t => ({
    label: t.name,
    value: t.id
  }))
)
</script>
