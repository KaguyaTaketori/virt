<script setup lang="ts">
import { computed } from 'vue'
import { X, Star, StarOff } from 'lucide-vue-next'
import type { Organization } from '@/api'

interface Props {
  modelValue: boolean
  organizations: Organization[]
  likedOrgIds: number[]
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'update:modelValue', val: boolean): void
  (e: 'select', orgId: number): void
}>()

const sortedOrgs = computed(() => {
  const liked: Organization[] = []
  const unliked: Organization[] = []
  
  for (const org of props.organizations) {
    if (props.likedOrgIds.includes(org.id)) {
      liked.push(org)
    } else {
      unliked.push(org)
    }
  }
  
  return { liked, unliked }
})

function close() {
  emit('update:modelValue', false)
}

function selectOrg(orgId: number) {
  emit('select', orgId)
  close()
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="modelValue"
        class="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        @click.self="close"
      >
        <Transition
          appear
          enter-active-class="transition-all duration-200 ease-out"
          enter-from-class="opacity-0 scale-95"
          enter-to-class="opacity-100 scale-100"
          leave-active-class="transition-all duration-150 ease-in"
          leave-from-class="opacity-100 scale-100"
          leave-to-class="opacity-0 scale-95"
        >
          <div
            v-if="modelValue"
            class="w-full max-w-lg bg-zinc-900 border border-zinc-800 rounded-xl shadow-2xl overflow-hidden"
          >
            <!-- Header -->
            <div class="flex items-center justify-between px-5 py-4 border-b border-zinc-800">
              <div>
                <h2 class="text-white font-semibold text-sm">选择分组</h2>
                <p class="text-zinc-500 text-xs mt-0.5">选择机构查看直播成员</p>
              </div>
              <button
                @click="close"
                class="p-1.5 rounded-lg text-zinc-500 hover:text-white hover:bg-zinc-800 transition-colors"
              >
                <X class="w-4 h-4" />
              </button>
            </div>

            <!-- Body -->
            <div class="max-h-[60vh] overflow-y-auto p-4">
              <!-- 已收藏机构 -->
              <div v-if="sortedOrgs.liked.length > 0">
                <div class="flex items-center gap-2 mb-3">
                  <Star class="w-3.5 h-3.5 text-amber-400" />
                  <span class="text-xs font-bold text-amber-400 uppercase tracking-wider">已收藏</span>
                </div>
                <div class="grid grid-cols-2 gap-2 mb-4">
                  <button
                    v-for="org in sortedOrgs.liked"
                    :key="org.id"
                    @click="selectOrg(org.id)"
                    class="flex items-center gap-2 px-3 py-2 rounded-lg bg-zinc-800/50 hover:bg-zinc-700 border border-zinc-700 hover:border-amber-500/50 transition-all text-left"
                  >
                    <img
                      v-if="org.logo_url"
                      :src="org.logo_url"
                      class="w-6 h-6 rounded-full object-cover"
                      referrerpolicy="no-referrer"
                    />
                    <div v-else class="w-6 h-6 rounded-full bg-zinc-700 flex items-center justify-center">
                      <Star class="w-3 h-3 text-amber-400" />
                    </div>
                    <span class="text-sm text-zinc-300 truncate">{{ org.name }}</span>
                  </button>
                </div>
              </div>

              <!-- 未收藏机构 -->
              <div v-if="sortedOrgs.unliked.length > 0">
                <div class="flex items-center gap-2 mb-3">
                  <StarOff class="w-3.5 h-3.5 text-zinc-500" />
                  <span class="text-xs font-bold text-zinc-500 uppercase tracking-wider">全部机构</span>
                </div>
                <div class="grid grid-cols-2 gap-2">
                  <button
                    v-for="org in sortedOrgs.unliked"
                    :key="org.id"
                    @click="selectOrg(org.id)"
                    class="flex items-center gap-2 px-3 py-2 rounded-lg bg-zinc-800/30 hover:bg-zinc-700 border border-zinc-700/50 hover:border-zinc-500 transition-all text-left"
                  >
                    <img
                      v-if="org.logo_url"
                      :src="org.logo_url"
                      class="w-6 h-6 rounded-full object-cover"
                      referrerpolicy="no-referrer"
                    />
                    <div v-else class="w-6 h-6 rounded-full bg-zinc-700 flex items-center justify-center">
                      <span class="text-[10px] text-zinc-400">ORG</span>
                    </div>
                    <span class="text-sm text-zinc-400 truncate">{{ org.name }}</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>