import { ref, computed } from 'vue'

export interface Palette {
  name: string
  name_en: string
  colors: string[]
}

export interface PaletteSet {
  version: string
  id: string
  name: string
  name_zh: string
  description: string
  author: string
  category: 'design_system' | 'terminal' | 'artistic'
  palettes: Palette[]
}

const paletteFiles = [
  'open_color.json',
  'tailwind_colors.json',
  'material_design.json',
  'radix_colors.json',
  'colorbrewer.json',
  'nord.json',
  'dracula.json',
  'solarized.json',
  'gruvbox.json',
  'catppuccin.json',
  'rose_pine.json',
  'tokyo_night.json',
  'nice_palettes.json',
]

export function usePalettes() {
  const palettes = ref<PaletteSet[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const selectedCategory = ref<string>('all')

  const categories = [
    { id: 'all', name: '全部', nameEn: 'All' },
    { id: 'design_system', name: '设计系统', nameEn: 'Design System' },
    { id: 'terminal', name: '终端主题', nameEn: 'Terminal' },
    { id: 'artistic', name: '艺术配色', nameEn: 'Artistic' },
  ]

  const filteredPalettes = computed(() => {
    if (selectedCategory.value === 'all') {
      return palettes.value
    }
    return palettes.value.filter(p => p.category === selectedCategory.value)
  })

  const totalPalettes = computed(() => {
    return palettes.value.reduce((sum, p) => sum + p.palettes.length, 0)
  })

  const loadPalettes = async () => {
    loading.value = true
    error.value = null

    try {
      const loaded: PaletteSet[] = []
      for (const file of paletteFiles) {
        try {
          const response = await fetch(`/palettes/${file}`)
          if (response.ok) {
            const data = await response.json()
            loaded.push(data)
          }
        } catch (e) {
          console.warn(`Failed to load ${file}:`, e)
        }
      }
      palettes.value = loaded
    } catch (e) {
      error.value = 'Failed to load palettes'
      console.error(e)
    } finally {
      loading.value = false
    }
  }

  const copyColor = async (color: string): Promise<boolean> => {
    try {
      await navigator.clipboard.writeText(color)
      return true
    } catch (e) {
      console.error('Failed to copy:', e)
      return false
    }
  }

  return {
    palettes,
    loading,
    error,
    categories,
    selectedCategory,
    filteredPalettes,
    totalPalettes,
    loadPalettes,
    copyColor,
  }
}
