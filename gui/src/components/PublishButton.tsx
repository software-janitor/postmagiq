import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Linkedin,
  Twitter,
  MessageCircle,
  Send,
  Calendar,
  Loader2,
  Check,
  AlertCircle,
  ChevronDown,
} from 'lucide-react'
import { clsx } from 'clsx'
import { apiGet, apiPost } from '../api/client'
import { useWorkspaceStore } from '../stores/workspaceStore'
import { useThemeClasses } from '../hooks/useThemeClasses'

interface SocialConnection {
  id: string
  platform: 'linkedin' | 'x' | 'threads'
  platform_username: string
  platform_name: string | null
}

interface PublishButtonProps {
  postId: string
  content: string
  className?: string
}

const PLATFORM_ICONS = {
  linkedin: Linkedin,
  x: Twitter,
  threads: MessageCircle,
}

const PLATFORM_NAMES = {
  linkedin: 'LinkedIn',
  x: 'X',
  threads: 'Threads',
}

export default function PublishButton({ postId, content, className }: PublishButtonProps) {
  const theme = useThemeClasses()
  const queryClient = useQueryClient()
  const { currentWorkspaceId } = useWorkspaceStore()
  const [isOpen, setIsOpen] = useState(false)
  const [publishStatus, setPublishStatus] = useState<Record<string, 'idle' | 'loading' | 'success' | 'error'>>({})
  const [publishError, setPublishError] = useState<string | null>(null)

  const { data: connections } = useQuery({
    queryKey: ['social-connections', currentWorkspaceId],
    queryFn: () => apiGet<SocialConnection[]>(`/v1/social/w/${currentWorkspaceId}/connections`),
    enabled: !!currentWorkspaceId,
  })

  const publishMutation = useMutation({
    mutationFn: async ({ connectionId, platform }: { connectionId: string; platform: string }) => {
      return apiPost(`/v1/publish/w/${currentWorkspaceId}/${platform}/${connectionId}`, {
        post_id: postId,
        content,
      })
    },
    onMutate: ({ connectionId }) => {
      setPublishStatus((prev) => ({ ...prev, [connectionId]: 'loading' }))
      setPublishError(null)
    },
    onSuccess: (data: { success: boolean; post_url?: string; error?: string }, { connectionId }) => {
      if (data.success) {
        setPublishStatus((prev) => ({ ...prev, [connectionId]: 'success' }))
        if (data.post_url) {
          window.open(data.post_url, '_blank')
        }
      } else {
        setPublishStatus((prev) => ({ ...prev, [connectionId]: 'error' }))
        setPublishError(data.error || 'Failed to publish')
      }
    },
    onError: (error: Error, { connectionId }) => {
      setPublishStatus((prev) => ({ ...prev, [connectionId]: 'error' }))
      setPublishError(error.message)
    },
  })

  const handlePublish = (connection: SocialConnection) => {
    publishMutation.mutate({
      connectionId: connection.id,
      platform: connection.platform,
    })
  }

  const hasConnections = connections && connections.length > 0

  if (!hasConnections) {
    return (
      <a
        href="/settings"
        className={clsx(
          'inline-flex items-center gap-2 px-3 py-2 text-sm rounded-lg transition-colors',
          'text-zinc-400 hover:text-white bg-zinc-800 hover:bg-zinc-700',
          className
        )}
      >
        <Send className="w-4 h-4" />
        Connect accounts to publish
      </a>
    )
  }

  return (
    <div className={clsx('relative inline-block', className)}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={clsx(
          'inline-flex items-center gap-2 px-3 py-2 text-sm rounded-lg transition-colors',
          'text-white bg-gradient-to-r',
          theme.gradient,
          theme.gradientHover
        )}
      >
        <Send className="w-4 h-4" />
        Publish
        <ChevronDown className={clsx('w-4 h-4 transition-transform', isOpen && 'rotate-180')} />
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setIsOpen(false)} />
          <div className="absolute right-0 mt-2 w-64 bg-zinc-900 border border-zinc-700 rounded-lg shadow-xl z-20">
            <div className="p-2">
              <div className="text-xs text-zinc-500 uppercase tracking-wide px-2 py-1 mb-1">
                Publish Now
              </div>
              {connections?.map((connection) => {
                const Icon = PLATFORM_ICONS[connection.platform]
                const status = publishStatus[connection.id] || 'idle'

                return (
                  <button
                    key={connection.id}
                    onClick={() => handlePublish(connection)}
                    disabled={status === 'loading' || status === 'success'}
                    className={clsx(
                      'w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left transition-colors',
                      status === 'success'
                        ? 'bg-green-500/10 text-green-400'
                        : status === 'error'
                          ? 'bg-red-500/10 text-red-400'
                          : 'hover:bg-zinc-800 text-white'
                    )}
                  >
                    {status === 'loading' ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : status === 'success' ? (
                      <Check className="w-4 h-4 text-green-400" />
                    ) : status === 'error' ? (
                      <AlertCircle className="w-4 h-4 text-red-400" />
                    ) : (
                      <Icon className="w-4 h-4" />
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium truncate">
                        {PLATFORM_NAMES[connection.platform]}
                      </div>
                      <div className="text-xs text-zinc-500 truncate">
                        @{connection.platform_username}
                      </div>
                    </div>
                  </button>
                )
              })}
            </div>

            {publishError && (
              <div className="px-3 py-2 text-xs text-red-400 border-t border-zinc-800">
                {publishError}
              </div>
            )}

            <div className="border-t border-zinc-800 p-2">
              <a
                href="/settings"
                className="block px-3 py-2 text-sm text-zinc-400 hover:text-white hover:bg-zinc-800 rounded-lg transition-colors"
              >
                Manage connected accounts
              </a>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
