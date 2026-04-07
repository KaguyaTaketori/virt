<script setup lang="ts">
import { ref, computed, provide } from 'vue'
import { useRoute } from 'vue-router'
import GlobalHeader from '@/components/GlobalHeader.vue'
import NavigationSidebar from '@/components/NavigationSidebar.vue'

const isSidebarCollapsed = ref<boolean>(
  localStorage.getItem('sidebarCollapsed') === 'true'
)

function toggleSidebar(): void {
  isSidebarCollapsed.value = !isSidebarCollapsed.value
  localStorage.setItem('sidebarCollapsed', String(isSidebarCollapsed.value))
}

const route = useRoute()

const isFullscreen = computed<boolean>(
  () => route.meta.fullscreen === true
)

const mainScrollRef = ref<HTMLElement | null>(null)
provide('mainScrollRef', mainScrollRef)
</script>

<template>
  <div class="h-screen w-screen overflow-hidden bg-zinc-950 text-white flex flex-col">
    <template v-if="isFullscreen">
      <div class="flex-1 min-h-0 relative">
        <router-view />
      </div>
    </template>
    <template v-else>
      <GlobalHeader
        :is-sidebar-collapsed="isSidebarCollapsed"
        @toggle-sidebar="toggleSidebar"
      />
      <div class="flex flex-1 min-h-0 overflow-hidden">
        <NavigationSidebar :is-collapsed="isSidebarCollapsed" />
        <main ref="mainScrollRef" class="flex-1 min-w-0 overflow-y-auto bg-zinc-900">
          <router-view />
        </main>
      </div>
    </template>
  </div>
</template>