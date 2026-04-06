<template>
  <div class="min-h-screen bg-zinc-950 px-4 py-8">
    <div class="max-w-3xl mx-auto">
      <h1 class="text-3xl font-bold text-white mb-6">设置</h1>
      
      <div class="flex gap-2 mb-6 border-b border-zinc-800 pb-2">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          :class="[
            'flex items-center gap-2 px-5 py-2.5 rounded-t-lg cursor-pointer text-sm transition-all',
            activeTab === tab.id
              ? 'bg-zinc-800 text-white border-b-2 border-pink-500 -mb-2.5 pb-3'
              : 'text-zinc-400 hover:text-white hover:bg-zinc-900'
          ]"
          @click="activeTab = tab.id"
        >
          <component :is="tab.icon" class="w-4 h-4" />
          <span>{{ tab.label }}</span>
        </button>
      </div>

      <div class="bg-zinc-900 rounded-lg p-6 min-h-[400px]">
        <BilibiliLogin v-if="activeTab === 'bilibili'" />
        <div v-else-if="activeTab === 'theme'" class="text-white">
          <h2 class="text-lg font-semibold mb-5">主题设置</h2>
          <div class="flex gap-4">
            <label class="flex flex-col items-center gap-2 cursor-pointer">
              <input type="radio" v-model="theme" value="light" class="hidden" />
              <span :class="[
                'flex flex-col items-center gap-2 p-3 rounded-lg border-2 transition-all',
                theme === 'light' ? 'border-pink-500 bg-zinc-800' : 'border-zinc-700 hover:border-zinc-600'
              ]">
                <span class="w-14 h-10 rounded bg-white border border-zinc-300"></span>
                <span class="text-sm text-zinc-400">浅色</span>
              </span>
            </label>
            <label class="flex flex-col items-center gap-2 cursor-pointer">
              <input type="radio" v-model="theme" value="dark" class="hidden" />
              <span :class="[
                'flex flex-col items-center gap-2 p-3 rounded-lg border-2 transition-all',
                theme === 'dark' ? 'border-pink-500 bg-zinc-800' : 'border-zinc-700 hover:border-zinc-600'
              ]">
                <span class="w-14 h-10 rounded bg-zinc-800 border border-zinc-600"></span>
                <span class="text-sm text-zinc-400">深色</span>
              </span>
            </label>
            <label class="flex flex-col items-center gap-2 cursor-pointer">
              <input type="radio" v-model="theme" value="system" class="hidden" />
              <span :class="[
                'flex flex-col items-center gap-2 p-3 rounded-lg border-2 transition-all',
                theme === 'system' ? 'border-pink-500 bg-zinc-800' : 'border-zinc-700 hover:border-zinc-600'
              ]">
                <span class="w-14 h-10 rounded bg-gradient-to-r from-white to-zinc-800 border border-zinc-600"></span>
                <span class="text-sm text-zinc-400">跟随系统</span>
              </span>
            </label>
          </div>
        </div>
        <div v-else-if="activeTab === 'other'" class="text-white">
          <h2 class="text-lg font-semibold mb-5">其他设置</h2>
          <p class="text-zinc-500 text-center py-10">暂无其他设置</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, markRaw } from 'vue'
import { Link, Sun, Settings } from 'lucide-vue-next'
import BilibiliLogin from './BilibiliLogin.vue'

const tabs = [
  { id: 'bilibili', label: 'B站账号', icon: markRaw(Link) },
  { id: 'theme', label: '主题', icon: markRaw(Sun) },
  { id: 'other', label: '其他', icon: markRaw(Settings) },
]

const activeTab = ref('bilibili')
const theme = ref('dark')
</script>
