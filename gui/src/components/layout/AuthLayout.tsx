import { ReactNode } from 'react'
import { Wand2 } from 'lucide-react'
import { useThemeClasses } from '../../hooks/useThemeClasses'

interface AuthLayoutProps {
  children: ReactNode
}

export default function AuthLayout({ children }: AuthLayoutProps) {
  const theme = useThemeClasses()

  return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center p-4 relative overflow-hidden">
      {/* Magical background glow */}
      <div className={`absolute top-1/4 left-1/4 w-96 h-96 ${theme.bgGlow1} rounded-full blur-3xl`} />
      <div className={`absolute bottom-1/4 right-1/4 w-96 h-96 ${theme.bgGlow2} rounded-full blur-3xl`} />

      <div className="w-full max-w-md relative z-10">
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 mb-2">
            <Wand2 className={`w-8 h-8 ${theme.iconPrimary}`} />
            <h1 className={`text-3xl font-bold bg-gradient-to-r ${theme.gradientText} bg-clip-text text-transparent`}>
              Postmagiq
            </h1>
          </div>
          <p className={theme.textMuted}>AI Content Platform</p>
        </div>
        <div className={`bg-zinc-900/80 backdrop-blur rounded-lg border ${theme.border} p-6 shadow-xl ${theme.shadow}`}>
          {children}
        </div>
      </div>
    </div>
  )
}
