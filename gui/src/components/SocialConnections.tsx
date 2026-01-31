import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Linkedin, Twitter, MessageCircle, Link2, Unlink, Loader2, ExternalLink } from 'lucide-react'
import { clsx } from 'clsx'
import { apiGet, apiDelete } from '../api/client'
import { useWorkspaceStore } from '../stores/workspaceStore'
import { useThemeClasses } from '../hooks/useThemeClasses'

interface SocialConnection {
  id: string
  platform: 'linkedin' | 'x' | 'threads'
  platform_username: string
  platform_name: string | null
  expires_at: string | null
  created_at: string
}

const PLATFORM_CONFIG = {
  linkedin: {
    name: 'LinkedIn',
    icon: Linkedin,
    color: 'text-blue-500',
    bgColor: 'bg-blue-500/10',
    borderColor: 'border-blue-500/30',
  },
  x: {
    name: 'X (Twitter)',
    icon: Twitter,
    color: 'text-zinc-300',
    bgColor: 'bg-zinc-500/10',
    borderColor: 'border-zinc-500/30',
  },
  threads: {
    name: 'Threads',
    icon: MessageCircle,
    color: 'text-purple-400',
    bgColor: 'bg-purple-500/10',
    borderColor: 'border-purple-500/30',
  },
}

export default function SocialConnections() {
  const theme = useThemeClasses()
  const queryClient = useQueryClient()
  const { currentWorkspaceId } = useWorkspaceStore()

  const { data: connections, isLoading } = useQuery({
    queryKey: ['social-connections', currentWorkspaceId],
    queryFn: () => apiGet<SocialConnection[]>(`/v1/social/w/${currentWorkspaceId}/connections`),
    enabled: !!currentWorkspaceId,
  })

  const disconnectMutation = useMutation({
    mutationFn: (connectionId: string) =>
      apiDelete(`/v1/social/w/${currentWorkspaceId}/connections/${connectionId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['social-connections', currentWorkspaceId] })
    },
  })

  const handleConnect = (platform: 'linkedin' | 'x' | 'threads') => {
    // Redirect to OAuth flow
    window.location.href = `/api/v1/social/w/${currentWorkspaceId}/connect/${platform}`
  }

  const handleDisconnect = (connectionId: string) => {
    if (confirm('Are you sure you want to disconnect this account?')) {
      disconnectMutation.mutate(connectionId)
    }
  }

  const getConnectionForPlatform = (platform: 'linkedin' | 'x' | 'threads') => {
    return connections?.find((c) => c.platform === platform)
  }

  const isExpired = (expiresAt: string | null) => {
    if (!expiresAt) return false
    return new Date(expiresAt) < new Date()
  }

  return (
    <div className="bg-zinc-900 rounded-lg border border-zinc-800">
      <div className="p-4 border-b border-zinc-800 flex items-center gap-2">
        <Link2 className={clsx('w-5 h-5', theme.iconPrimary)} />
        <h2 className="text-lg font-semibold text-white">Connected Accounts</h2>
      </div>
      <div className="p-4">
        <p className="text-sm text-zinc-400 mb-4">
          Connect your social media accounts to publish directly from Postmagiq.
        </p>

        {isLoading ? (
          <div className="flex items-center gap-2 text-zinc-400">
            <Loader2 className="w-4 h-4 animate-spin" />
            Loading connections...
          </div>
        ) : (
          <div className="space-y-3">
            {(['linkedin', 'x', 'threads'] as const).map((platform) => {
              const config = PLATFORM_CONFIG[platform]
              const connection = getConnectionForPlatform(platform)
              const Icon = config.icon
              const expired = connection && isExpired(connection.expires_at)

              return (
                <div
                  key={platform}
                  className={clsx(
                    'flex items-center justify-between p-3 rounded-lg border',
                    connection ? config.borderColor : 'border-zinc-700',
                    connection ? config.bgColor : 'bg-zinc-800/50'
                  )}
                >
                  <div className="flex items-center gap-3">
                    <Icon className={clsx('w-5 h-5', connection ? config.color : 'text-zinc-500')} />
                    <div>
                      <div className="text-sm font-medium text-white">{config.name}</div>
                      {connection ? (
                        <div className="text-xs text-zinc-400">
                          @{connection.platform_username}
                          {expired && (
                            <span className="ml-2 text-amber-400">(expired - reconnect)</span>
                          )}
                        </div>
                      ) : (
                        <div className="text-xs text-zinc-500">Not connected</div>
                      )}
                    </div>
                  </div>

                  {connection ? (
                    <button
                      onClick={() => handleDisconnect(connection.id)}
                      disabled={disconnectMutation.isPending}
                      className="flex items-center gap-1 px-3 py-1.5 text-sm text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-lg transition-colors"
                    >
                      {disconnectMutation.isPending ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Unlink className="w-4 h-4" />
                      )}
                      Disconnect
                    </button>
                  ) : (
                    <button
                      onClick={() => handleConnect(platform)}
                      className={clsx(
                        'flex items-center gap-1 px-3 py-1.5 text-sm rounded-lg transition-colors',
                        'text-white bg-gradient-to-r',
                        theme.gradient,
                        theme.gradientHover
                      )}
                    >
                      <ExternalLink className="w-4 h-4" />
                      Connect
                    </button>
                  )}
                </div>
              )
            })}
          </div>
        )}

        <p className="mt-4 text-xs text-zinc-500">
          Your credentials are stored securely and only used to publish content you approve.
        </p>
      </div>
    </div>
  )
}
