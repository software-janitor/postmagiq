import { useThemeStore } from '../stores/themeStore'
import { THEMES, generateThemeClasses, ThemeId } from '../config/themes'

const DEFAULT_THEME: ThemeId = 'emerald'

export function useThemeClasses() {
  const { currentTheme } = useThemeStore()
  const config = THEMES[currentTheme] || THEMES[DEFAULT_THEME]
  return generateThemeClasses(config)
}

export function getThemeClasses(themeId: ThemeId) {
  const config = THEMES[themeId] || THEMES[DEFAULT_THEME]
  return generateThemeClasses(config)
}
