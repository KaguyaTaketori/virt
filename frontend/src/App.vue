<template>
  <n-config-provider :theme="isDark ? darkTheme : null" :theme-overrides="themeStore.naiveThemeOverrides">
    <n-message-provider>
      <div class="min-h-screen transition-colors duration-300" :class="isDark ? 'bg-[#18181c]' : 'bg-gray-100'">
        <header class="transition-colors duration-300 sticky top-0 z-50 border-b" :class="isDark ? 'bg-[#242428] border-[#303035]' : 'bg-white border-gray-200'">
          <nav class="container mx-auto px-4 py-4 flex items-center justify-between">
            <router-link to="/" class="text-2xl font-bold hover:opacity-80 transition" :style="{ color: themeStore.currentTheme.colors.primary }">
              VTuber Live
            </router-link>
            <div class="flex items-center gap-4">
              <router-link to="/" class="transition" :style="{ color: themeStore.currentTheme.colors.primary }">首页</router-link>
              <router-link to="/admin/channels" class="transition" :style="{ color: themeStore.currentTheme.colors.primary }">管理</router-link>
              <n-select
                v-model:value="themeStore.currentThemeId"
                :options="themeOptions"
                @update:value="themeStore.setTheme"
                size="small"
                style="width: 130px"
              />
              <n-switch v-model:value="isDark" @update:value="toggleDark">
                <template #checked>
                  🌙
                </template>
                <template #unchecked>
                  ☀️
                </template>
              </n-switch>
            </div>
          </nav>
        </header>
        
        <main class="transition-colors duration-300" :class="isDark ? 'text-gray-200' : 'text-gray-800'">
          <router-view />
        </main>
        
        <footer class="transition-colors duration-300 mt-12 py-6 border-t" :class="isDark ? 'bg-[#242428] border-[#303035] text-gray-500' : 'bg-white border-gray-200 text-gray-500'">
          <div class="container mx-auto px-4 text-center">
            <p>VTuber Live Aggregator</p>
          </div>
        </footer>
      </div>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { NConfigProvider, NMessageProvider, NSelect, NSwitch, darkTheme } from 'naive-ui'
import { useThemeStore } from './stores/theme'

const themeStore = useThemeStore()
const isDark = ref(true)

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
