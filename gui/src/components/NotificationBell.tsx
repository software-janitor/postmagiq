import { useState, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Bell, Check, CheckCheck, X, ExternalLink } from 'lucide-react'
import { clsx } from 'clsx'
import { apiGet, apiPost } from '../api/client'
import { useWorkspaceStore } from '../stores/workspaceStore'
import { formatDistanceToNow } from 'date-fns'

interface Notification {
  id: string
  notification_type: string
  title: string
  message: string
  priority: string
  resource_type: string | null
  resource_id: string | null
  actor_id: string | null
  is_read: boolean
  read_at: string | null
  is_dismissed: boolean
  dismissed_at: string | null
  created_at: string
}

interface NotificationListResponse {
  notifications: Notification[]
  unread_count: number
  total: number
}

interface UnreadCountResponse {
  count: number
}

interface MarkReadResponse {
  marked_count: number
}

// Map notification types to display-friendly labels
const notificationTypeLabels: Record<string, string> = {
  approval_requested: 'Approval Requested',
  approval_approved: 'Approved',
  approval_rejected: 'Rejected',
  approval_changes_requested: 'Changes Requested',
  approval_comment: 'New Comment',
  post_assigned: 'Post Assigned',
  post_reassigned: 'Post Reassigned',
  post_status_changed: 'Status Changed',
  post_due_soon: 'Due Soon',
  post_overdue: 'Overdue',
  member_joined: 'Member Joined',
  member_left: 'Member Left',
  invitation_received: 'Invitation Received',
  role_changed: 'Role Changed',
  system_announcement: 'Announcement',
}

// Priority colors
const priorityColors: Record<string, string> = {
  low: 'text-zinc-400',
  normal: 'text-zinc-300',
  high: 'text-amber-400',
  urgent: 'text-red-400',
}

