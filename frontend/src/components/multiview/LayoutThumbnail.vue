<script setup lang="ts">
/**
 * 布局缩略图组件
 * 使用 SVG 矢量绘制，保证比例精确且代码简洁
 */
defineProps<{
  type: string;
  active?: boolean; // 是否处于选中状态
}>()

// 定义颜色常量，方便统一修改
const COLORS = {
  bg: '#09090b',       // 黑色背景
  border: '#27272a',   // 边框色
  main: '#f43f5e',     // 主窗位颜色 (rose-500)
  sub: '#3f3f46',      // 次窗位颜色 (zinc-600)
  stroke: '#18181b'    // 窗位间的缝隙色
}
</script>

<template>
  <svg 
    viewBox="0 0 100 60" 
    class="w-full h-full rounded-md shadow-inner transition-all duration-300"
    :class="active ? 'ring-2 ring-rose-500' : ''"
  >
    <!-- 底槽 -->
    <rect width="100" height="60" :fill="COLORS.bg" />

    <!-- 1本视频 -->
    <template v-if="type === '1-s'">
      <rect x="2" y="2" width="96" height="56" :fill="COLORS.main" rx="2" />
    </template>

    <!-- 2本视频：左右 -->
    <template v-if="type === '2-h'">
      <rect x="2" y="2" width="47" height="56" :fill="COLORS.main" rx="2" />
      <rect x="51" y="2" width="47" height="56" :fill="COLORS.sub" rx="2" />
    </template>

    <!-- 2本视频：上下 -->
    <template v-if="type === '2-v'">
      <rect x="2" y="2" width="96" height="27" :fill="COLORS.main" rx="2" />
      <rect x="2" y="31" width="96" height="27" :fill="COLORS.sub" rx="2" />
    </template>

    <!-- 3本视频：1大2小 (1🎞️ + 2) -->
    <template v-if="type === '3-1+2'">
      <rect x="2" y="2" width="63" height="56" :fill="COLORS.main" rx="2" />
      <rect x="67" y="2" width="31" height="27" :fill="COLORS.sub" rx="2" />
      <rect x="67" y="31" width="31" height="27" :fill="COLORS.sub" rx="2" />
    </template>

    <!-- 3本视频：三列 -->
    <template v-if="type === '3-cols'">
      <rect x="2" y="2" width="30" height="56" :fill="COLORS.main" rx="2" />
      <rect x="34" y="2" width="32" height="56" :fill="COLORS.sub" rx="2" />
      <rect x="68" y="2" width="30" height="56" :fill="COLORS.sub" rx="2" />
    </template>

    <!-- 4本视频：田字格 -->
    <template v-if="type === '4-grid'">
      <rect x="2" y="2" width="47" height="27" :fill="COLORS.main" rx="2" />
      <rect x="51" y="2" width="47" height="27" :fill="COLORS.sub" rx="2" />
      <rect x="2" y="31" width="47" height="27" :fill="COLORS.sub" rx="2" />
      <rect x="51" y="31" width="47" height="27" :fill="COLORS.sub" rx="2" />
    </template>

    <!-- 4本视频：1大3小 -->
    <template v-if="type === '4-1+3'">
      <rect x="2" y="2" width="68" height="56" :fill="COLORS.main" rx="2" />
      <rect x="72" y="2" width="26" height="17" :fill="COLORS.sub" rx="2" />
      <rect x="72" y="21" width="26" height="18" :fill="COLORS.sub" rx="2" />
      <rect x="72" y="41" width="26" height="17" :fill="COLORS.sub" rx="2" />
    </template>
  </svg>
</template>