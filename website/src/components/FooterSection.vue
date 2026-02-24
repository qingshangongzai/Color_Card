<template>
  <footer class="bg-gray-900 dark:bg-black text-white py-16">
    <div class="section-container">
      <div class="grid grid-cols-1 md:grid-cols-4 gap-12 mb-12">
        <!-- Brand -->
        <div class="md:col-span-2">
          <div class="flex items-center gap-3 mb-4">
            <img src="/logo.png" alt="Color Card" class="w-10 h-10 rounded-lg" />
            <span class="text-xl font-bold">Color Card</span>
          </div>
          <p class="text-gray-400 max-w-sm">
            {{ t('footer.description') }}
          </p>
        </div>

        <!-- Links -->
        <div>
          <h4 class="font-semibold mb-4">{{ t('footer.links.product') }}</h4>
          <ul class="space-y-2 text-gray-400">
            <li><a href="#features" class="hover:text-white transition-colors">{{ t('nav.features') }}</a></li>
            <li><a href="#palettes" class="hover:text-white transition-colors">{{ t('nav.palettes') }}</a></li>
            <li><a href="#download" class="hover:text-white transition-colors">{{ t('nav.download') }}</a></li>
          </ul>
        </div>

        <div>
          <h4 class="font-semibold mb-4">{{ t('footer.links.resources') }}</h4>
          <ul class="space-y-2 text-gray-400">
            <li>
              <a href="https://github.com/qingshangongzai/Color_Card" target="_blank" class="hover:text-white transition-colors flex items-center gap-2">
                <Github class="w-4 h-4" />
                GitHub
              </a>
            </li>
            <li>
              <a href="https://gitee.com/qingshangongzai/color_card" target="_blank" class="hover:text-white transition-colors flex items-center gap-2">
                <GitBranch class="w-4 h-4" />
                Gitee
              </a>
            </li>
          </ul>
        </div>
      </div>

      <!-- Bottom -->
      <div class="pt-8 border-t border-gray-800 flex flex-col sm:flex-row items-center justify-between gap-4">
        <p class="text-gray-500 text-sm">
          {{ t('footer.copyright') }}
        </p>
        <div class="flex items-center gap-4">
          <!-- Language Switcher -->
          <div class="flex items-center gap-2 bg-gray-800 rounded-lg p-1">
            <button
              v-for="lang in languages"
              :key="lang.code"
              @click="changeLanguage(lang.code)"
              class="px-3 py-1.5 rounded-md text-sm font-medium transition-all duration-200"
              :class="locale === lang.code 
                ? 'bg-brand-primary text-white' 
                : 'text-gray-400 hover:text-white'"
            >
              {{ lang.name }}
            </button>
          </div>
          
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
          {{ t('footer.license') }}
        </a>
      </div>
    </div>
  </footer>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { Github, GitBranch, Sun, Moon, Scale } from 'lucide-vue-next'
import { useTheme } from '@/composables/useTheme'

const { t, locale } = useI18n()
const { theme, toggleTheme } = useTheme()

const languages = [
  { code: 'zh-CN', name: '中文' },
  { code: 'en-US', name: 'EN' },
]

const changeLanguage = (code: string) => {
  locale.value = code
}
</script>
