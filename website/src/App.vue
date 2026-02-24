<template>
  <div class="min-h-screen bg-white dark:bg-gray-950 text-gray-900 dark:text-white transition-colors duration-300">
    <!-- Navigation -->
    <nav class="fixed top-0 left-0 right-0 z-50 glass-card border-b-0">
      <div class="section-container">
        <div class="flex items-center justify-between h-16">
          <!-- Logo -->
          <a href="#" class="flex items-center gap-2">
            <img src="/logo.png" alt="Color Card" class="w-8 h-8 rounded-lg" />
            <span class="font-bold text-lg hidden sm:block">Color Card</span>
          </a>

          <!-- Nav Links -->
          <div class="hidden md:flex items-center gap-8">
            <a href="#features" class="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors">
              {{ t('nav.features') }}
            </a>
            <a href="#palettes" class="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors">
              {{ t('nav.palettes') }}
            </a>
            <a href="#download" class="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors">
              {{ t('nav.download') }}
            </a>
          </div>

          <!-- Actions -->
          <div class="flex items-center gap-2">
            <button
              @click="toggleTheme"
              class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            >
              <Sun v-if="theme === 'dark'" class="w-5 h-5" />
              <Moon v-else class="w-5 h-5" />
            </button>
            <a 
              href="#download"
              class="btn-primary py-2 px-4 text-sm hidden sm:inline-flex"
            >
              {{ t('hero.download') }}
            </a>
          </div>
        </div>
      </div>
    </nav>

    <!-- Main Content -->
    <main>
      <HeroSection />
      <FeatureCard />
      <PaletteBrowser />
      <DownloadSection />
    </main>

    <!-- Footer -->
    <FooterSection />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Sun, Moon } from 'lucide-vue-next'
import { useTheme } from '@/composables/useTheme'
import HeroSection from '@/components/HeroSection.vue'
import FeatureCard from '@/components/FeatureCard.vue'
import PaletteBrowser from '@/components/PaletteBrowser.vue'
import DownloadSection from '@/components/DownloadSection.vue'
import FooterSection from '@/components/FooterSection.vue'

const { t } = useI18n()
const { theme, initTheme, toggleTheme } = useTheme()

onMounted(() => {
  initTheme()
})
</script>
