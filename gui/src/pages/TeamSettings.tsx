import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { UserPlus, Trash2, ChevronDown, Shield, Mail, Clock, Check } from 'lucide-react'
import { clsx } from 'clsx'
import { apiGet, apiPost, apiDelete } from '../api/client'
import { useWorkspaceStore, WorkspaceRole } from '../stores/workspaceStore'
import { usePermission } from '../hooks/usePermission'
import { useThemeClasses } from '../hooks/useThemeClasses'

interface Member {
  id: string
  user_id: string | null
  email: string
  role: WorkspaceRole
  invite_status: 'pending' | 'accepted' | 'expired'
  invited_at: string
  accepted_at: string | null
}

const ROLE_LABELS: Record<WorkspaceRole, string> = {
  owner: 'Owner',
  admin: 'Admin',
  editor: 'Editor',
  viewer: 'Viewer',
}

export default function TeamSettings() {
  const theme = useThemeClasses()
  const { currentWorkspaceId } = useWorkspaceStore()
  const canManageUsers = usePermission('workspace:users')
  const queryClient = useQueryClient()

  const [showInviteModal, setShowInviteModal] = useState(false)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState<WorkspaceRole>('editor')
  const [inviteError, setInviteError] = useState<string | null>(null)

  const { data: members, isLoading } = useQuery({
    queryKey: ['members', currentWorkspaceId],
    queryFn: () => apiGet<Member[]>(`/v1/w/${currentWorkspaceId}/members`),
    enabled: !!currentWorkspaceId,
  })

  const inviteMutation = useMutation({
    mutationFn: (data: { email: string; role: WorkspaceRole }) =>
      apiPost(`/v1/w/${currentWorkspaceId}/members`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['members', currentWorkspaceId] })
      setShowInviteModal(false)
      setInviteEmail('')
      setInviteRole('editor')
      setInviteError(null)
    },
    onError: (error: Error) => {
      setInviteError(error.message)
    },
  })

  const removeMutation = useMutation({
    mutationFn: (memberId: string) =>
      apiDelete(`/v1/w/${currentWorkspaceId}/members/${memberId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['members', currentWorkspaceId] })
    },
  })

  const handleInvite = (e: React.FormEvent) => {
    e.preventDefault()
    setInviteError(null)
    inviteMutation.mutate({ email: inviteEmail, role: inviteRole })
  }

  const handleRemove = (member: Member) => {
    if (confirm(`Remove ${member.email} from the workspace?`)) {
      removeMutation.mutate(member.id)
    }
  }

  if (!currentWorkspaceId) {
    return (
      <div className="text-center py-12 text-zinc-400">
        No workspace selected
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Team</h1>
          <p className="text-zinc-400 mt-1">Manage workspace members and permissions</p>
        </div>
        {canManageUsers && (
          <button
            onClick={() => setShowInviteModal(true)}
            className={clsx('flex items-center gap-2 px-4 py-2 text-white rounded-lg font-medium transition-colors bg-gradient-to-r', theme.gradient, theme.gradientHover)}
          >
            <UserPlus className="w-4 h-4" />
            Invite member
          </button>
        )}
      </div>

      {/* Members list */}
      <div className="bg-zinc-900 rounded-lg border border-zinc-800">
        <div className="p-4 border-b border-zinc-800">
          <h2 className="text-lg font-semibold text-white">Members</h2>
        </div>

        {isLoading ? (
          <div className="p-8 text-center text-zinc-400">Loading...</div>
        ) : !members?.length ? (
          <div className="p-8 text-center text-zinc-400">No members found</div>
        ) : (
          <div className="divide-y divide-zinc-800">
            {members.map((member) => (
              <div key={member.id} className="p-4 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 bg-zinc-800 rounded-full flex items-center justify-center">
                    <span className="text-white font-medium">
                      {member.email.charAt(0).toUpperCase()}
                    </span>
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-white font-medium">{member.email}</span>
                      {member.invite_status === 'pending' && (
                        <span className={clsx('flex items-center gap-1 px-2 py-0.5 text-xs rounded', theme.bgMuted, theme.textPrimary)}>
                          <Clock className="w-3 h-3" />
                          Pending
                        </span>
                      )}
                      {member.invite_status === 'accepted' && (
                        <span className="flex items-center gap-1 px-2 py-0.5 bg-green-500/20 text-green-400 text-xs rounded">
                          <Check className="w-3 h-3" />
                          Active
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 text-sm text-zinc-400">
                      <Shield className="w-3 h-3" />
                      {ROLE_LABELS[member.role]}
                    </div>
                  </div>
                </div>

                {canManageUsers && member.role !== 'owner' && (
                  <button
                    onClick={() => handleRemove(member)}
                    className="p-2 text-zinc-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                    title="Remove member"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Invite modal */}
      {showInviteModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-zinc-900 rounded-lg border border-zinc-800 w-full max-w-md p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Invite member</h3>

            <form onSubmit={handleInvite} className="space-y-4">
              {inviteError && (
                <div className="p-3 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400 text-sm">
                  {inviteError}
                </div>
              )}

              <div>
                <label className="block text-sm text-zinc-400 mb-1">Email</label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
                  <input
                    type="email"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    required
                    className={clsx('w-full pl-10 pr-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none', theme.borderHover)}
                    placeholder="colleague@company.com"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm text-zinc-400 mb-1">Role</label>
                <div className="relative">
                  <select
                    value={inviteRole}
                    onChange={(e) => setInviteRole(e.target.value as WorkspaceRole)}
                    className={clsx('w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none appearance-none', theme.borderHover)}
                  >
                    <option value="editor">Editor - Create and edit content</option>
                    <option value="viewer">Viewer - View only access</option>
                    <option value="admin">Admin - Manage members and settings</option>
                  </select>
                  <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500 pointer-events-none" />
                </div>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowInviteModal(false)}
                  className="flex-1 px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white rounded-lg font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={inviteMutation.isPending}
                  className={clsx('flex-1 px-4 py-2 text-white rounded-lg font-medium transition-colors bg-gradient-to-r', theme.gradient, theme.gradientHover, theme.gradientDisabled)}
                >
                  {inviteMutation.isPending ? 'Sending...' : 'Send invite'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
