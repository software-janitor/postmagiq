/**
 * Voice Profiles page - Manage writing voice profiles with preview of composed prompts.
 */

import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Mic,
  Plus,
  Trash2,
  Edit,
  Loader2,
  Save,
  X,
  Eye,
  Sparkles,
} from 'lucide-react'
import { clsx } from 'clsx'
import { useThemeClasses } from '../hooks/useThemeClasses'
import { apiGet, apiPost, apiPut, apiDelete } from '../api/client'
import { useWorkspaceStore } from '../stores/workspaceStore'
import AIAssistant from '../components/AIAssistant'

// Types
interface VoiceProfile {
  id: string
  workspace_id: string
  name: string
  slug: string
  description: string | null
  is_preset: boolean
  tone_description: string | null
  signature_phrases: string | null
  word_choices: string | null
  example_excerpts: string | null
  avoid_patterns: string | null
  created_at: string
  updated_at: string
}

interface ComposedPromptPreview {
  composed_prompt: string
  voice_profile: string
  universal_rules: string
  persona_template: string | null
}

interface VoiceProfileFormData {
  name: string
  slug: string
  description: string
  tone_description: string
  signature_phrases: string
  word_choices: string
  example_excerpts: string
  avoid_patterns: string
}

const emptyForm: VoiceProfileFormData = {
  name: '',
  slug: '',
  description: '',
  tone_description: '',
  signature_phrases: '',
  word_choices: '',
  example_excerpts: '',
  avoid_patterns: '',
}

function generateSlug(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
}

