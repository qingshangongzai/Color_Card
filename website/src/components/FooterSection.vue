<template>
  <footer class="bg-gray-900 dark:bg-black text-white py-16">
    <div class="section-container">
      <div class="grid grid-cols-1 md:grid-cols-5 gap-12 mb-12">
        <!-- Brand -->
        <div class="md:col-span-2">
          <div class="flex items-center gap-3 mb-4">
            <img src="/logo.png" alt="Color Card" class="w-10 h-10 rounded-lg" />
            <span class="text-xl font-bold">Color Card</span>
          </div>
          <p class="text-gray-400 max-w-sm">
            强大的桌面端配色工具，助你轻松完成色彩提取、管理与分析
          </p>
        </div>

        <!-- Links -->
        <div>
          <h4 class="font-semibold mb-4">产品</h4>
          <ul class="space-y-2 text-gray-400">
            <li><a href="#features" class="hover:text-white transition-colors">功能特性</a></li>
            <li><a href="#palettes" class="hover:text-white transition-colors">配色方案</a></li>
            <li><a href="#download" class="hover:text-white transition-colors">下载</a></li>
          </ul>
        </div>

        <div>
          <h4 class="font-semibold mb-4">资源</h4>
          <ul class="space-y-2 text-gray-400">
            <li>
              <a href="https://github.com/qingshangongzai/Color_Card" target="_blank" class="hover:text-white transition-colors flex items-center gap-2">
                <Github class="w-4 h-4" />
                GitHub
              </a>
            </li>
            <li>
              <a href="https://gitee.com/HxiaoStudio/Color_Card" target="_blank" class="hover:text-white transition-colors flex items-center gap-2">
                <GitBranch class="w-4 h-4" />
                Gitee
              </a>
            </li>
          </ul>
        </div>

        <!-- Social -->
        <div>
          <h4 class="font-semibold mb-4">社交</h4>
          <ul class="space-y-2 text-gray-400">
            <li>
              <a href="https://space.bilibili.com/1232406878" target="_blank" class="hover:text-white transition-colors flex items-center gap-2">
                <svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M17.813 4.653h.854c1.51.054 2.769.578 3.773 1.574 1.004.995 1.524 2.249 1.56 3.76v7.36c-.036 1.51-.556 2.769-1.56 3.773s-2.262 1.524-3.773 1.56H5.333c-1.51-.036-2.769-.556-3.773-1.56S.036 18.858 0 17.347v-7.36c.036-1.511.556-2.765 1.56-3.76 1.004-.996 2.262-1.52 3.773-1.574h.774l-1.174-1.12a1.234 1.234 0 0 1-.373-.906c0-.356.124-.658.373-.907l.027-.027c.267-.249.573-.373.92-.373.347 0 .653.124.92.373L9.653 4.44c.071.071.134.142.187.213h4.267a.836.836 0 0 1 .16-.213l2.853-2.747c.267-.249.573-.373.92-.373.347 0 .662.151.929.4.267.249.391.551.391.907 0 .355-.124.657-.373.906zM5.333 7.24c-.746.018-1.373.276-1.88.773-.506.498-.769 1.13-.786 1.894v7.52c.017.764.28 1.395.786 1.893.507.498 1.134.756 1.88.773h13.334c.746-.017 1.373-.275 1.88-.773.506-.498.769-1.129.786-1.893v-7.52c-.017-.765-.28-1.396-.786-1.894-.507-.497-1.134-.755-1.88-.773zM8 11.107c.373 0 .684.124.933.373.25.249.383.569.4.96v1.173c-.017.391-.15.711-.4.96-.249.25-.56.374-.933.374s-.684-.125-.933-.374c-.25-.249-.383-.569-.4-.96V12.44c0-.373.129-.689.386-.947.258-.257.574-.386.947-.386zm8 0c.373 0 .684.124.933.373.25.249.383.569.4.96v1.173c-.017.391-.15.711-.4.96-.249.25-.56.374-.933.374s-.684-.125-.933-.374c-.25-.249-.383-.569-.4-.96V12.44c.017-.391.15-.711.4-.96.249-.249.56-.373.933-.373z"/>
                </svg>
                Bilibili
              </a>
            </li>
          </ul>
        </div>
      </div>

      <!-- Bottom -->
      <div class="pt-8 border-t border-gray-800 flex flex-col sm:flex-row items-center justify-between gap-4">
        <p class="text-gray-500 text-sm">
          © 2026 浮晓 HXiao Studio. All rights reserved.
        </p>
        <div class="flex items-center gap-4">
          <!-- Theme Toggle -->
          <button
            @click="toggleTheme"
            class="p-2 rounded-lg bg-gray-800 text-gray-400 hover:text-white transition-colors"
          >
            <Sun v-if="theme === 'dark'" class="w-5 h-5" />
            <Moon v-else class="w-5 h-5" />
          </button>
        </div>
      </div>

      <!-- License -->
      <div class="mt-8 text-center">
        <a 
          href="https://www.gnu.org/licenses/gpl-3.0.html" 
          target="_blank"
          class="inline-flex items-center gap-2 text-gray-500 hover:text-gray-300 text-sm transition-colors"
        >
          <Scale class="w-4 h-4" />
          GNU General Public License v3.0
        </a>
      </div>
    </div>
  </footer>
</template>

<script setup lang="ts">
import { Github, GitBranch, Sun, Moon, Scale } from 'lucide-vue-next'
import { useTheme } from '@/composables/useTheme'

const { theme, toggleTheme } = useTheme()
</script>
