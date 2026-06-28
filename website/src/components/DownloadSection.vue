<template>
  <section id="download" class="py-24 bg-gradient-to-b from-gray-50 to-white dark:from-gray-950 dark:to-gray-900">
    <div class="section-container">
      <!-- Header -->
      <div class="text-center mb-16">
        <h2 class="section-title">下载</h2>
        <p class="section-subtitle">选择适合你的平台，立即开始使用 Color Card</p>
      </div>

      <!-- Download Cards -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto mb-16">
        <!-- Windows Download -->
        <div class="glass-card rounded-2xl p-8 text-center hover:shadow-xl transition-all duration-300">
          <div class="w-16 h-16 mx-auto mb-6 rounded-2xl bg-blue-500/10 flex items-center justify-center">
            <Monitor class="w-8 h-8 text-blue-500" />
          </div>
          <h3 class="text-xl font-bold text-gray-900 dark:text-white mb-2">
            Windows 版
          </h3>
          <p class="text-gray-600 dark:text-gray-400 mb-6">
            支持 Windows 10/11 64 位及以上系统，安装包约 60MB
          </p>
          <a 
            href="https://gitee.com/HxiaoStudio/Color_Card/releases"
            target="_blank"
            class="btn-primary inline-flex items-center gap-2"
          >
            <Download class="w-5 h-5" />
            下载安装包
          </a>
        </div>

        <!-- Source Code -->
        <div class="glass-card rounded-2xl p-8 text-center hover:shadow-xl transition-all duration-300">
          <div class="w-16 h-16 mx-auto mb-6 rounded-2xl bg-purple-500/10 flex items-center justify-center">
            <Code2 class="w-8 h-8 text-purple-500" />
          </div>
          <h3 class="text-xl font-bold text-gray-900 dark:text-white mb-2">
            源码
          </h3>
          <p class="text-gray-600 dark:text-gray-400 mb-6">
            从 GitHub 或 Gitee 获取源码，支持自行编译打包
          </p>
          <a 
            href="https://gitee.com/HxiaoStudio/Color_Card"
            target="_blank"
            class="btn-secondary inline-flex items-center gap-2"
          >
            <GitBranch class="w-5 h-5" />
            Gitee 仓库
          </a>
        </div>
      </div>

      <!-- System Requirements -->
      <div class="glass-card rounded-2xl p-8 max-w-2xl mx-auto">
        <h3 class="text-lg font-bold text-gray-900 dark:text-white mb-6 flex items-center gap-2">
          <Cpu class="w-5 h-5 text-brand-primary" />
          系统要求
        </h3>
        <ul class="space-y-3 text-gray-600 dark:text-gray-400">
          <li class="flex items-center gap-3">
            <div class="w-2 h-2 rounded-full bg-brand-primary" />
            操作系统：Windows 10/11 64位
          </li>
          <li class="flex items-center gap-3">
            <div class="w-2 h-2 rounded-full bg-brand-secondary" />
            Python 3.11 及以上
          </li>
          <li class="flex items-center gap-3">
            <div class="w-2 h-2 rounded-full bg-brand-accent" />
            内存：建议 4GB 及以上
          </li>
          <li class="flex items-center gap-3">
            <div class="w-2 h-2 rounded-full bg-green-500" />
            磁盘：建议 500MB 可用空间
          </li>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import {
  Monitor,
  Download,
  Code2,
  GitBranch,
  Cpu,
} from 'lucide-vue-next'
</script>
