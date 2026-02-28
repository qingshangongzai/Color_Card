import { ref, watch } from 'vue'

type Theme = 'light' | 'dark'

const STORAGE_KEY = 'color-card-theme'

export function useTheme() {
  const theme = ref<Theme>('light')

  const initTheme = () => {
    const saved = localStorage.getItem(STORAGE_KEY) as Theme | null
    if (saved) {
      theme.value = saved
    } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
      theme.value = 'dark'
    }
    applyTheme()
  }

  const applyTheme = () => {
    if (theme.value === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }

  const toggleTheme = () => {
    theme.value = theme.value === 'light' ? 'dark' : 'light'
    localStorage.setItem(STORAGE_KEY, theme.value)
    applyTheme()
  }

  const setTheme = (newTheme: Theme) => {
    theme.value = newTheme
    localStorage.setItem(STORAGE_KEY, newTheme)
    applyTheme()
  }

  watch(theme, applyTheme)

  return {
    theme,
    initTheme,
    toggleTheme,
    setTheme,
  }
}
