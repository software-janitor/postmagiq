import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Bell, Mail, Check } from 'lucide-react'
import { clsx } from 'clsx'
import { apiGet, apiRequest } from '../api/client'
import { useWorkspaceStore } from '../stores/workspaceStore'

interface NotificationChannel {
  id: string
  channel_type: string
  name: string
  description: string | null
  is_enabled: boolean
  created_at: string
}

interface NotificationPreference {
  id: string
  channel_id: string
  notification_type: string
  is_enabled: boolean
}

// Group notification types by category for better UX
const notificationCategories = [
  {
    name: 'Approvals',
    types: [
      { type: 'approval_requested', label: 'Approval requested from you' },
      { type: 'approval_approved', label: 'Your content was approved' },
      { type: 'approval_rejected', label: 'Your content was rejected' },
      { type: 'approval_changes_requested', label: 'Changes requested on your content' },
      { type: 'approval_comment', label: 'New comment on approval' },
    ],
  },
  {
    name: 'Assignments',
    types: [
      { type: 'post_assigned', label: 'Post assigned to you' },
      { type: 'post_reassigned', label: 'Post reassigned' },
    ],
  },
  {
    name: 'Content',
    types: [
      { type: 'post_status_changed', label: 'Post status changed' },
      { type: 'post_due_soon', label: 'Post due soon' },
      { type: 'post_overdue', label: 'Post overdue' },
    ],
  },
  {
    name: 'Team',
    types: [
      { type: 'member_joined', label: 'New member joined workspace' },
      { type: 'member_left', label: 'Member left workspace' },
      { type: 'invitation_received', label: 'Invitation received' },
      { type: 'role_changed', label: 'Your role was changed' },
    ],
  },
  {
    name: 'System',
    types: [{ type: 'system_announcement', label: 'System announcements' }],
  },
]

// Map channel types to icons
const channelIcons: Record<string, typeof Bell> = {
  in_app: Bell,
  email: Mail,
}

export default function NotificationSettings() {
  const { currentWorkspaceId } = useWorkspaceStore()
  const queryClient = useQueryClient()

  // Fetch channels
  const { data: channels, isLoading: channelsLoading } = useQuery({
    queryKey: ['notification-channels', currentWorkspaceId],
    queryFn: () =>
      apiGet<NotificationChannel[]>(`/v1/w/${currentWorkspaceId}/notifications/channels`),
    enabled: !!currentWorkspaceId,
  })

  // Fetch preferences
  const { data: preferences, isLoading: preferencesLoading } = useQuery({
    queryKey: ['notification-preferences', currentWorkspaceId],
    queryFn: () =>
      apiGet<NotificationPreference[]>(`/v1/w/${currentWorkspaceId}/notifications/preferences`),
    enabled: !!currentWorkspaceId,
  })

  // Update preference mutation
  const updatePreferenceMutation = useMutation({
    mutationFn: ({
      channelId,
      notificationType,
      isEnabled,
    }: {
      channelId: string
      notificationType: string
      isEnabled: boolean
    }) =>
      apiRequest<NotificationPreference>(
        `/v1/w/${currentWorkspaceId}/notifications/preferences/${channelId}/${notificationType}?is_enabled=${isEnabled}`,
        { method: 'PUT' }
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['notification-preferences', currentWorkspaceId],
      })
    },
  })

  const isLoading = channelsLoading || preferencesLoading

  // Helper to check if a preference is enabled
  const isEnabled = (channelId: string, notificationType: string): boolean => {
    const pref = preferences?.find(
      (p) => p.channel_id === channelId && p.notification_type === notificationType
    )
    // Default to true if no preference exists
    return pref ? pref.is_enabled : true
  }

  // Toggle preference
  const togglePreference = (channelId: string, notificationType: string) => {
    const currentValue = isEnabled(channelId, notificationType)
    updatePreferenceMutation.mutate({
      channelId,
      notificationType,
      isEnabled: !currentValue,
    })
  }

  if (isLoading) {
    return (
      <div className="bg-zinc-900 rounded-lg border border-zinc-800">
        <div className="p-4 border-b border-zinc-800 flex items-center gap-2">
          <Bell className="w-5 h-5 text-amber-400" />
          <h2 className="text-lg font-semibold text-white">Notifications</h2>
        </div>
        <div className="p-8 text-center text-zinc-500">Loading notification settings...</div>
      </div>
    )
  }

  const enabledChannels = channels?.filter((c) => c.is_enabled) ?? []

  return (
    <div id="notifications" className="bg-zinc-900 rounded-lg border border-zinc-800">
      <div className="p-4 border-b border-zinc-800 flex items-center gap-2">
        <Bell className="w-5 h-5 text-amber-400" />
        <h2 className="text-lg font-semibold text-white">Notification Preferences</h2>
      </div>
      <div className="p-4">
        <p className="text-sm text-zinc-400 mb-6">
          Choose which notifications you want to receive and how you want to receive them.
        </p>

        {/* Channel headers */}
        {enabledChannels.length > 0 && (
          <div className="grid gap-6">
            <div className="flex items-center gap-4 pb-2 border-b border-zinc-800">
              <div className="flex-1" />
              {enabledChannels.map((channel) => {
                const Icon = channelIcons[channel.channel_type] || Bell
                return (
                  <div
                    key={channel.id}
                    className="w-20 text-center flex flex-col items-center gap-1"
                  >
                    <Icon className="w-5 h-5 text-zinc-400" />
                    <span className="text-xs text-zinc-500">{channel.name}</span>
                  </div>
                )
              })}
            </div>

            {/* Categories and types */}
            {notificationCategories.map((category) => (
              <div key={category.name} className="space-y-3">
                <h3 className="text-sm font-medium text-white">{category.name}</h3>
                {category.types.map((notifType) => (
                  <div
                    key={notifType.type}
                    className="flex items-center gap-4 py-2 hover:bg-zinc-800/50 rounded-lg px-2 -mx-2 transition-colors"
                  >
                    <div className="flex-1">
                      <span className="text-sm text-zinc-300">{notifType.label}</span>
                    </div>
                    {enabledChannels.map((channel) => (
                      <div key={channel.id} className="w-20 flex justify-center">
                        <button
                          onClick={() => togglePreference(channel.id, notifType.type)}
                          disabled={updatePreferenceMutation.isPending}
                          className={clsx(
                            'w-8 h-8 rounded-lg flex items-center justify-center transition-colors',
                            isEnabled(channel.id, notifType.type)
                              ? 'bg-amber-600/20 text-amber-400 hover:bg-amber-600/30'
                              : 'bg-zinc-800 text-zinc-600 hover:bg-zinc-700'
                          )}
                        >
                          {isEnabled(channel.id, notifType.type) && <Check className="w-4 h-4" />}
                        </button>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}

        {enabledChannels.length === 0 && (
          <div className="text-center text-zinc-500 py-8">
            No notification channels available.
          </div>
        )}
      </div>
    </div>
  )
}
