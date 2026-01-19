import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { THEMES, ThemeId } from '../config/themes'

// Default theme to fall back to
const DEFAULT_THEME: ThemeId = 'emerald'

// Validate that a theme exists
function isValidTheme(theme: string): theme is ThemeId {
  return theme in THEMES
}

interface ThemeState {
  currentTheme: ThemeId
  setTheme: (theme: ThemeId) => void
  getThemeName: () => string
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      currentTheme: DEFAULT_THEME,
      setTheme: (theme) => set({ currentTheme: theme }),
      getThemeName: () => {
        const theme = get().currentTheme
        return THEMES[theme]?.name || THEMES[DEFAULT_THEME].name
      },
    }),
    {
      name: 'postmagiq-theme',
      // Validate persisted state on load
      onRehydrateStorage: () => (state) => {
        if (state && !isValidTheme(state.currentTheme)) {
          // Reset to default if stored theme no longer exists
          state.currentTheme = DEFAULT_THEME
        }
      },
    }
  )
)

// Re-export for convenience
export type { ThemeId } from '../config/themes'
