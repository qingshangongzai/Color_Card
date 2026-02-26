<template>
  <section id="features" class="py-24 bg-gray-50 dark:bg-gray-950">
    <div class="section-container">
      <!-- Header -->
      <div class="text-center mb-16">
        <h2 class="section-title">{{ t('features.title') }}</h2>
        <p class="section-subtitle">{{ t('features.subtitle') }}</p>
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
            {{ t(`features.${feature.key}.title`) }}
          </h3>

          <!-- Description -->
          <p class="text-gray-600 dark:text-gray-400 leading-relaxed">
            {{ t(`features.${feature.key}.description`) }}
          </p>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import {
  Pipette,
  Palette,
  Bookmark,
  Library,
  Eye,
  BarChart3,
} from 'lucide-vue-next'

const { t } = useI18n()

const features = [
  { key: 'colorExtract', icon: Pipette },
  { key: 'colorGeneration', icon: Palette },
  { key: 'paletteManagement', icon: Bookmark },
  { key: 'builtInPalettes', icon: Library },
  { key: 'colorPreview', icon: Eye },
  { key: 'luminanceAnalysis', icon: BarChart3 },
]
</script>
