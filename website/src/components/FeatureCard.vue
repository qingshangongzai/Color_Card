<template>
  <section id="features" class="py-24 bg-gray-50 dark:bg-gray-950">
    <div class="section-container">
      <!-- Header -->
      <div class="text-center mb-16">
        <h2 class="section-title">功能特性</h2>
        <p class="section-subtitle">一站式配色解决方案，从提取到管理，满足你的所有色彩需求</p>
      </div>

      <!-- Features Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        <div 
          v-for="(feature, index) in features" 
          :key="feature.key"
          class="group glass-card rounded-2xl p-8 hover:shadow-xl transition-all duration-300 hover:-translate-y-1"
          :style="{ animationDelay: `${index * 100}ms` }"
        >
          <!-- Icon -->
          <div class="w-14 h-14 rounded-xl bg-gradient-to-br from-brand-primary/20 to-brand-secondary/20 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
            <component 
              :is="feature.icon" 
              class="w-7 h-7 text-brand-primary"
            />
          </div>

          <!-- Title -->
          <h3 class="text-xl font-bold text-gray-900 dark:text-white mb-3">
            {{ feature.title }}
          </h3>

          <!-- Description -->
          <p class="text-gray-600 dark:text-gray-400 leading-relaxed">
            {{ feature.description }}
          </p>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import {
  Pipette,
  Palette,
  Bookmark,
  Library,
  Eye,
  BarChart3,
} from 'lucide-vue-next'

const features = [
  { key: 'colorAnalysis', icon: Pipette, title: '颜色分析', description: '从图片中精准提取颜色，支持多种颜色空间，快速获取任意位置的色彩信息' },
  { key: 'colorGeneration', icon: Palette, title: '颜色生成', description: '基于色彩理论智能生成配色方案，轻松获得和谐美观的颜色组合' },
  { key: 'paletteManagement', icon: Bookmark, title: '色卡管理', description: '创建和管理自定义色卡，支持分类整理、导入导出，让配色井井有条' },
  { key: 'builtInPalettes', icon: Library, title: '内置色板', description: '内置多套知名设计系统与终端配色方案，开箱即用，灵感随手可得' },
  { key: 'colorPreview', icon: Eye, title: '颜色预览', description: '在多种场景下预览颜色效果，确保配色在实际应用中表现完美' },
  { key: 'luminanceAnalysis', icon: BarChart3, title: '亮度分析', description: '分析颜色明度与对比度，确保文本可读性和视觉层次感' },
]
</script>
