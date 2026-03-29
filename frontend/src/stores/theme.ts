import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { themes, defaultTheme } from '../config/themes'

export const useThemeStore = defineStore('theme', () => {
  const currentThemeId = ref(localStorage.getItem('theme') || defaultTheme.id)
  const isDark = ref(localStorage.getItem('isDark') !== 'false')
  
  const currentTheme = computed(() => 
    themes.find(t => t.id === currentThemeId.value) || defaultTheme
  )
  
  const naiveThemeOverrides = computed(() => ({
    common: {
      primaryColor: currentTheme.value.colors.primary,
      primaryColorHover: currentTheme.value.colors.primaryHover,
      primaryColorPressed: currentTheme.value.colors.primary,
      primaryColorSuppl: currentTheme.value.colors.primary,
    },
    Button: {
      colorPrimary: currentTheme.value.colors.primary,
      colorHoverPrimary: currentTheme.value.colors.primaryHover,
      colorPressedPrimary: currentTheme.value.colors.primary,
    },
    Tag: {
      colorPrimary: currentTheme.value.colors.primary,
      borderColorPrimary: currentTheme.value.colors.primary,
    }
  }))
  
  function setTheme(themeId: string) {
    currentThemeId.value = themeId
    localStorage.setItem('theme', themeId)
  }
  
  function toggleDark() {
    isDark.value = !isDark.value
    localStorage.setItem('isDark', String(isDark.value))
  }
  
  return { 
    themes, 
    currentThemeId, 
    currentTheme, 
    naiveThemeOverrides,
    isDark,
    setTheme,
    toggleDark
  }
})