export default function VoiceProfiles() {
  const theme = useThemeClasses()
  const queryClient = useQueryClient()
  const workspaceId = useWorkspaceStore((s) => s.currentWorkspaceId)

  const [selectedProfile, setSelectedProfile] = useState<string | null>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState<string | null>(null)
  const [showPreviewModal, setShowPreviewModal] = useState(false)
  const [formData, setFormData] = useState<VoiceProfileFormData>(emptyForm)
  const [autoSlug, setAutoSlug] = useState(true)

  // Fetch voice profiles
  const { data: profiles = [], isLoading } = useQuery({
    queryKey: ['voice-profiles', workspaceId],
    queryFn: () => apiGet<VoiceProfile[]>(`/v1/w/${workspaceId}/voice-profiles`),
    enabled: !!workspaceId,
  })

  // Fetch composed prompt preview
  const { data: previewData, isLoading: isLoadingPreview } = useQuery({
    queryKey: ['voice-profile-preview', workspaceId, selectedProfile],
    queryFn: () => apiGet<ComposedPromptPreview>(`/v1/w/${workspaceId}/voice-profiles/${selectedProfile}/preview`),
    enabled: !!workspaceId && !!selectedProfile && showPreviewModal,
  })

  const selectedProfileData = profiles.find(p => p.id === selectedProfile)

  // Auto-select first profile
  useEffect(() => {
    if (profiles.length > 0 && !selectedProfile) {
      setSelectedProfile(profiles[0].id)
    }
  }, [profiles, selectedProfile])

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: VoiceProfileFormData) =>
      apiPost<{ id: string }>(`/v1/w/${workspaceId}/voice-profiles`, {
        name: data.name,
        slug: data.slug || generateSlug(data.name),
        description: data.description || null,
        tone_description: data.tone_description || null,
        signature_phrases: data.signature_phrases || null,
        word_choices: data.word_choices || null,
        example_excerpts: data.example_excerpts || null,
        avoid_patterns: data.avoid_patterns || null,
      }),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['voice-profiles'] })
      setShowCreateModal(false)
      setFormData(emptyForm)
      setAutoSlug(true)
      setSelectedProfile(result.id)
    },
  })

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: (data: VoiceProfileFormData & { id: string }) =>
      apiPut(`/v1/w/${workspaceId}/voice-profiles/${data.id}`, {
        name: data.name,
        slug: data.slug,
        description: data.description || null,
        tone_description: data.tone_description || null,
        signature_phrases: data.signature_phrases || null,
        word_choices: data.word_choices || null,
        example_excerpts: data.example_excerpts || null,
        avoid_patterns: data.avoid_patterns || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['voice-profiles'] })
      setShowEditModal(false)
      setFormData(emptyForm)
    },
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiDelete(`/v1/w/${workspaceId}/voice-profiles/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['voice-profiles'] })
      setShowDeleteModal(null)
      if (selectedProfile === showDeleteModal) {
        setSelectedProfile(profiles.find(p => p.id !== showDeleteModal)?.id || null)
      }
    },
  })

  const handleCreateSubmit = () => {
    if (!formData.name.trim()) return
    createMutation.mutate(formData)
  }

  const handleEditSubmit = () => {
    if (!formData.name.trim() || !selectedProfile) return
    updateMutation.mutate({ ...formData, id: selectedProfile })
  }

  const openEditModal = (profile: VoiceProfile) => {
    setFormData({
      name: profile.name,
      slug: profile.slug,
      description: profile.description || '',
      tone_description: profile.tone_description || '',
      signature_phrases: profile.signature_phrases || '',
      word_choices: profile.word_choices || '',
      example_excerpts: profile.example_excerpts || '',
      avoid_patterns: profile.avoid_patterns || '',
    })
    setAutoSlug(false)
    setShowEditModal(true)
  }

  const handleNameChange = (name: string) => {
    setFormData(prev => ({
      ...prev,
      name,
      slug: autoSlug ? generateSlug(name) : prev.slug,
    }))
  }

  return (
    <div className="h-full flex gap-6">
      {/* Profile List */}
      <div className="w-80 flex-shrink-0 bg-zinc-900 rounded-lg border border-zinc-800 overflow-hidden">
        <div className="p-4 border-b border-zinc-800">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Mic className={clsx('w-5 h-5', theme.iconPrimary)} />
              Voice Profiles
            </h2>
            <button
              onClick={() => {
                setFormData(emptyForm)
                setAutoSlug(true)
                setShowCreateModal(true)
              }}
              className={clsx('p-2 text-white rounded-lg transition-colors bg-gradient-to-r', theme.gradient, theme.gradientHover)}
              title="Add New Profile"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>
          <p className="text-sm text-zinc-400 mt-1">
            Writing voice configurations
          </p>
        </div>

        <div className="overflow-y-auto h-[calc(100%-80px)]">
          {isLoading ? (
            <div className="p-4 text-center text-zinc-400">
              <Loader2 className="w-5 h-5 animate-spin mx-auto" />
            </div>
          ) : profiles.length === 0 ? (
            <div className="p-8 text-center">
              <Mic className="w-12 h-12 mx-auto mb-3 text-zinc-700" />
              <p className="text-zinc-400 mb-4">No voice profiles yet</p>
              <button
                onClick={() => {
                  setFormData(emptyForm)
                  setAutoSlug(true)
                  setShowCreateModal(true)
                }}
                className={clsx('inline-flex items-center gap-2 px-4 py-2 text-white rounded-lg bg-gradient-to-r', theme.gradient, theme.gradientHover)}
              >
                <Plus className="w-4 h-4" />
                Create Profile
              </button>
            </div>
          ) : (
            <div className="divide-y divide-zinc-800">
              {profiles.map((profile) => (
                <div
                  key={profile.id}
                  className={clsx(
                    'w-full p-4 text-left transition-colors relative group cursor-pointer',
                    selectedProfile === profile.id
                      ? clsx(theme.bgMuted, 'border-l-2', theme.border)
                      : 'hover:bg-zinc-800/50'
                  )}
                  onClick={() => setSelectedProfile(profile.id)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={clsx(
                        'w-10 h-10 rounded-lg flex items-center justify-center',
                        selectedProfile === profile.id
                          ? clsx('text-white bg-gradient-to-r', theme.gradient)
                          : 'bg-zinc-800 text-zinc-400'
                      )}>
                        <Mic className="w-5 h-5" />
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-white font-medium truncate">{profile.name}</span>
                          {profile.is_preset && (
                            <span className={clsx('text-xs px-1.5 py-0.5 rounded', theme.bgMuted, theme.textPrimary)}>
                              Preset
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-zinc-500 truncate">{profile.slug}</div>
                      </div>
                    </div>

                    {!profile.is_preset && (
                      <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            openEditModal(profile)
                          }}
                          className="p-1.5 text-zinc-400 hover:text-white hover:bg-zinc-700 rounded"
                          title="Edit"
                        >
                          <Edit className="w-4 h-4" />
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            setShowDeleteModal(profile.id)
                          }}
                          className="p-1.5 text-zinc-400 hover:text-red-400 hover:bg-red-600/10 rounded"
                          title="Delete"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    )}
                  </div>

                  {profile.description && (
                    <p className="mt-2 text-sm text-zinc-400 line-clamp-2 ml-13">
                      {profile.description}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Profile Details */}
      <div className="flex-1 bg-zinc-900 rounded-lg border border-zinc-800 overflow-hidden">
        {selectedProfileData ? (
          <>
            {/* Header */}
            <div className="p-4 border-b border-zinc-800 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className={clsx('w-12 h-12 rounded-xl flex items-center justify-center bg-gradient-to-br', theme.gradient)}>
                  <Mic className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-white flex items-center gap-2">
                    {selectedProfileData.name}
                    {selectedProfileData.is_preset && (
                      <span className={clsx('text-xs px-2 py-0.5 rounded', theme.bgMuted, theme.textPrimary)}>
                        Preset
                      </span>
                    )}
                  </h2>
                  <p className="text-sm text-zinc-400">{selectedProfileData.slug}</p>
                </div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setShowPreviewModal(true)}
                  className="px-4 py-2 bg-zinc-800 text-white rounded-lg hover:bg-zinc-700 flex items-center gap-2"
                >
                  <Eye className="w-4 h-4" />
                  Preview Prompt
                </button>
                {!selectedProfileData.is_preset && (
                  <button
                    onClick={() => openEditModal(selectedProfileData)}
                    className={clsx('px-4 py-2 text-white rounded-lg flex items-center gap-2 bg-gradient-to-r', theme.gradient, theme.gradientHover)}
                  >
                    <Edit className="w-4 h-4" />
                    Edit
                  </button>
                )}
              </div>
            </div>

            {/* Content */}
            <div className="p-6 overflow-y-auto h-[calc(100%-80px)] space-y-6">
              {selectedProfileData.description && (
                <div>
                  <h3 className="text-sm font-medium text-zinc-400 mb-2">Description</h3>
                  <p className="text-white bg-zinc-800/50 rounded-lg p-3">{selectedProfileData.description}</p>
                </div>
              )}

              {selectedProfileData.tone_description && (
                <div>
                  <h3 className="text-sm font-medium text-zinc-400 mb-2">Tone Description</h3>
                  <p className="text-white bg-zinc-800/50 rounded-lg p-3 whitespace-pre-wrap">{selectedProfileData.tone_description}</p>
                </div>
              )}

              {selectedProfileData.signature_phrases && (
                <div>
                  <h3 className="text-sm font-medium text-zinc-400 mb-2">Signature Phrases</h3>
                  <p className="text-white bg-zinc-800/50 rounded-lg p-3 whitespace-pre-wrap">{selectedProfileData.signature_phrases}</p>
                </div>
              )}

              {selectedProfileData.word_choices && (
                <div>
                  <h3 className="text-sm font-medium text-zinc-400 mb-2">Word Choices</h3>
                  <p className="text-white bg-zinc-800/50 rounded-lg p-3 whitespace-pre-wrap">{selectedProfileData.word_choices}</p>
                </div>
              )}

              {selectedProfileData.example_excerpts && (
                <div>
                  <h3 className="text-sm font-medium text-zinc-400 mb-2">Example Excerpts</h3>
                  <p className="text-white bg-zinc-800/50 rounded-lg p-3 whitespace-pre-wrap">{selectedProfileData.example_excerpts}</p>
                </div>
              )}

              {selectedProfileData.avoid_patterns && (
                <div>
                  <h3 className="text-sm font-medium text-zinc-400 mb-2">Avoid Patterns</h3>
                  <p className="text-white bg-zinc-800/50 rounded-lg p-3 whitespace-pre-wrap">{selectedProfileData.avoid_patterns}</p>
                </div>
              )}

              {!selectedProfileData.tone_description &&
               !selectedProfileData.signature_phrases &&
               !selectedProfileData.word_choices &&
               !selectedProfileData.example_excerpts &&
               !selectedProfileData.avoid_patterns && (
                <div className="text-center py-8 text-zinc-500">
                  <Sparkles className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>No voice details configured yet.</p>
                  {!selectedProfileData.is_preset && (
                    <button
                      onClick={() => openEditModal(selectedProfileData)}
                      className={clsx('mt-4 px-4 py-2 text-white rounded-lg bg-gradient-to-r', theme.gradient, theme.gradientHover)}
                    >
                      Add Voice Details
                    </button>
                  )}
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="h-full flex items-center justify-center text-zinc-500">
            <div className="text-center">
              <Mic className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>Select a voice profile to view details</p>
            </div>
          </div>
        )}
      </div>

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-4 border-b border-zinc-800">
              <h2 className="text-lg font-semibold text-white">Create Voice Profile</h2>
              <button
                onClick={() => {
                  setShowCreateModal(false)
                  setFormData(emptyForm)
                }}
                className="p-2 text-zinc-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-zinc-400 mb-1">Name *</label>
                  <input
                    value={formData.name}
                    onChange={(e) => handleNameChange(e.target.value)}
                    placeholder="e.g., Professional Thought Leader"
                    className={clsx('w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none', theme.borderHover)}
                  />
                </div>
                <div>
                  <label className="block text-sm text-zinc-400 mb-1">Slug</label>
                  <input
                    value={formData.slug}
                    onChange={(e) => {
                      setAutoSlug(false)
                      setFormData(prev => ({ ...prev, slug: e.target.value }))
                    }}
                    placeholder="auto-generated-from-name"
                    className={clsx('w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none', theme.borderHover)}
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm text-zinc-400 mb-1">Description</label>
                <input
                  value={formData.description}
                  onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="Brief description of this voice profile"
                  className={clsx('w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none', theme.borderHover)}
                />
              </div>

              <div>
                <label className="block text-sm text-zinc-400 mb-1">Tone Description</label>
                <textarea
                  value={formData.tone_description}
                  onChange={(e) => setFormData(prev => ({ ...prev, tone_description: e.target.value }))}
                  placeholder="Describe the overall tone: reflective, personal, vulnerable about what you didn't know, generous to others..."
                  rows={3}
                  className={clsx('w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none resize-none', theme.borderHover)}
                />
              </div>

              <div>
                <label className="block text-sm text-zinc-400 mb-1">Signature Phrases</label>
                <textarea
                  value={formData.signature_phrases}
                  onChange={(e) => setFormData(prev => ({ ...prev, signature_phrases: e.target.value }))}
                  placeholder={`Phrases that reflect your voice:\n- "I never imagined..."\n- "What I didn't realize was..."\n- "It took me time to realize..."`}
                  rows={4}
                  className={clsx('w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none resize-none', theme.borderHover)}
                />
              </div>

              <div>
                <label className="block text-sm text-zinc-400 mb-1">Word Choices</label>
                <textarea
                  value={formData.word_choices}
                  onChange={(e) => setFormData(prev => ({ ...prev, word_choices: e.target.value }))}
                  placeholder={`Preferred word choices:\n- "assuming" over "hoping"\n- "advice" over "wisdom"\n- Use natural contractions`}
                  rows={4}
                  className={clsx('w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none resize-none', theme.borderHover)}
                />
              </div>

              <div>
                <label className="block text-sm text-zinc-400 mb-1">Example Excerpts</label>
                <textarea
                  value={formData.example_excerpts}
                  onChange={(e) => setFormData(prev => ({ ...prev, example_excerpts: e.target.value }))}
                  placeholder="Paste examples of writing that captures this voice..."
                  rows={4}
                  className={clsx('w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none resize-none', theme.borderHover)}
                />
              </div>

              <div>
                <label className="block text-sm text-zinc-400 mb-1">Avoid Patterns</label>
                <textarea
                  value={formData.avoid_patterns}
                  onChange={(e) => setFormData(prev => ({ ...prev, avoid_patterns: e.target.value }))}
                  placeholder={`Patterns to avoid:\n- Sounding like a template\n- Preachy declarations\n- Bullet points in posts\n- Generic inspiration`}
                  rows={4}
                  className={clsx('w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none resize-none', theme.borderHover)}
                />
              </div>

              {createMutation.isError && (
                <p className="text-red-400 text-sm">
                  Failed to create profile: {createMutation.error?.message || 'Unknown error'}
                </p>
              )}

              <div className="flex justify-end gap-3 pt-2">
                <button
                  onClick={() => {
                    setShowCreateModal(false)
                    setFormData(emptyForm)
                  }}
                  className="px-4 py-2 bg-zinc-800 text-white rounded-lg hover:bg-zinc-700"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateSubmit}
                  disabled={!formData.name.trim() || createMutation.isPending}
                  className={clsx('px-4 py-2 text-white rounded-lg disabled:opacity-50 flex items-center gap-2 bg-gradient-to-r', theme.gradient, theme.gradientHover)}
                >
                  {createMutation.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Save className="w-4 h-4" />
                  )}
                  Create Profile
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {showEditModal && selectedProfileData && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-4 border-b border-zinc-800">
              <h2 className="text-lg font-semibold text-white">Edit Voice Profile</h2>
              <button
                onClick={() => {
                  setShowEditModal(false)
                  setFormData(emptyForm)
                }}
                className="p-2 text-zinc-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-zinc-400 mb-1">Name *</label>
                  <input
                    value={formData.name}
                    onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                    className={clsx('w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none', theme.borderHover)}
                  />
                </div>
                <div>
                  <label className="block text-sm text-zinc-400 mb-1">Slug</label>
                  <input
                    value={formData.slug}
                    onChange={(e) => setFormData(prev => ({ ...prev, slug: e.target.value }))}
                    className={clsx('w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none', theme.borderHover)}
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm text-zinc-400 mb-1">Description</label>
                <input
                  value={formData.description}
                  onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                  className={clsx('w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none', theme.borderHover)}
                />
              </div>

              <div>
                <label className="block text-sm text-zinc-400 mb-1">Tone Description</label>
                <textarea
                  value={formData.tone_description}
                  onChange={(e) => setFormData(prev => ({ ...prev, tone_description: e.target.value }))}
                  rows={3}
                  className={clsx('w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none resize-none', theme.borderHover)}
                />
              </div>

              <div>
                <label className="block text-sm text-zinc-400 mb-1">Signature Phrases</label>
                <textarea
                  value={formData.signature_phrases}
                  onChange={(e) => setFormData(prev => ({ ...prev, signature_phrases: e.target.value }))}
                  rows={4}
                  className={clsx('w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none resize-none', theme.borderHover)}
                />
              </div>

              <div>
                <label className="block text-sm text-zinc-400 mb-1">Word Choices</label>
                <textarea
                  value={formData.word_choices}
                  onChange={(e) => setFormData(prev => ({ ...prev, word_choices: e.target.value }))}
                  rows={4}
                  className={clsx('w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none resize-none', theme.borderHover)}
                />
              </div>

              <div>
                <label className="block text-sm text-zinc-400 mb-1">Example Excerpts</label>
                <textarea
                  value={formData.example_excerpts}
                  onChange={(e) => setFormData(prev => ({ ...prev, example_excerpts: e.target.value }))}
                  rows={4}
                  className={clsx('w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none resize-none', theme.borderHover)}
                />
              </div>

              <div>
                <label className="block text-sm text-zinc-400 mb-1">Avoid Patterns</label>
                <textarea
                  value={formData.avoid_patterns}
                  onChange={(e) => setFormData(prev => ({ ...prev, avoid_patterns: e.target.value }))}
                  rows={4}
                  className={clsx('w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none resize-none', theme.borderHover)}
                />
              </div>

              {updateMutation.isError && (
                <p className="text-red-400 text-sm">
                  Failed to update profile: {updateMutation.error?.message || 'Unknown error'}
                </p>
              )}

              <div className="flex justify-end gap-3 pt-2">
                <button
                  onClick={() => {
                    setShowEditModal(false)
                    setFormData(emptyForm)
                  }}
                  className="px-4 py-2 bg-zinc-800 text-white rounded-lg hover:bg-zinc-700"
                >
                  Cancel
                </button>
                <button
                  onClick={handleEditSubmit}
                  disabled={!formData.name.trim() || updateMutation.isPending}
                  className={clsx('px-4 py-2 text-white rounded-lg disabled:opacity-50 flex items-center gap-2 bg-gradient-to-r', theme.gradient, theme.gradientHover)}
                >
                  {updateMutation.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Save className="w-4 h-4" />
                  )}
                  Save Changes
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 w-96">
            <h3 className="text-lg font-semibold text-white mb-2">Delete Voice Profile?</h3>
            <p className="text-zinc-400 mb-4">
              This will permanently delete this voice profile. This action cannot be undone.
            </p>
            {deleteMutation.isError && (
              <p className="text-red-400 text-sm mb-4">
                Failed to delete: {deleteMutation.error?.message || 'Unknown error'}
              </p>
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

      {/* Preview Modal */}
      {showPreviewModal && selectedProfileData && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
            <div className="flex items-center justify-between p-4 border-b border-zinc-800">
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <Eye className="w-5 h-5" />
                Composed Prompt Preview
              </h2>
              <button
                onClick={() => setShowPreviewModal(false)}
                className="p-2 text-zinc-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6">
              {isLoadingPreview ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className={clsx('w-8 h-8 animate-spin', theme.textPrimary)} />
                </div>
              ) : previewData ? (
                <div className="space-y-6">
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <span className={clsx('text-xs uppercase tracking-wide font-medium', theme.textPrimary)}>
                        Full Composed Prompt
                      </span>
                      <span className="text-xs text-zinc-500">
                        (Universal Rules + Voice Profile + Persona Template)
                      </span>
                    </div>
                    <pre className="text-white bg-zinc-800/50 rounded-lg p-4 text-sm whitespace-pre-wrap overflow-x-auto font-mono max-h-96 overflow-y-auto">
                      {previewData.composed_prompt}
                    </pre>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <div className="text-xs uppercase tracking-wide text-zinc-400 mb-2">Universal Rules</div>
                      <pre className="text-zinc-300 bg-zinc-800/30 rounded-lg p-3 text-xs whitespace-pre-wrap overflow-x-auto font-mono max-h-48 overflow-y-auto">
                        {previewData.universal_rules || '(none)'}
                      </pre>
                    </div>
                    <div>
                      <div className="text-xs uppercase tracking-wide text-zinc-400 mb-2">Voice Profile Section</div>
                      <pre className="text-zinc-300 bg-zinc-800/30 rounded-lg p-3 text-xs whitespace-pre-wrap overflow-x-auto font-mono max-h-48 overflow-y-auto">
                        {previewData.voice_profile || '(none)'}
                      </pre>
                    </div>
                  </div>

                  {previewData.persona_template && (
                    <div>
                      <div className="text-xs uppercase tracking-wide text-zinc-400 mb-2">Persona Template</div>
                      <pre className="text-zinc-300 bg-zinc-800/30 rounded-lg p-3 text-xs whitespace-pre-wrap overflow-x-auto font-mono max-h-48 overflow-y-auto">
                        {previewData.persona_template}
                      </pre>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-12 text-zinc-500">
                  <p>Failed to load preview</p>
                </div>
              )}
            </div>

            <div className="p-4 border-t border-zinc-800">
              <button
                onClick={() => setShowPreviewModal(false)}
                className="w-full px-4 py-2 bg-zinc-800 text-white rounded-lg hover:bg-zinc-700"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* AI Assistant */}
      <AIAssistant context="voice" />
    </div>
  )
}
