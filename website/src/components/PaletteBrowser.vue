<template>
  <section id="palettes" class="py-24">
    <div class="section-container">
      <!-- Header -->
      <div class="text-center mb-12">
        <h2 class="section-title">{{ t('palettes.title') }}</h2>
        <p class="section-subtitle">
          {{ t('palettes.subtitle') }}
          <span v-if="totalPalettes > 0" class="text-brand-primary font-semibold">
            ({{ totalPalettes }} {{ locale === 'zh-CN' ? '组' : 'sets' }})
          </span>
        </p>
      </div>

      <!-- Category Filter -->
      <div class="flex flex-wrap justify-center gap-3 mb-12">
        <button
          v-for="cat in categories"
          :key="cat.id"
          @click="selectedCategory = cat.id"
          class="px-5 py-2.5 rounded-full font-medium transition-all duration-200"
          :class="selectedCategory === cat.id 
            ? 'bg-brand-primary text-white shadow-lg shadow-brand-primary/30' 
            : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'"
        >
          {{ locale === 'zh-CN' ? cat.name : cat.nameEn }}
        </button>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="text-center py-20">
        <div class="inline-block w-10 h-10 border-4 border-brand-primary/30 border-t-brand-primary rounded-full animate-spin" />
        <p class="mt-4 text-gray-600 dark:text-gray-400">加载中...</p>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="text-center py-20">
        <p class="text-red-500">{{ error }}</p>
      </div>

      <!-- Palettes Grid -->
      <div v-else class="space-y-12">
        <div 
          v-for="paletteSet in filteredPalettes" 
          :key="paletteSet.id"
          class="glass-card rounded-2xl p-6 sm:p-8"
        >
          <!-- Palette Set Header -->
          <div class="flex items-center justify-between mb-6">
            <div>
              <h3 class="text-xl font-bold text-gray-900 dark:text-white">
                {{ locale === 'zh-CN' ? paletteSet.name_zh : paletteSet.name }}
              </h3>
              <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
                {{ paletteSet.description }}
              </p>
            </div>
            <span class="text-sm text-gray-400">
              {{ paletteSet.palettes.length }} {{ locale === 'zh-CN' ? '组' : 'sets' }}
            </span>
          </div>

          <!-- Color Palettes -->
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            <div 
              v-for="palette in paletteSet.palettes.slice(0, 8)" 
              :key="palette.name"
              class="group cursor-pointer"
              @click="copyColor(palette.colors[Math.floor(palette.colors.length / 2)])"
            >
              <div class="glass-card rounded-xl overflow-hidden hover:shadow-lg transition-all duration-200 hover:-translate-y-1">
                <!-- Color Strip -->
                <div class="flex h-16">
                  <div 
                    v-for="(color, idx) in palette.colors.slice(0, 5)" 
                    :key="idx"
                    class="flex-1"
                    :style="{ backgroundColor: color }"
                  />
                </div>
                <!-- Info -->
                <div class="p-3">
                  <p class="font-medium text-gray-900 dark:text-white text-sm truncate">
                    {{ locale === 'zh-CN' ? palette.name : palette.name_en }}
                  </p>
                  <p class="text-xs text-gray-500 mt-1 font-mono">
                    {{ palette.colors[Math.floor(palette.colors.length / 2)] }}
                  </p>
                </div>
              </div>
            </div>
          </div>

          <!-- Show More if needed -->
          <div v-if="paletteSet.palettes.length > 8" class="text-center mt-4">
            <span class="text-sm text-gray-500">
              +{{ paletteSet.palettes.length - 8 }} {{ locale === 'zh-CN' ? '更多' : 'more' }}
            </span>
          </div>
        </div>
      </div>

      <!-- Toast Notification -->
      <Transition
        enter-active-class="transition duration-300 ease-out"
        enter-from-class="transform translate-y-2 opacity-0"
        enter-to-class="transform translate-y-0 opacity-100"
        leave-active-class="transition duration-200 ease-in"
        leave-from-class="transform translate-y-0 opacity-100"
        leave-to-class="transform translate-y-2 opacity-0"
      >
        <div 
          v-if="showToast" 
          class="fixed bottom-8 left-1/2 -translate-x-1/2 px-6 py-3 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-full shadow-lg z-50"
        >
          {{ toastMessage }}
        </div>
      </Transition>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePalettes } from '@/composables/usePalettes'

const { t, locale } = useI18n()
const { 
  palettes, 
  loading, 
  error, 
  categories, 
  selectedCategory, 
  filteredPalettes, 
  totalPalettes, 
  loadPalettes,
  copyColor: copyColorToClipboard 
} = usePalettes()

const showToast = ref(false)
const toastMessage = ref('')

const copyColor = async (color: string) => {
  const success = await copyColorToClipboard(color)
  toastMessage.value = success ? t('palettes.copySuccess') : t('palettes.copyFailed')
  showToast.value = true
  setTimeout(() => {
    showToast.value = false
  }, 2000)
}

onMounted(() => {
  loadPalettes()
})
</script>
