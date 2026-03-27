<template>
  <div class="min-h-screen bg-gray-900 text-gray-100">
    <header class="bg-gray-800 border-b border-gray-700 sticky top-0 z-50">
      <nav class="container mx-auto px-4 py-4 flex items-center justify-between">
        <router-link to="/" class="text-2xl font-bold text-pink-500 hover:text-pink-400 transition">
          VTuber Live
        </router-link>
        <div class="flex gap-6">
          <router-link to="/" class="hover:text-pink-400 transition">首页</router-link>
          <router-link to="/admin/channels" class="hover:text-pink-400 transition">管理</router-link>
        </div>
      </nav>
    </header>
    
    <main>
      <router-view />
    </main>
    
    <footer class="bg-gray-800 border-t border-gray-700 mt-12 py-6">
      <div class="container mx-auto px-4 text-center text-gray-500">
        <p>VTuber Live Aggregator - MVP</p>
      </div>
    </footer>
  </div>
</template>

<script setup>
</script>