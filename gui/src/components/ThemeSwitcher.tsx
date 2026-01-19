import { useThemeStore } from '../stores/themeStore'
import { THEMES, ThemeId } from '../config/themes'
import { Palette } from 'lucide-react'
import { useState } from 'react'

// Generate preview gradient classes from theme config
function getPreviewClasses(themeId: ThemeId) {
  const config = THEMES[themeId]
  return {
    from: `from-${config.primary}-500`,
    to: `to-${config.secondary}-500`,
  }
}

export default function ThemeSwitcher() {
  const { currentTheme, setTheme } = useThemeStore()
  const [isOpen, setIsOpen] = useState(false)
  const currentPreview = getPreviewClasses(currentTheme)

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 transition-colors text-sm"
      >
        <div className={`w-4 h-4 rounded-full bg-gradient-to-r ${currentPreview.from} ${currentPreview.to}`} />
        <span className="text-zinc-300">{THEMES[currentTheme].name}</span>
        <Palette className="w-4 h-4 text-zinc-400" />
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />
          <div className="absolute bottom-full left-0 mb-2 bg-zinc-900 border border-zinc-700 rounded-lg shadow-xl z-50 p-2 min-w-[180px]">
            <div className="text-xs text-zinc-500 uppercase tracking-wide px-2 py-1 mb-1">Color Theme</div>
            {(Object.keys(THEMES) as ThemeId[]).map((themeId) => {
              const theme = THEMES[themeId]
              const preview = getPreviewClasses(themeId)
              const isActive = currentTheme === themeId
              return (
                <button
                  key={themeId}
                  onClick={() => {
                    setTheme(themeId)
                    setIsOpen(false)
                  }}
                  className={`w-full flex items-center gap-3 px-2 py-2 rounded-lg transition-colors ${
                    isActive ? 'bg-zinc-700' : 'hover:bg-zinc-800'
                  }`}
                >
                  <div className={`w-5 h-5 rounded-full bg-gradient-to-r ${preview.from} ${preview.to}`} />
                  <span className={`text-sm ${isActive ? 'text-white' : 'text-zinc-400'}`}>
                    {theme.name}
                  </span>
                </button>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}
