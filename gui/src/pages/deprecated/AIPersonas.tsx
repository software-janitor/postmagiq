import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Bot, PenTool, Search, Shuffle, Cpu, Loader2, Save, RotateCcw, Plus, Trash2 } from 'lucide-react'
import { clsx } from 'clsx'
import { useThemeClasses } from '../hooks/useThemeClasses'
import { apiGet, apiPut, apiPost, apiDelete } from '../api/client'
import AIAssistant from '../components/AIAssistant'

interface Persona {
  id: string
  name: string
  description: string
  filename: string
  exists: boolean
  is_default: boolean
}

interface PersonaDetail {
  id: string
  name: string
  description: string
  content: string
}

const PERSONA_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  writer: PenTool,
  auditor: Search,
  synthesizer: Shuffle,
  orchestrator: Cpu,
}

export default function AIPersonas() {
  const theme = useThemeClasses()
  const [selectedPersona, setSelectedPersona] = useState<string | null>(null)
  const [editedContent, setEditedContent] = useState<string>('')
  const [hasChanges, setHasChanges] = useState(false)
  const [showNewModal, setShowNewModal] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState<string | null>(null)
  const [newPersona, setNewPersona] = useState({ id: '', name: '', description: '' })
  const queryClient = useQueryClient()

  const { data: personasData, isLoading } = useQuery({
    queryKey: ['ai-personas'],
    queryFn: () => apiGet<{ personas: Persona[] }>('/workflow-personas'),
  })

  const { data: selectedPersonaData, isLoading: isLoadingDetail } = useQuery({
    queryKey: ['ai-persona', selectedPersona],
    queryFn: () => apiGet<PersonaDetail>(`/workflow-personas/${selectedPersona}`),
    enabled: !!selectedPersona,
  })

  // When selectedPersonaData changes, update editedContent
  if (selectedPersonaData?.content && !hasChanges && editedContent !== selectedPersonaData.content) {
    setEditedContent(selectedPersonaData.content)
  }

  const updateMutation = useMutation({
    mutationFn: (content: string) =>
      apiPut(`/workflow-personas/${selectedPersona}`, { content }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-persona', selectedPersona] })
      setHasChanges(false)
    },
  })

  const createMutation = useMutation({
    mutationFn: (data: { id: string; name: string; description: string }) =>
      apiPost('/workflow-personas', data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['ai-personas'] })
      setShowNewModal(false)
      setNewPersona({ id: '', name: '', description: '' })
      setSelectedPersona(variables.id)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (personaId: string) => apiDelete(`/workflow-personas/${personaId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-personas'] })
      setShowDeleteModal(null)
      if (selectedPersona === showDeleteModal) {
        setSelectedPersona(null)
      }
    },
  })

  const handleSave = () => {
    if (selectedPersona && editedContent) {
      updateMutation.mutate(editedContent)
    }
  }

  const handleReset = () => {
    if (selectedPersonaData?.content) {
      setEditedContent(selectedPersonaData.content)
      setHasChanges(false)
    }
  }

  const personas = personasData?.personas || []

  return (
    <div className="h-full flex gap-6">
      {/* Persona List */}
      <div className="w-72 flex-shrink-0 bg-zinc-900 rounded-lg border border-zinc-800 overflow-hidden">
        <div className="p-4 border-b border-zinc-800">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Bot className={clsx('w-5 h-5', theme.iconPrimary)} />
              AI Personas
            </h2>
            <button
              onClick={() => setShowNewModal(true)}
              className={clsx('p-2 text-white rounded-lg transition-colors bg-gradient-to-r', theme.gradient, theme.gradientHover)}
              title="Add New Persona"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>
          <p className="text-sm text-zinc-400 mt-1">
            Workflow agent configurations
          </p>
        </div>

        <div className="p-2">
          {isLoading ? (
            <div className="p-4 text-center text-zinc-400">
              <Loader2 className="w-5 h-5 animate-spin mx-auto" />
            </div>
          ) : (
            <div className="space-y-1">
              {personas.map((persona) => {
                const Icon = PERSONA_ICONS[persona.id] || Bot
                return (
                  <div
                    key={persona.id}
                    className={clsx(
                      'w-full p-3 rounded-lg text-left transition-colors relative group',
                      selectedPersona === persona.id
                        ? clsx(theme.bgMuted, 'border', theme.border)
                        : 'hover:bg-zinc-800 border border-transparent'
                    )}
                  >
                    <button
                      onClick={() => {
                        setSelectedPersona(persona.id)
                        setHasChanges(false)
                      }}
                      className="w-full text-left"
                    >
                      <div className="flex items-center gap-3">
                        <div className={clsx(
                          'w-10 h-10 rounded-lg flex items-center justify-center',
                          selectedPersona === persona.id
                            ? clsx('text-white bg-gradient-to-r', theme.gradient)
                            : 'bg-zinc-800 text-zinc-400'
                        )}>
                          <Icon className="w-5 h-5" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-white font-medium">{persona.name}</span>
                            {!persona.is_default && (
                              <span className="text-xs px-1.5 py-0.5 bg-purple-600/20 text-purple-400 rounded">
                                Custom
                              </span>
                            )}
                          </div>
                          <div className="text-xs text-zinc-500 truncate">{persona.description}</div>
                        </div>
                      </div>
                    </button>
                    {!persona.is_default && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          setShowDeleteModal(persona.id)
                        }}
                        className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 text-zinc-500 hover:text-red-400 hover:bg-red-600/10 rounded opacity-0 group-hover:opacity-100 transition-opacity"
                        title="Delete Persona"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>

      {/* Persona Editor */}
      <div className="flex-1 flex flex-col bg-zinc-900 rounded-lg border border-zinc-800 overflow-hidden">
        {selectedPersona ? (
          <>
            {/* Header */}
            <div className="p-4 border-b border-zinc-800 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-white">
                  {selectedPersonaData?.name || 'Loading...'}
                </h3>
                <p className="text-sm text-zinc-400">
                  {selectedPersonaData?.description}
                </p>
              </div>
              <div className="flex gap-2">
                {hasChanges && (
                  <button
                    onClick={handleReset}
                    className="px-3 py-1.5 text-sm text-zinc-400 hover:text-white hover:bg-zinc-800 rounded-lg flex items-center gap-1"
                  >
                    <RotateCcw className="w-4 h-4" />
                    Reset
                  </button>
                )}
                <button
                  onClick={handleSave}
                  disabled={!hasChanges || updateMutation.isPending}
                  className={clsx(
                    'px-3 py-1.5 text-sm rounded-lg flex items-center gap-1',
                    hasChanges
                      ? clsx('text-white bg-gradient-to-r', theme.gradient, theme.gradientHover)
                      : 'bg-zinc-800 text-zinc-500 cursor-not-allowed'
                  )}
                >
                  {updateMutation.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Save className="w-4 h-4" />
                  )}
                  Save
                </button>
              </div>
            </div>

            {/* Editor */}
            <div className="flex-1 p-4 overflow-hidden">
              {isLoadingDetail ? (
                <div className="h-full flex items-center justify-center text-zinc-400">
                  <Loader2 className="w-6 h-6 animate-spin" />
                </div>
              ) : (
                <textarea
                  value={editedContent}
                  onChange={(e) => {
                    setEditedContent(e.target.value)
                    setHasChanges(e.target.value !== selectedPersonaData?.content)
                  }}
                  className={clsx('w-full h-full bg-zinc-800 border border-zinc-700 rounded-lg p-4 text-white text-sm font-mono resize-none focus:outline-none', theme.borderHover)}
                  placeholder="Enter persona instructions..."
                />
              )}
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-zinc-500">
            <div className="text-center">
              <Bot className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>Select a persona to view and edit</p>
            </div>
          </div>
        )}
      </div>

      {/* New Persona Modal */}
      {showNewModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-6 w-96">
            <h3 className="text-lg font-semibold text-white mb-4">Create New Persona</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-zinc-400 mb-2">ID (lowercase)</label>
                <input
                  type="text"
                  value={newPersona.id}
                  onChange={(e) => setNewPersona({ ...newPersona, id: e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '') })}
                  placeholder="e.g., researcher"
                  className={clsx('w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none', theme.borderHover)}
                />
              </div>
              <div>
                <label className="block text-sm text-zinc-400 mb-2">Name</label>
                <input
                  type="text"
                  value={newPersona.name}
                  onChange={(e) => setNewPersona({ ...newPersona, name: e.target.value })}
                  placeholder="e.g., Researcher"
                  className={clsx('w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none', theme.borderHover)}
                />
              </div>
              <div>
                <label className="block text-sm text-zinc-400 mb-2">Description</label>
                <input
                  type="text"
                  value={newPersona.description}
                  onChange={(e) => setNewPersona({ ...newPersona, description: e.target.value })}
                  placeholder="e.g., Gathers information and context"
                  className={clsx('w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none', theme.borderHover)}
                />
              </div>
              {createMutation.isError && (
                <p className="text-red-400 text-sm">Failed to create persona</p>
              )}
              <div className="flex gap-3 pt-2">
                <button
                  onClick={() => {
                    setShowNewModal(false)
                    setNewPersona({ id: '', name: '', description: '' })
                  }}
                  className="flex-1 px-4 py-2 bg-zinc-800 text-white rounded-lg hover:bg-zinc-700"
                >
                  Cancel
                </button>
                <button
                  onClick={() => createMutation.mutate(newPersona)}
                  disabled={!newPersona.id || !newPersona.name || createMutation.isPending}
                  className={clsx('flex-1 px-4 py-2 text-white rounded-lg disabled:opacity-50 flex items-center justify-center gap-2 bg-gradient-to-r', theme.gradient, theme.gradientHover)}
                >
                  {createMutation.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Plus className="w-4 h-4" />
                  )}
                  Create
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-6 w-96">
            <h3 className="text-lg font-semibold text-white mb-2">Delete Persona?</h3>
            <p className="text-zinc-400 mb-4">
              This will delete the persona "{showDeleteModal}" and its configuration file.
              This action cannot be undone.
            </p>
            {deleteMutation.isError && (
              <p className="text-red-400 text-sm mb-4">Failed to delete persona</p>
            )}
            <div className="flex gap-3">
              <button
                onClick={() => setShowDeleteModal(null)}
                disabled={deleteMutation.isPending}
                className="flex-1 px-4 py-2 bg-zinc-800 text-white rounded-lg hover:bg-zinc-700 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={() => deleteMutation.mutate(showDeleteModal)}
                disabled={deleteMutation.isPending}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-500 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {deleteMutation.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Trash2 className="w-4 h-4" />
                )}
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* AI Assistant */}
      <AIAssistant context="personas" />
    </div>
  )
}
