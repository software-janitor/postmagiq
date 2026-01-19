import { useQuery } from '@tanstack/react-query'
import { useWorkflowStore } from '../../stores/workflowStore'
import { useWorkspaceStore } from '../../stores/workspaceStore'
import { useAuthStore } from '../../stores/authStore'
import { apiGet } from '../../api/client'
import { Circle, Coins, Eye, EyeOff } from 'lucide-react'
import { clsx } from 'clsx'
import NotificationBell from '../NotificationBell'

interface UsageSummary {
  posts: { used: number; limit: number }
  subscription: { tier_name: string }
}

export default function Header() {
  const { running, currentRunId, currentState } = useWorkflowStore()
  const { currentWorkspaceId } = useWorkspaceStore()
  const { user, viewAsUser, toggleViewAsUser } = useAuthStore()

  const isOwner = user?.role === 'owner'

  // Fetch credits/usage for display
  const { data: usage } = useQuery({
    queryKey: ['usage-header', currentWorkspaceId],
    queryFn: () => apiGet<UsageSummary>(`/v1/w/${currentWorkspaceId}/usage`),
    enabled: !!currentWorkspaceId,
    refetchInterval: 60000, // Refresh every minute
    staleTime: 30000,
  })

  // Calculate credits (posts * 100 credits each, roughly)
  const creditsUsed = (usage?.posts?.used ?? 0) * 100
  const creditsLimit = (usage?.posts?.limit ?? 5) * 100

  return (
    <header className="h-14 bg-zinc-900 border-b border-amber-900/30 flex items-center justify-between px-6">
      <div className="flex items-center gap-4">
        {running && (
          <div className="flex items-center gap-2 text-sm">
            <Circle className={clsx(
              'w-3 h-3 fill-current',
              running ? 'text-amber-500 animate-pulse' : 'text-zinc-500'
            )} />
            <span className="text-zinc-300">
              Running: <span className="text-white font-medium">{currentRunId}</span>
            </span>
            {currentState && (
              <span className="text-zinc-400">
                ({currentState})
              </span>
            )}
          </div>
        )}
      </div>

      <div className="flex items-center gap-4 text-sm text-zinc-400">
        {/* View As User Toggle (Owner Only) */}
        {isOwner && (
          <button
            onClick={toggleViewAsUser}
            className={clsx(
              'flex items-center gap-1.5 px-2 py-1 rounded-md border transition-colors',
              viewAsUser
                ? 'bg-amber-900/30 border-amber-600 text-amber-400'
                : 'bg-zinc-800 border-zinc-700 text-zinc-400 hover:text-zinc-300'
            )}
            title={viewAsUser ? 'Viewing as regular user' : 'View as regular user'}
          >
            {viewAsUser ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            <span className="text-xs">{viewAsUser ? 'User View' : 'Owner'}</span>
          </button>
        )}
        {/* Credits Display */}
        {currentWorkspaceId && usage && (
          <div className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-zinc-800 border border-zinc-700">
            <Coins className="w-4 h-4 text-amber-400" />
            <span className={clsx(
              'font-medium',
              creditsUsed >= creditsLimit ? 'text-red-400' : 'text-amber-400'
            )}>
              {creditsLimit - creditsUsed}
            </span>
            <span className="text-zinc-500">credits</span>
          </div>
        )}
        <NotificationBell />
        <span>API: <span className="text-amber-400">Connected</span></span>
      </div>
    </header>
  )
}