export default function NotificationBell() {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const { currentWorkspaceId } = useWorkspaceStore()
  const queryClient = useQueryClient()

  // Fetch unread count (polling every 30 seconds)
  const { data: unreadData } = useQuery({
    queryKey: ['notifications-unread', currentWorkspaceId],
    queryFn: () =>
      apiGet<UnreadCountResponse>(`/v1/w/${currentWorkspaceId}/notifications/unread-count`),
    enabled: !!currentWorkspaceId,
    refetchInterval: 30000,
  })

  // Fetch notifications when dropdown is open
  const { data: notificationsData, isLoading } = useQuery({
    queryKey: ['notifications', currentWorkspaceId],
    queryFn: () =>
      apiGet<NotificationListResponse>(`/v1/w/${currentWorkspaceId}/notifications?limit=10`),
    enabled: !!currentWorkspaceId && isOpen,
  })

  // Mark as read mutation
  const markReadMutation = useMutation({
    mutationFn: (notificationId: string) =>
      apiPost<Notification>(`/v1/w/${currentWorkspaceId}/notifications/${notificationId}/read`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications', currentWorkspaceId] })
      queryClient.invalidateQueries({ queryKey: ['notifications-unread', currentWorkspaceId] })
    },
  })

  // Mark all as read mutation
  const markAllReadMutation = useMutation({
    mutationFn: () =>
      apiPost<MarkReadResponse>(`/v1/w/${currentWorkspaceId}/notifications/mark-read`, {
        mark_all: true,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications', currentWorkspaceId] })
      queryClient.invalidateQueries({ queryKey: ['notifications-unread', currentWorkspaceId] })
    },
  })

  // Dismiss mutation
  const dismissMutation = useMutation({
    mutationFn: (notificationId: string) =>
      apiPost<Notification>(`/v1/w/${currentWorkspaceId}/notifications/${notificationId}/dismiss`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications', currentWorkspaceId] })
      queryClient.invalidateQueries({ queryKey: ['notifications-unread', currentWorkspaceId] })
    },
  })

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const unreadCount = unreadData?.count ?? 0
  const notifications = notificationsData?.notifications ?? []

  const handleNotificationClick = (notification: Notification) => {
    if (!notification.is_read) {
      markReadMutation.mutate(notification.id)
    }

    // Navigate to resource if available
    if (notification.resource_type && notification.resource_id) {
      // Handle navigation based on resource type
      if (notification.resource_type === 'post') {
        window.location.href = `/finished?post=${notification.resource_id}`
      } else if (notification.resource_type === 'approval_request') {
        window.location.href = `/approvals?request=${notification.resource_id}`
      }
      setIsOpen(false)
    }
  }

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={clsx(
          'relative p-2 rounded-lg transition-colors',
          isOpen
            ? 'bg-amber-600/20 text-amber-400'
            : 'text-zinc-400 hover:text-white hover:bg-zinc-800'
        )}
      >
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs font-bold rounded-full flex items-center justify-center">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-96 bg-zinc-900 border border-zinc-700 rounded-lg shadow-xl z-50">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-700">
            <h3 className="text-sm font-semibold text-white">Notifications</h3>
            {unreadCount > 0 && (
              <button
                onClick={() => markAllReadMutation.mutate()}
                disabled={markAllReadMutation.isPending}
                className="text-xs text-amber-400 hover:text-amber-300 flex items-center gap-1"
              >
                <CheckCheck className="w-3 h-3" />
                Mark all read
              </button>
            )}
          </div>

          {/* Notifications list */}
          <div className="max-h-96 overflow-y-auto">
            {isLoading ? (
              <div className="px-4 py-8 text-center text-zinc-500">Loading...</div>
            ) : notifications.length === 0 ? (
              <div className="px-4 py-8 text-center text-zinc-500">No notifications</div>
            ) : (
              notifications.map((notification) => (
                <div
                  key={notification.id}
                  className={clsx(
                    'group px-4 py-3 border-b border-zinc-800 last:border-b-0 transition-colors',
                    notification.is_read ? 'bg-zinc-900' : 'bg-zinc-800/50',
                    'hover:bg-zinc-800'
                  )}
                >
                  <div className="flex items-start gap-3">
                    {/* Unread indicator */}
                    <div className="pt-1.5">
                      {!notification.is_read && (
                        <div className="w-2 h-2 rounded-full bg-amber-500" />
                      )}
                    </div>

                    {/* Content */}
                    <div
                      className="flex-1 min-w-0 cursor-pointer"
                      onClick={() => handleNotificationClick(notification)}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <span
                          className={clsx(
                            'text-xs font-medium',
                            priorityColors[notification.priority] || 'text-zinc-400'
                          )}
                        >
                          {notificationTypeLabels[notification.notification_type] ||
                            notification.notification_type}
                        </span>
                        <span className="text-xs text-zinc-500">
                          {formatDistanceToNow(new Date(notification.created_at), {
                            addSuffix: true,
                          })}
                        </span>
                      </div>
                      <p className="text-sm font-medium text-white truncate">
                        {notification.title}
                      </p>
                      <p className="text-xs text-zinc-400 line-clamp-2">{notification.message}</p>
                      {notification.resource_type && (
                        <span className="inline-flex items-center gap-1 mt-1 text-xs text-amber-400">
                          <ExternalLink className="w-3 h-3" />
                          View
                        </span>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      {!notification.is_read && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            markReadMutation.mutate(notification.id)
                          }}
                          className="p-1 text-zinc-500 hover:text-green-400 rounded"
                          title="Mark as read"
                        >
                          <Check className="w-4 h-4" />
                        </button>
                      )}
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          dismissMutation.mutate(notification.id)
                        }}
                        className="p-1 text-zinc-500 hover:text-red-400 rounded"
                        title="Dismiss"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Footer */}
          {notifications.length > 0 && (
            <div className="px-4 py-2 border-t border-zinc-700">
              <a
                href="/settings#notifications"
                className="text-xs text-amber-400 hover:text-amber-300"
              >
                Manage notification settings
              </a>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
