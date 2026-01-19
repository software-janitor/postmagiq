import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Settings, Plus, Trash2, GripVertical } from 'lucide-react'
import { useState } from 'react'
import { clsx } from 'clsx'
import { apiGet, apiPost, apiPatch, apiDelete } from '../api/client'
import { useThemeClasses } from '../hooks/useThemeClasses'
import { useWorkspaceStore } from '../stores/workspaceStore'
import ApprovalQueue from '../components/ApprovalQueue'

interface ApprovalStage {
  id: string
  workspace_id: string
  name: string
  description: string | null
  order: number
  is_required: boolean
  is_active: boolean
  auto_approve_role: string | null
  created_at: string
}

interface CreateStageRequest {
  name: string
  description?: string
  order?: number
  is_required?: boolean
}

export default function Approvals() {
  const theme = useThemeClasses()
  const { currentWorkspaceId } = useWorkspaceStore()
  const queryClient = useQueryClient()
  const [showSettings, setShowSettings] = useState(false)
  const [newStageName, setNewStageName] = useState('')
  const [newStageDescription, setNewStageDescription] = useState('')

  const { data: stages, isLoading: stagesLoading } = useQuery({
    queryKey: ['approval-stages', currentWorkspaceId],
    queryFn: () =>
      apiGet<ApprovalStage[]>(`/v1/w/${currentWorkspaceId}/approvals/stages?include_inactive=true`),
    enabled: !!currentWorkspaceId,
  })

  const createStageMutation = useMutation({
    mutationFn: (data: CreateStageRequest) =>
      apiPost<ApprovalStage>(`/v1/w/${currentWorkspaceId}/approvals/stages`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approval-stages'] })
      setNewStageName('')
      setNewStageDescription('')
    },
  })

  const updateStageMutation = useMutation({
    mutationFn: ({ stageId, data }: { stageId: string; data: Partial<ApprovalStage> }) =>
      apiPatch<ApprovalStage>(`/v1/w/${currentWorkspaceId}/approvals/stages/${stageId}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approval-stages'] })
    },
  })

  const deleteStageMutation = useMutation({
    mutationFn: (stageId: string) =>
      apiDelete(`/v1/w/${currentWorkspaceId}/approvals/stages/${stageId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approval-stages'] })
    },
  })

  const handleCreateStage = () => {
    if (newStageName.trim()) {
      const maxOrder = stages?.reduce((max, s) => Math.max(max, s.order), 0) || 0
      createStageMutation.mutate({
        name: newStageName.trim(),
        description: newStageDescription.trim() || undefined,
        order: maxOrder + 1,
        is_required: true,
      })
    }
  }

  const handleToggleActive = (stage: ApprovalStage) => {
    updateStageMutation.mutate({
      stageId: stage.id,
      data: { is_active: !stage.is_active },
    })
  }

  const activeStages = stages?.filter((s) => s.is_active).sort((a, b) => a.order - b.order) || []
  const inactiveStages = stages?.filter((s) => !s.is_active) || []

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Approvals</h1>
        <button
          onClick={() => setShowSettings(!showSettings)}
          className="flex items-center gap-2 px-3 py-2 bg-zinc-800 hover:bg-zinc-700 text-white rounded-lg transition-colors"
        >
          <Settings className="w-4 h-4" />
          {showSettings ? 'Hide Settings' : 'Settings'}
        </button>
      </div>

      {/* Settings Panel */}
      {showSettings && (
        <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-4 space-y-4">
          <h2 className="text-lg font-semibold text-white">Approval Stages</h2>
          <p className="text-sm text-zinc-400">
            Configure the stages content must pass through before publication.
          </p>

          {/* Active Stages */}
          <div className="space-y-2">
            <h3 className="text-sm font-medium text-zinc-300">Active Stages</h3>
            {stagesLoading ? (
              <div className="text-zinc-400 text-sm">Loading stages...</div>
            ) : activeStages.length > 0 ? (
              <div className="space-y-2">
                {activeStages.map((stage) => (
                  <div
                    key={stage.id}
                    className="flex items-center justify-between p-3 bg-zinc-800/50 rounded-lg border border-zinc-700"
                  >
                    <div className="flex items-center gap-3">
                      <GripVertical className="w-4 h-4 text-zinc-500" />
                      <div>
                        <div className="font-medium text-white">{stage.name}</div>
                        {stage.description && (
                          <div className="text-sm text-zinc-400">{stage.description}</div>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-zinc-500">Order: {stage.order}</span>
                      {stage.is_required && (
                        <span className={clsx('px-2 py-0.5 text-xs rounded', theme.bgMuted, theme.textPrimary)}>
                          Required
                        </span>
                      )}
                      <button
                        onClick={() => handleToggleActive(stage)}
                        className="px-2 py-1 text-xs text-zinc-400 hover:text-red-400 transition-colors"
                      >
                        Disable
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-zinc-500 text-sm py-2">
                No active stages. Add a stage to start the approval workflow.
              </div>
            )}
          </div>

          {/* Inactive Stages */}
          {inactiveStages.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-medium text-zinc-300">Inactive Stages</h3>
              <div className="space-y-2">
                {inactiveStages.map((stage) => (
                  <div
                    key={stage.id}
                    className="flex items-center justify-between p-3 bg-zinc-800/30 rounded-lg border border-zinc-700/50 opacity-60"
                  >
                    <div className="flex items-center gap-3">
                      <div>
                        <div className="font-medium text-white">{stage.name}</div>
                        {stage.description && (
                          <div className="text-sm text-zinc-400">{stage.description}</div>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleToggleActive(stage)}
                        className="px-2 py-1 text-xs text-zinc-400 hover:text-green-400 transition-colors"
                      >
                        Enable
                      </button>
                      <button
                        onClick={() => deleteStageMutation.mutate(stage.id)}
                        className="p-1 text-zinc-400 hover:text-red-400 transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Add New Stage */}
          <div className="pt-4 border-t border-zinc-700 space-y-3">
            <h3 className="text-sm font-medium text-zinc-300">Add New Stage</h3>
            <div className="flex gap-2">
              <input
                type="text"
                value={newStageName}
                onChange={(e) => setNewStageName(e.target.value)}
                placeholder="Stage name"
                className={clsx('flex-1 px-3 py-2 bg-zinc-800 border border-zinc-600 rounded-lg text-white placeholder:text-zinc-500 focus:outline-none', theme.borderHover)}
              />
              <input
                type="text"
                value={newStageDescription}
                onChange={(e) => setNewStageDescription(e.target.value)}
                placeholder="Description (optional)"
                className={clsx('flex-1 px-3 py-2 bg-zinc-800 border border-zinc-600 rounded-lg text-white placeholder:text-zinc-500 focus:outline-none', theme.borderHover)}
              />
              <button
                onClick={handleCreateStage}
                disabled={!newStageName.trim() || createStageMutation.isPending}
                className={clsx('flex items-center gap-1 px-4 py-2 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed bg-gradient-to-r', theme.gradient, theme.gradientHover)}
              >
                <Plus className="w-4 h-4" />
                Add
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Approval Queue */}
      <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-4">
        <ApprovalQueue />
      </div>
    </div>
  )
}
