<template>
  <section class="relative min-h-screen flex items-center justify-center overflow-hidden">
    <!-- Animated Background -->
    <div class="absolute inset-0 overflow-hidden">
      <div 
        class="absolute inset-0 bg-gradient-to-br from-brand-primary/20 via-transparent to-brand-secondary/20 dark:from-brand-primary/10 dark:to-brand-secondary/10"
        :style="gradientStyle"
      />
      <div class="absolute top-20 left-10 w-72 h-72 bg-brand-primary/30 rounded-full blur-3xl animate-float" />
      <div class="absolute bottom-20 right-10 w-96 h-96 bg-brand-secondary/30 rounded-full blur-3xl animate-float animation-delay-500" />
      <div class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-brand-accent/20 rounded-full blur-3xl animate-float animation-delay-300" />
    </div>

    <!-- Content -->
    <div class="relative z-10 section-container text-center">
      <!-- Badge -->
      <div class="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm border border-gray-200 dark:border-gray-700 mb-8 animate-fade-in">
        <span class="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
        <span class="text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('hero.badge') }}</span>
      </div>

      <!-- Logo -->
      <div class="mb-8 animate-fade-in animation-delay-100">
        <img 
          src="/logo.png" 
          alt="Color Card" 
          class="w-32 h-32 mx-auto drop-shadow-2xl hover:scale-105 transition-transform duration-300"
        />
      </div>

      <!-- Title -->
      <h1 class="text-4xl sm:text-5xl lg:text-7xl font-bold mb-6 animate-fade-in animation-delay-200">
        <span class="gradient-text">{{ t('hero.title') }}</span>
      </h1>

      <!-- Subtitle -->
      <p class="text-xl sm:text-2xl text-gray-700 dark:text-gray-300 mb-4 animate-fade-in animation-delay-300">
        {{ t('hero.subtitle') }}
      </p>

      <!-- Description -->
      <p class="text-base sm:text-lg text-gray-600 dark:text-gray-400 max-w-2xl mx-auto mb-10 animate-fade-in animation-delay-400">
        {{ t('hero.description') }}
      </p>

      <!-- CTA Buttons -->
      <div class="flex flex-col sm:flex-row items-center justify-center gap-4 animate-fade-in animation-delay-500">
        <a 
          href="#download" 
          class="btn-primary text-lg px-8 py-4"
        >
          {{ t('hero.download') }}
        </a>
        <a 
          href="#features" 
          class="btn-secondary text-lg px-8 py-4"
        >
          {{ t('hero.learnMore') }}
        </a>
      </div>

      <!-- Stats -->
      <div class="mt-16 grid grid-cols-3 gap-8 max-w-lg mx-auto animate-fade-in animation-delay-500">
        <div class="text-center">
          <div class="text-3xl sm:text-4xl font-bold text-brand-primary">13</div>
          <div class="text-sm text-gray-600 dark:text-gray-400 mt-1">配色方案</div>
        </div>
        <div class="text-center">
          <div class="text-3xl sm:text-4xl font-bold text-brand-secondary">661</div>
          <div class="text-sm text-gray-600 dark:text-gray-400 mt-1">色卡组</div>
        </div>
        <div class="text-center">
          <div class="text-3xl sm:text-4xl font-bold text-brand-accent">8</div>
          <div class="text-sm text-gray-600 dark:text-gray-400 mt-1">预览场景</div>
        </div>
      </div>
    </div>

    <!-- Scroll Indicator -->
    <div class="absolute bottom-8 left-1/2 -translate-x-1/2 animate-bounce">
      <svg class="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
      </svg>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const mouseX = ref(0)
const mouseY = ref(0)

const gradientStyle = ref({
  background: 'radial-gradient(circle at 50% 50%, rgba(255, 107, 107, 0.15) 0%, transparent 50%)'
})

const handleMouseMove = (e: MouseEvent) => {
  mouseX.value = e.clientX / window.innerWidth
  mouseY.value = e.clientY / window.innerHeight
  
  gradientStyle.value = {
    background: `radial-gradient(circle at ${mouseX.value * 100}% ${mouseY.value * 100}%, rgba(255, 107, 107, 0.2) 0%, rgba(21, 170, 191, 0.2) 50%, transparent 70%)`
  }
}

onMounted(() => {
  window.addEventListener('mousemove', handleMouseMove)
})

onUnmounted(() => {
  window.removeEventListener('mousemove', handleMouseMove)
})
</script>
