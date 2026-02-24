<template>
  <section id="download" class="py-24 bg-gradient-to-b from-gray-50 to-white dark:from-gray-950 dark:to-gray-900">
    <div class="section-container">
      <!-- Header -->
      <div class="text-center mb-16">
        <h2 class="section-title">{{ t('download.title') }}</h2>
        <p class="section-subtitle">{{ t('download.subtitle') }}</p>
      </div>

      <!-- Download Cards -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto mb-16">
        <!-- Windows Download -->
        <div class="glass-card rounded-2xl p-8 text-center hover:shadow-xl transition-all duration-300">
          <div class="w-16 h-16 mx-auto mb-6 rounded-2xl bg-blue-500/10 flex items-center justify-center">
            <Monitor class="w-8 h-8 text-blue-500" />
          </div>
          <h3 class="text-xl font-bold text-gray-900 dark:text-white mb-2">
            {{ t('download.windows.title') }}
          </h3>
          <p class="text-gray-600 dark:text-gray-400 mb-6">
            {{ t('download.windows.description') }}
          </p>
          <a 
            href="https://gitee.com/qingshangongzai/color_card/releases"
            target="_blank"
            class="btn-primary inline-flex items-center gap-2"
          >
            <Download class="w-5 h-5" />
            {{ t('download.windows.button') }}
          </a>
        </div>

        <!-- Source Code -->
        <div class="glass-card rounded-2xl p-8 text-center hover:shadow-xl transition-all duration-300">
          <div class="w-16 h-16 mx-auto mb-6 rounded-2xl bg-purple-500/10 flex items-center justify-center">
            <Code2 class="w-8 h-8 text-purple-500" />
          </div>
          <h3 class="text-xl font-bold text-gray-900 dark:text-white mb-2">
            {{ t('download.source.title') }}
          </h3>
          <p class="text-gray-600 dark:text-gray-400 mb-6">
            {{ t('download.source.description') }}
          </p>
          <div class="flex gap-3 justify-center">
            <a 
              href="https://github.com/qingshangongzai/Color_Card"
              target="_blank"
              class="btn-secondary inline-flex items-center gap-2"
            >
              <Github class="w-5 h-5" />
              {{ t('download.source.github') }}
            </a>
            <a 
              href="https://gitee.com/qingshangongzai/color_card"
              target="_blank"
              class="btn-secondary inline-flex items-center gap-2"
            >
              <GitBranch class="w-5 h-5" />
              {{ t('download.source.gitee') }}
            </a>
          </div>
        </div>
      </div>

      <!-- System Requirements -->
      <div class="glass-card rounded-2xl p-8 max-w-2xl mx-auto">
        <h3 class="text-lg font-bold text-gray-900 dark:text-white mb-6 flex items-center gap-2">
          <Cpu class="w-5 h-5 text-brand-primary" />
          {{ t('download.requirements.title') }}
        </h3>
        <ul class="space-y-3 text-gray-600 dark:text-gray-400">
          <li class="flex items-center gap-3">
            <div class="w-2 h-2 rounded-full bg-brand-primary" />
            {{ t('download.requirements.os') }}
          </li>
          <li class="flex items-center gap-3">
            <div class="w-2 h-2 rounded-full bg-brand-secondary" />
            {{ t('download.requirements.python') }}
          </li>
          <li class="flex items-center gap-3">
            <div class="w-2 h-2 rounded-full bg-brand-accent" />
            {{ t('download.requirements.memory') }}
          </li>
          <li class="flex items-center gap-3">
            <div class="w-2 h-2 rounded-full bg-green-500" />
            {{ t('download.requirements.disk') }}
          </li>
        </ul>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import {
  Monitor,
  Download,
  Code2,
  Github,
  GitBranch,
  Cpu,
} from 'lucide-vue-next'

const { t } = useI18n()
</script>
