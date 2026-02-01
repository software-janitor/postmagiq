import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Play,
  PenTool,
  History,
  Settings,
  GitBranch,
  UserPlus,
  Mic,
  FileCheck,
  Wand2,
  Target,
  ChevronDown,
  Plus,
  Loader2,
  Layers,
  UsersRound,
  LogOut,
  CheckSquare,
  MessageCircle,
  BarChart3,
} from 'lucide-react'
import { clsx } from 'clsx'
import { useQuery } from '@tanstack/react-query'
import { fetchExistingStrategy } from '../../api/onboarding'
import ThemeSwitcher from '../ThemeSwitcher'
import { useAuthStore } from '../../stores/authStore'
import { useWorkspaceStore } from '../../stores/workspaceStore'
import { useThemeClasses } from '../../hooks/useThemeClasses'
import { useEffectiveFlags, FeatureFlags } from '../../stores/flagsStore'

import { usePermission, Scope } from '../../hooks/usePermission'

interface NavItem {
  path: string
  icon: React.ComponentType<{ className?: string }>
  label: string
  scope?: Scope
  flag?: keyof FeatureFlags
}

const navItems: NavItem[] = [
  { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/strategies', icon: Layers, label: 'Strategies' },
  { path: '/strategy', icon: Target, label: 'Current Strategy' },
  { path: '/onboarding', icon: UserPlus, label: 'New Strategy' },
  { path: '/voice', icon: Mic, label: 'Voice Learning' },
  { path: '/voice-profiles', icon: MessageCircle, label: 'Voice Profiles' },
  { path: '/story', icon: PenTool, label: 'New Story' },
  { path: '/finished', icon: FileCheck, label: 'Finished Posts' },
  { path: '/workflow', icon: Play, label: 'Live Workflow', flag: 'show_live_workflow' },
  { path: '/runs', icon: History, label: 'Run History', flag: 'show_internal_workflow' },
  { path: '/editor', icon: GitBranch, label: 'State Editor', flag: 'show_state_editor' },
  { path: '/approvals', icon: CheckSquare, label: 'Approvals', scope: 'content:read' as const, flag: 'show_approvals' },
  { path: '/team', icon: UsersRound, label: 'Team', scope: 'team:read' as const, flag: 'show_teams' },
  { path: '/settings', icon: Settings, label: 'Settings', scope: 'workflow:execute' as const },
]

function ScopedNavLink({ item }: { item: NavItem }) {
  const hasPermission = usePermission(item.scope || 'content:read')
  const flags = useEffectiveFlags()
  const theme = useThemeClasses()

  // If item has a scope requirement and user doesn't have it, don't render
  if (item.scope && !hasPermission) {
    return null
  }

  // If item has a feature flag requirement and it's disabled, don't render
  if (item.flag && !flags[item.flag]) {
    return null
  }

  const Icon = item.icon

  return (
    <NavLink
      to={item.path}
      className={({ isActive }) =>
        clsx(
          'flex items-center gap-3 px-3 py-2 rounded-lg transition-colors',
          isActive
            ? `bg-gradient-to-r ${theme.gradient} text-white shadow-lg ${theme.shadow}`
            : `text-zinc-400 ${theme.bgHover} hover:${theme.textPrimary}`
        )
      }
    >
      <Icon className="w-5 h-5" />
      {item.label}
    </NavLink>
  )
}

export default function Sidebar() {
  const { logout, user } = useAuthStore()
  const theme = useThemeClasses()

  // Fetch current strategy for the strategy indicator
  const workspaceId = useWorkspaceStore((s) => s.currentWorkspaceId)
  const { data: strategy, isLoading } = useQuery({
    queryKey: ['strategy', workspaceId],
    queryFn: () => fetchExistingStrategy(),
    enabled: !!workspaceId,
  })

  const strategyName = strategy?.goal?.signature_thesis?.split('.')[0] || 'No Strategy'
  const hasStrategy = strategy?.exists && strategy?.goal

  const handleLogout = async () => {
    await logout()
    window.location.href = '/auth/login'
  }

  return (
    <aside className={`w-64 bg-black border-r ${theme.border} flex flex-col`}>
      <div className={`p-4 border-b ${theme.border}`}>
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <Wand2 className={`w-6 h-6 ${theme.iconPrimary}`} />
          <span className={`bg-gradient-to-r ${theme.gradientText} bg-clip-text text-transparent`}>Postmagiq</span>
        </h1>
        <p className={`text-xs ${theme.textMuted} mt-1`}>AI Content Platform</p>
      </div>

      {/* Strategy Indicator */}
      <div className={`px-4 py-3 border-b ${theme.border}`}>
        <div className="text-xs text-zinc-500 uppercase tracking-wide mb-2">Active Strategy</div>
        {isLoading ? (
          <div className="flex items-center gap-2 text-zinc-400 text-sm">
            <Loader2 className="w-4 h-4 animate-spin" />
            Loading...
          </div>
        ) : !hasStrategy ? (
          <NavLink
            to="/onboarding"
            className={`flex items-center gap-2 px-3 py-2 ${theme.bgMuted} ${theme.textPrimary} rounded-lg text-sm hover:opacity-80`}
          >
            <Plus className="w-4 h-4" />
            Create Strategy
          </NavLink>
        ) : (
          <NavLink
            to="/strategies"
            className={`flex items-center justify-between px-3 py-2 bg-zinc-900 border border-zinc-700 rounded-lg text-sm text-white ${theme.borderHover} transition-colors`}
          >
            <div className="flex items-center gap-2 min-w-0">
              <Target className={`w-4 h-4 ${theme.iconPrimary} flex-shrink-0`} />
              <span className="truncate">{strategyName}</span>
            </div>
            <ChevronDown className="w-4 h-4 text-zinc-400 flex-shrink-0" />
          </NavLink>
        )}
      </div>

      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => (
          <ScopedNavLink key={item.path} item={item} />
        ))}

        {/* Admin Section - Owner Only */}
        {user?.role === 'owner' && (
          <>
            <div className="mt-4 mb-2 px-3 text-xs text-zinc-500 uppercase tracking-wide">
              Admin
            </div>
            <NavLink
              to="/admin/analytics"
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 px-3 py-2 rounded-lg transition-colors',
                  isActive
                    ? `bg-gradient-to-r ${theme.gradient} text-white shadow-lg ${theme.shadow}`
                    : `text-zinc-400 ${theme.bgHover} hover:${theme.textPrimary}`
                )
              }
            >
              <BarChart3 className="w-5 h-5" />
              Analytics
            </NavLink>
          </>
        )}
      </nav>

      {/* Theme Switcher */}
      <div className={`px-4 py-3 border-t ${theme.border}`}>
        <ThemeSwitcher />
      </div>

      {/* User & Logout */}
      <div className={`p-4 border-t ${theme.border}`}>
        <div className="flex items-center justify-between">
          <div className="min-w-0">
            <div className="text-sm text-white truncate">{user?.full_name || user?.email}</div>
            <div className="text-xs text-zinc-500">Postmagiq v1.0</div>
          </div>
          <button
            onClick={handleLogout}
            className="p-2 text-zinc-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
            title="Sign out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  )
}
