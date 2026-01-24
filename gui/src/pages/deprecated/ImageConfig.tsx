import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Camera, User, Shirt, Coffee, Bot,
  Plus, Trash2, Save, RefreshCw, Check, X, Edit2, Upload, Users, Sparkles, Settings
} from 'lucide-react'
import { clsx } from 'clsx'
import { apiGet, apiPost, apiPut, apiDelete } from '../api/client'
import AIAssistant from '../components/AIAssistant'
import SceneCharacterPicker from '../components/SceneCharacterPicker'
import SceneBuilder from '../components/SceneBuilder'
import PropRulesEditor from '../components/PropRulesEditor'
import { useThemeClasses } from '../hooks/useThemeClasses'
import ThemeIcon from '../components/ThemeIcon'

type TabType = 'scenes' | 'poses' | 'outfits' | 'props' | 'characters'

interface Scene {
  id: number
  code: string
  name: string
  sentiment: string
  viewpoint: string
  description: string
  is_hardware_only: number
  no_desk_props: number
}

interface Pose {
  id: number
  code: string
  sentiment: string
  description: string
  emotional_note: string | null
}

interface Outfit {
  id: number
  vest: string
  shirt: string
  pants: string
}

interface Prop {
  id: number
  category: string
  description: string
  context: string
}

interface Character {
  id: number
  character_type: string
  appearance: string
  face_details: string | null
  clothing_rules: string | null
}

const TABS: { id: TabType; label: string; icon: React.ReactNode }[] = [
  { id: 'scenes', label: 'Scenes', icon: <Camera className="w-4 h-4" /> },
  { id: 'poses', label: 'Poses', icon: <User className="w-4 h-4" /> },
  { id: 'outfits', label: 'Outfits', icon: <Shirt className="w-4 h-4" /> },
  { id: 'props', label: 'Props', icon: <Coffee className="w-4 h-4" /> },
  { id: 'characters', label: 'Characters', icon: <Bot className="w-4 h-4" /> },
]

const SENTIMENTS = ['SUCCESS', 'FAILURE', 'UNRESOLVED']
const VIEWPOINTS = ['standard', 'wide', 'close_up', 'over_shoulder', 'birds_eye', 'high_angle', 'profile']
const PROP_CATEGORIES = ['notes', 'drinks', 'tech', 'plants', 'hardware_boards', 'hardware_tools']
const PROP_CONTEXTS = ['all', 'software', 'hardware']

export default function ImageConfig() {
  const theme = useThemeClasses()
  const [activeTab, setActiveTab] = useState<TabType>('scenes')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [showAddModal, setShowAddModal] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<number | null>(null)
  const [sentimentFilter, setSentimentFilter] = useState<string | null>(null)
  const [showImportModal, setShowImportModal] = useState(false)
  const [jsonInput, setJsonInput] = useState('')
  const [importError, setImportError] = useState<string | null>(null)
  const [showCharacterPicker, setShowCharacterPicker] = useState<number | null>(null)
  const [showSceneBuilder, setShowSceneBuilder] = useState(false)
  const [showPropRules, setShowPropRules] = useState(false)

  // Add form state
  const [newScene, setNewScene] = useState({ code: '', name: '', sentiment: 'SUCCESS', description: '', viewpoint: 'standard', is_hardware_only: false, no_desk_props: false })
  const [newPose, setNewPose] = useState({ code: '', sentiment: 'SUCCESS', description: '', emotional_note: '' })
  const [newOutfit, setNewOutfit] = useState({ vest: '', shirt: '', pants: 'Dark pants' })
  const [newProp, setNewProp] = useState({ category: 'notes', description: '', context: 'all' })

  const queryClient = useQueryClient()
  const userId = 1 // Single user mode

  // Seed defaults on first load
  const seedMutation = useMutation({
    mutationFn: () => apiPost(`/image-config/users/${userId}/seed`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['image-config'] })
    },
  })

  // Reset to defaults (delete existing and re-seed)
  const resetMutation = useMutation({
    mutationFn: () => apiPost(`/image-config/users/${userId}/reset`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['image-config'] })
    },
  })

  // Create mutations
  const createSceneMutation = useMutation({
    mutationFn: (data: typeof newScene) => apiPost(`/image-config/users/${userId}/scenes`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['image-config', 'scenes'] })
      setShowAddModal(false)
      setNewScene({ code: '', name: '', sentiment: 'SUCCESS', description: '', viewpoint: 'standard', is_hardware_only: false, no_desk_props: false })
    },
  })

  const createPoseMutation = useMutation({
    mutationFn: (data: typeof newPose) => apiPost(`/image-config/users/${userId}/poses`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['image-config', 'poses'] })
      setShowAddModal(false)
      setNewPose({ code: '', sentiment: 'SUCCESS', description: '', emotional_note: '' })
    },
  })

  const createOutfitMutation = useMutation({
    mutationFn: (data: typeof newOutfit) => apiPost(`/image-config/users/${userId}/outfits`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['image-config', 'outfits'] })
      setShowAddModal(false)
      setNewOutfit({ vest: '', shirt: '', pants: 'Dark pants' })
    },
  })

  // Bulk import outfits mutation
  const bulkImportOutfitsMutation = useMutation({
    mutationFn: (outfits: Array<{ vest: string; shirt: string; pants?: string }>) =>
      apiPost<{ imported: number; skipped: number; errors: string[] }>(
        `/image-config/users/${userId}/outfits/bulk`,
        { outfits }
      ),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['image-config', 'outfits'] })
      setShowImportModal(false)
      setJsonInput('')
      setImportError(null)
      // Show success message with counts
      const msg = `Imported ${data.imported} outfit(s). ${data.skipped > 0 ? `Skipped ${data.skipped} duplicate(s).` : ''}`
      alert(msg)
    },
    onError: (error: Error) => {
      setImportError(error.message)
    },
  })

  const createPropMutation = useMutation({
    mutationFn: (data: typeof newProp) => apiPost(`/image-config/users/${userId}/props`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['image-config', 'props'] })
      setShowAddModal(false)
      setNewProp({ category: 'notes', description: '', context: 'all' })
    },
  })

  // Queries
  const { data: scenesData } = useQuery({
    queryKey: ['image-config', 'scenes', userId, sentimentFilter],
    queryFn: () => apiGet<{ scenes: Scene[] }>(`/image-config/users/${userId}/scenes${sentimentFilter ? `?sentiment=${sentimentFilter}` : ''}`),
  })

  const { data: posesData } = useQuery({
    queryKey: ['image-config', 'poses', userId, sentimentFilter],
    queryFn: () => apiGet<{ poses: Pose[] }>(`/image-config/users/${userId}/poses${sentimentFilter ? `?sentiment=${sentimentFilter}` : ''}`),
  })

  const { data: outfitsData } = useQuery({
    queryKey: ['image-config', 'outfits', userId],
    queryFn: () => apiGet<{ outfits: Outfit[] }>(`/image-config/users/${userId}/outfits`),
  })

  const { data: propsData } = useQuery({
    queryKey: ['image-config', 'props', userId],
    queryFn: () => apiGet<{ props: Prop[] }>(`/image-config/users/${userId}/props`),
  })

  const { data: charactersData } = useQuery({
    queryKey: ['image-config', 'characters', userId],
    queryFn: () => apiGet<{ characters: Character[] }>(`/image-config/users/${userId}/characters`),
  })

  // Check if seeding is needed
  useEffect(() => {
    if (scenesData?.scenes?.length === 0) {
      seedMutation.mutate()
    }
  }, [scenesData])

  // Delete mutations
  const deleteSceneMutation = useMutation({
    mutationFn: (id: number) => apiDelete(`/image-config/scenes/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['image-config', 'scenes'] })
      setShowDeleteConfirm(null)
    },
  })

  const deletePoseMutation = useMutation({
    mutationFn: (id: number) => apiDelete(`/image-config/poses/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['image-config', 'poses'] })
      setShowDeleteConfirm(null)
    },
  })

  const deleteOutfitMutation = useMutation({
    mutationFn: (id: number) => apiDelete(`/image-config/outfits/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['image-config', 'outfits'] })
      setShowDeleteConfirm(null)
    },
  })

  const deletePropMutation = useMutation({
    mutationFn: (id: number) => apiDelete(`/image-config/props/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['image-config', 'props'] })
      setShowDeleteConfirm(null)
    },
  })

  const handleDelete = (id: number) => {
    switch (activeTab) {
      case 'scenes':
        deleteSceneMutation.mutate(id)
        break
      case 'poses':
        deletePoseMutation.mutate(id)
        break
      case 'outfits':
        deleteOutfitMutation.mutate(id)
        break
      case 'props':
        deletePropMutation.mutate(id)
        break
    }
  }

  const scenes = scenesData?.scenes || []
  const poses = posesData?.poses || []
  const outfits = outfitsData?.outfits || []
  const props = propsData?.props || []
  const characters = charactersData?.characters || []

  return (
    <div className="h-full flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <ThemeIcon className={clsx("w-8 h-8", theme.textPrimary)} />
          <div>
            <h1 className="text-2xl font-bold text-white">Image Configuration</h1>
            <p className="text-sm text-zinc-400">Customize scenes, poses, outfits, props, and characters</p>
          </div>
        </div>
        <div className="flex gap-2">
          {activeTab === 'outfits' && (
            <button
              onClick={() => setShowImportModal(true)}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-500 flex items-center gap-2"
            >
              <Upload className="w-4 h-4" />
              Import JSON
            </button>
          )}
          {activeTab === 'scenes' && (
            <button
              onClick={() => setShowSceneBuilder(true)}
              className={clsx("px-4 py-2 text-white rounded-lg flex items-center gap-2 bg-gradient-to-r", theme.gradient, theme.gradientHover)}
            >
              <Sparkles className="w-4 h-4" />
              AI Generate
            </button>
          )}
          {activeTab === 'props' && (
            <button
              onClick={() => setShowPropRules(true)}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-500 flex items-center gap-2"
            >
              <Settings className="w-4 h-4" />
              Selection Rules
            </button>
          )}
          <button
            onClick={() => setShowAddModal(true)}
            disabled={activeTab === 'characters'}
            className={clsx("px-4 py-2 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 bg-gradient-to-r", theme.gradient, theme.gradientHover)}
          >
            <Plus className="w-4 h-4" />
            Add New
          </button>
          <button
            onClick={() => resetMutation.mutate()}
            disabled={resetMutation.isPending}
            className="px-4 py-2 bg-zinc-800 text-white rounded-lg hover:bg-zinc-700 flex items-center gap-2"
          >
            <RefreshCw className={clsx("w-4 h-4", resetMutation.isPending && "animate-spin")} />
            Reset to Defaults
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-zinc-800 pb-2">
        {TABS.map(tab => (
          <button
            key={tab.id}
            onClick={() => {
              setActiveTab(tab.id)
              setEditingId(null)
            }}
            className={clsx(
              'px-4 py-2 rounded-t-lg flex items-center gap-2 transition-colors',
              activeTab === tab.id
                ? `bg-gradient-to-r ${theme.gradient} text-white`
                : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
            )}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Filter (for scenes and poses) */}
      {(activeTab === 'scenes' || activeTab === 'poses') && (
        <div className="flex items-center gap-2">
          <span className="text-sm text-zinc-400">Filter:</span>
          <button
            onClick={() => setSentimentFilter(null)}
            className={clsx(
              'px-3 py-1 rounded text-sm',
              !sentimentFilter ? `bg-gradient-to-r ${theme.gradient} text-white` : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
            )}
          >
            All
          </button>
          {SENTIMENTS.map(s => (
            <button
              key={s}
              onClick={() => setSentimentFilter(s)}
              className={clsx(
                'px-3 py-1 rounded text-sm',
                sentimentFilter === s ? `bg-gradient-to-r ${theme.gradient} text-white` : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
              )}
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {activeTab === 'scenes' && (
          <ScenesTab
            scenes={scenes}
            editingId={editingId}
            setEditingId={setEditingId}
            setShowDeleteConfirm={setShowDeleteConfirm}
            onOpenCharacters={setShowCharacterPicker}
          />
        )}
        {activeTab === 'poses' && (
          <PosesTab
            poses={poses}
            editingId={editingId}
            setEditingId={setEditingId}
            setShowDeleteConfirm={setShowDeleteConfirm}
          />
        )}
        {activeTab === 'outfits' && (
          <OutfitsTab
            outfits={outfits}
            editingId={editingId}
            setEditingId={setEditingId}
            setShowDeleteConfirm={setShowDeleteConfirm}
          />
        )}
        {activeTab === 'props' && (
          <PropsTab
            props={props}
            editingId={editingId}
            setEditingId={setEditingId}
            setShowDeleteConfirm={setShowDeleteConfirm}
          />
        )}
        {activeTab === 'characters' && (
          <CharactersTab
            characters={characters}
            editingId={editingId}
            setEditingId={setEditingId}
          />
        )}
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm !== null && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-6 w-96">
            <h3 className="text-lg font-semibold text-white mb-4">Confirm Delete</h3>
            <p className="text-zinc-400 mb-6">Are you sure you want to delete this item? This cannot be undone.</p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowDeleteConfirm(null)}
                className="flex-1 px-4 py-2 bg-zinc-800 text-white rounded-lg hover:bg-zinc-700"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDelete(showDeleteConfirm)}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-500"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-6 w-[600px] max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-semibold text-white mb-4">
              Add New {activeTab.charAt(0).toUpperCase() + activeTab.slice(1, -1)}
            </h3>

            {/* Scene Form */}
            {activeTab === 'scenes' && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm text-zinc-400 mb-1">Code</label>
                    <input
                      value={newScene.code}
                      onChange={e => setNewScene({ ...newScene, code: e.target.value })}
                      className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded text-white"
                      placeholder="e.g., A27"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-zinc-400 mb-1">Name</label>
                    <input
                      value={newScene.name}
                      onChange={e => setNewScene({ ...newScene, name: e.target.value })}
                      className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded text-white"
                      placeholder="Scene name"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm text-zinc-400 mb-1">Sentiment</label>
                    <select
                      value={newScene.sentiment}
                      onChange={e => setNewScene({ ...newScene, sentiment: e.target.value })}
                      className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded text-white"
                    >
                      {SENTIMENTS.map(s => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm text-zinc-400 mb-1">Viewpoint</label>
                    <select
                      value={newScene.viewpoint}
                      onChange={e => setNewScene({ ...newScene, viewpoint: e.target.value })}
                      className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded text-white"
                    >
                      {VIEWPOINTS.map(v => <option key={v} value={v}>{v}</option>)}
                    </select>
                  </div>
                </div>
                <div>
                  <label className="block text-sm text-zinc-400 mb-1">Description</label>
                  <textarea
                    value={newScene.description}
                    onChange={e => setNewScene({ ...newScene, description: e.target.value })}
                    className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded text-white"
                    rows={4}
                    placeholder="Describe the scene..."
                  />
                </div>
                <div className="flex gap-4">
                  <label className="flex items-center gap-2 text-zinc-400">
                    <input
                      type="checkbox"
                      checked={newScene.is_hardware_only}
                      onChange={e => setNewScene({ ...newScene, is_hardware_only: e.target.checked })}
                      className="rounded"
                    />
                    Hardware only
                  </label>
                  <label className="flex items-center gap-2 text-zinc-400">
                    <input
                      type="checkbox"
                      checked={newScene.no_desk_props}
                      onChange={e => setNewScene({ ...newScene, no_desk_props: e.target.checked })}
                      className="rounded"
                    />
                    No desk props
                  </label>
                </div>
              </div>
            )}

            {/* Pose Form */}
            {activeTab === 'poses' && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm text-zinc-400 mb-1">Code</label>
                    <input
                      value={newPose.code}
                      onChange={e => setNewPose({ ...newPose, code: e.target.value })}
                      className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded text-white"
                      placeholder="e.g., S11"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-zinc-400 mb-1">Sentiment</label>
                    <select
                      value={newPose.sentiment}
                      onChange={e => setNewPose({ ...newPose, sentiment: e.target.value })}
                      className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded text-white"
                    >
                      {SENTIMENTS.map(s => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </div>
                </div>
                <div>
                  <label className="block text-sm text-zinc-400 mb-1">Description</label>
                  <textarea
                    value={newPose.description}
                    onChange={e => setNewPose({ ...newPose, description: e.target.value })}
                    className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded text-white"
                    rows={3}
                    placeholder="Describe the pose..."
                  />
                </div>
                <div>
                  <label className="block text-sm text-zinc-400 mb-1">Emotional Note</label>
                  <input
                    value={newPose.emotional_note}
                    onChange={e => setNewPose({ ...newPose, emotional_note: e.target.value })}
                    className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded text-white"
                    placeholder="e.g., Pride, ownership"
                  />
                </div>
              </div>
            )}

            {/* Outfit Form */}
            {activeTab === 'outfits' && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-zinc-400 mb-1">Vest</label>
                  <input
                    value={newOutfit.vest}
                    onChange={e => setNewOutfit({ ...newOutfit, vest: e.target.value })}
                    className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded text-white"
                    placeholder="e.g., Navy Blue suit vest"
                  />
                </div>
                <div>
                  <label className="block text-sm text-zinc-400 mb-1">Shirt</label>
                  <input
                    value={newOutfit.shirt}
                    onChange={e => setNewOutfit({ ...newOutfit, shirt: e.target.value })}
                    className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded text-white"
                    placeholder="e.g., White"
                  />
                </div>
                <div>
                  <label className="block text-sm text-zinc-400 mb-1">Pants</label>
                  <input
                    value={newOutfit.pants}
                    onChange={e => setNewOutfit({ ...newOutfit, pants: e.target.value })}
                    className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded text-white"
                    placeholder="e.g., Dark navy pants"
                  />
                </div>
              </div>
            )}

            {/* Prop Form */}
            {activeTab === 'props' && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm text-zinc-400 mb-1">Category</label>
                    <select
                      value={newProp.category}
                      onChange={e => setNewProp({ ...newProp, category: e.target.value })}
                      className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded text-white"
                    >
                      {PROP_CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm text-zinc-400 mb-1">Context</label>
                    <select
                      value={newProp.context}
                      onChange={e => setNewProp({ ...newProp, context: e.target.value })}
                      className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded text-white"
                    >
                      {PROP_CONTEXTS.map(c => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </div>
                </div>
                <div>
                  <label className="block text-sm text-zinc-400 mb-1">Description</label>
                  <textarea
                    value={newProp.description}
                    onChange={e => setNewProp({ ...newProp, description: e.target.value })}
                    className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded text-white"
                    rows={3}
                    placeholder="Describe the prop..."
                  />
                </div>
              </div>
            )}

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowAddModal(false)}
                className="flex-1 px-4 py-2 bg-zinc-800 text-white rounded-lg hover:bg-zinc-700"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  if (activeTab === 'scenes') createSceneMutation.mutate(newScene)
                  else if (activeTab === 'poses') createPoseMutation.mutate(newPose)
                  else if (activeTab === 'outfits') createOutfitMutation.mutate(newOutfit)
                  else if (activeTab === 'props') createPropMutation.mutate(newProp)
                }}
                disabled={
                  createSceneMutation.isPending ||
                  createPoseMutation.isPending ||
                  createOutfitMutation.isPending ||
                  createPropMutation.isPending
                }
                className={clsx("flex-1 px-4 py-2 text-white rounded-lg flex items-center justify-center gap-2 bg-gradient-to-r", theme.gradient, theme.gradientHover)}
              >
                <Plus className="w-4 h-4" />
                Add
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Import JSON Modal (for outfits) */}
      {showImportModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-6 w-[700px] max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-semibold text-white mb-4">
              Import Outfits from JSON
            </h3>

            <div className="space-y-4">
              <div>
                <label className="block text-sm text-zinc-400 mb-2">
                  Paste JSON array of outfits:
                </label>
                <textarea
                  value={jsonInput}
                  onChange={e => {
                    setJsonInput(e.target.value)
                    setImportError(null)
                  }}
                  className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded text-white font-mono text-sm"
                  rows={12}
                  placeholder={`[
  {
    "vest": "Navy Blue suit vest",
    "shirt": "White",
    "pants": "Dark navy pants"
  },
  {
    "vest": "Charcoal Grey suit vest",
    "shirt": "Light Blue",
    "pants": "Charcoal pants"
  }
]`}
                />
              </div>

              <div className="text-xs text-zinc-500">
                <p className="mb-1">Expected format:</p>
                <ul className="list-disc list-inside space-y-0.5">
                  <li><code className="text-purple-400">vest</code> - Required</li>
                  <li><code className="text-purple-400">shirt</code> - Required</li>
                  <li><code className="text-purple-400">pants</code> - Optional (defaults to "Dark pants")</li>
                </ul>
                <p className="mt-2">Duplicates will be skipped automatically.</p>
              </div>

              {importError && (
                <div className="p-3 bg-red-900/20 border border-red-800 rounded text-red-400 text-sm">
                  {importError}
                </div>
              )}
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => {
                  setShowImportModal(false)
                  setJsonInput('')
                  setImportError(null)
                }}
                className="flex-1 px-4 py-2 bg-zinc-800 text-white rounded-lg hover:bg-zinc-700"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  try {
                    const parsed = JSON.parse(jsonInput)
                    if (!Array.isArray(parsed)) {
                      setImportError('JSON must be an array of outfit objects')
                      return
                    }
                    if (parsed.length === 0) {
                      setImportError('Array is empty')
                      return
                    }
                    bulkImportOutfitsMutation.mutate(parsed)
                  } catch (e) {
                    setImportError(`Invalid JSON: ${(e as Error).message}`)
                  }
                }}
                disabled={bulkImportOutfitsMutation.isPending || !jsonInput.trim()}
                className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {bulkImportOutfitsMutation.isPending ? (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                ) : (
                  <Upload className="w-4 h-4" />
                )}
                Import
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Scene Character Picker */}
      {showCharacterPicker !== null && (
        <SceneCharacterPicker
          sceneId={showCharacterPicker}
          userId={userId}
          onClose={() => setShowCharacterPicker(null)}
        />
      )}

      {/* Scene Builder */}
      {showSceneBuilder && (
        <SceneBuilder
          userId={userId}
          onClose={() => setShowSceneBuilder(false)}
        />
      )}

      {/* Prop Rules Editor */}
      {showPropRules && (
        <PropRulesEditor
          userId={userId}
          onClose={() => setShowPropRules(false)}
        />
      )}

      {/* AI Assistant */}
      <AIAssistant context={activeTab} />
    </div>
  )
}

// =========================================================================
// Scenes Tab
// =========================================================================

function ScenesTab({ scenes, editingId, setEditingId, setShowDeleteConfirm, onOpenCharacters }: {
  scenes: Scene[]
  editingId: number | null
  setEditingId: (id: number | null) => void
  setShowDeleteConfirm: (id: number | null) => void
  onOpenCharacters: (id: number) => void
}) {
  const queryClient = useQueryClient()
  const [editForm, setEditForm] = useState<Partial<Scene>>({})

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Scene> }) =>
      apiPut(`/image-config/scenes/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['image-config', 'scenes'] })
      setEditingId(null)
    },
  })

  const startEdit = (scene: Scene) => {
    setEditingId(scene.id)
    setEditForm({ name: scene.name, description: scene.description, viewpoint: scene.viewpoint })
  }

  const saveEdit = (id: number) => {
    updateMutation.mutate({ id, data: editForm })
  }

  return (
    <div className="grid gap-4">
      {scenes.map(scene => (
        <div key={scene.id} className="bg-zinc-900 rounded-lg border border-zinc-800 p-4">
          {editingId === scene.id ? (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <span className={clsx(
                  'px-2 py-1 rounded text-xs font-bold',
                  scene.sentiment === 'SUCCESS' ? 'bg-cyan-600/20 text-cyan-400' :
                  scene.sentiment === 'FAILURE' ? 'bg-red-600/20 text-red-400' :
                  'bg-amber-600/20 text-amber-400'
                )}>
                  {scene.code}
                </span>
                <input
                  value={editForm.name || ''}
                  onChange={e => setEditForm({ ...editForm, name: e.target.value })}
                  className="flex-1 px-2 py-1 bg-zinc-800 border border-zinc-700 rounded text-white"
                  placeholder="Scene name"
                />
                <select
                  value={editForm.viewpoint || 'standard'}
                  onChange={e => setEditForm({ ...editForm, viewpoint: e.target.value })}
                  className="px-2 py-1 bg-zinc-800 border border-zinc-700 rounded text-white text-sm"
                >
                  {VIEWPOINTS.map(v => (
                    <option key={v} value={v}>{v}</option>
                  ))}
                </select>
              </div>
              <textarea
                value={editForm.description || ''}
                onChange={e => setEditForm({ ...editForm, description: e.target.value })}
                className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded text-white text-sm"
                rows={3}
                placeholder="Scene description..."
              />
              <div className="flex gap-2">
                <button
                  onClick={() => saveEdit(scene.id)}
                  disabled={updateMutation.isPending}
                  className="px-3 py-1 bg-green-600 text-white rounded flex items-center gap-1 text-sm"
                >
                  <Check className="w-4 h-4" />
                  Save
                </button>
                <button
                  onClick={() => setEditingId(null)}
                  className="px-3 py-1 bg-zinc-700 text-white rounded flex items-center gap-1 text-sm"
                >
                  <X className="w-4 h-4" />
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className={clsx(
                    'px-2 py-1 rounded text-xs font-bold',
                    scene.sentiment === 'SUCCESS' ? 'bg-cyan-600/20 text-cyan-400' :
                    scene.sentiment === 'FAILURE' ? 'bg-red-600/20 text-red-400' :
                    'bg-amber-600/20 text-amber-400'
                  )}>
                    {scene.code}
                  </span>
                  <span className="text-white font-medium">{scene.name}</span>
                  <span className="text-zinc-500 text-sm">[{scene.viewpoint}]</span>
                  {scene.is_hardware_only ? <span className="text-xs bg-amber-600/20 text-amber-400 px-2 py-0.5 rounded">hardware only</span> : null}
                  {scene.no_desk_props ? <span className="text-xs bg-zinc-600/20 text-zinc-400 px-2 py-0.5 rounded">no props</span> : null}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => onOpenCharacters(scene.id)}
                    className="p-1 text-zinc-400 hover:text-amber-400"
                    title="Manage characters in scene"
                  >
                    <Users className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => startEdit(scene)}
                    className="p-1 text-zinc-400 hover:text-white"
                  >
                    <Edit2 className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setShowDeleteConfirm(scene.id)}
                    className="p-1 text-zinc-400 hover:text-red-400"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
              <p className="text-zinc-400 text-sm">{scene.description}</p>
            </>
          )}
        </div>
      ))}
    </div>
  )
}

// =========================================================================
// Poses Tab
// =========================================================================

function PosesTab({ poses, editingId, setEditingId, setShowDeleteConfirm }: {
  poses: Pose[]
  editingId: number | null
  setEditingId: (id: number | null) => void
  setShowDeleteConfirm: (id: number | null) => void
}) {
  const queryClient = useQueryClient()
  const [editForm, setEditForm] = useState<Partial<Pose>>({})

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Pose> }) =>
      apiPut(`/image-config/poses/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['image-config', 'poses'] })
      setEditingId(null)
    },
  })

  const startEdit = (pose: Pose) => {
    setEditingId(pose.id)
    setEditForm({ description: pose.description, emotional_note: pose.emotional_note })
  }

  const saveEdit = (id: number) => {
    updateMutation.mutate({ id, data: editForm })
  }

  return (
    <div className="grid gap-3">
      {poses.map(pose => (
        <div key={pose.id} className="bg-zinc-900 rounded-lg border border-zinc-800 p-4">
          {editingId === pose.id ? (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <span className={clsx(
                  'px-2 py-1 rounded text-xs font-bold',
                  pose.sentiment === 'SUCCESS' ? 'bg-cyan-600/20 text-cyan-400' :
                  pose.sentiment === 'FAILURE' ? 'bg-red-600/20 text-red-400' :
                  'bg-amber-600/20 text-amber-400'
                )}>
                  {pose.code}
                </span>
              </div>
              <input
                value={editForm.description || ''}
                onChange={e => setEditForm({ ...editForm, description: e.target.value })}
                className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded text-white text-sm"
                placeholder="Pose description..."
              />
              <input
                value={editForm.emotional_note || ''}
                onChange={e => setEditForm({ ...editForm, emotional_note: e.target.value })}
                className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded text-white text-sm"
                placeholder="Emotional note..."
              />
              <div className="flex gap-2">
                <button
                  onClick={() => saveEdit(pose.id)}
                  disabled={updateMutation.isPending}
                  className="px-3 py-1 bg-green-600 text-white rounded flex items-center gap-1 text-sm"
                >
                  <Check className="w-4 h-4" />
                  Save
                </button>
                <button
                  onClick={() => setEditingId(null)}
                  className="px-3 py-1 bg-zinc-700 text-white rounded flex items-center gap-1 text-sm"
                >
                  <X className="w-4 h-4" />
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className={clsx(
                  'px-2 py-1 rounded text-xs font-bold',
                  pose.sentiment === 'SUCCESS' ? 'bg-cyan-600/20 text-cyan-400' :
                  pose.sentiment === 'FAILURE' ? 'bg-red-600/20 text-red-400' :
                  'bg-amber-600/20 text-amber-400'
                )}>
                  {pose.code}
                </span>
                <span className="text-white">{pose.description}</span>
                {pose.emotional_note && (
                  <span className="text-zinc-500 text-sm">({pose.emotional_note})</span>
                )}
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => startEdit(pose)}
                  className="p-1 text-zinc-400 hover:text-white"
                >
                  <Edit2 className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setShowDeleteConfirm(pose.id)}
                  className="p-1 text-zinc-400 hover:text-red-400"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

// =========================================================================
// Outfits Tab
// =========================================================================

function OutfitsTab({ outfits, editingId, setEditingId, setShowDeleteConfirm }: {
  outfits: Outfit[]
  editingId: number | null
  setEditingId: (id: number | null) => void
  setShowDeleteConfirm: (id: number | null) => void
}) {
  const theme = useThemeClasses()
  const queryClient = useQueryClient()
  const [editForm, setEditForm] = useState<Partial<Outfit>>({})

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Outfit> }) =>
      apiPut(`/image-config/outfits/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['image-config', 'outfits'] })
      setEditingId(null)
    },
  })

  const startEdit = (outfit: Outfit) => {
    setEditingId(outfit.id)
    setEditForm({ vest: outfit.vest, shirt: outfit.shirt, pants: outfit.pants })
  }

  const saveEdit = (id: number) => {
    updateMutation.mutate({ id, data: editForm })
  }

  return (
    <div className="grid grid-cols-2 gap-4">
      {outfits.map(outfit => (
        <div key={outfit.id} className="bg-zinc-900 rounded-lg border border-zinc-800 p-4">
          {editingId === outfit.id ? (
            <div className="space-y-3">
              <input
                value={editForm.vest || ''}
                onChange={e => setEditForm({ ...editForm, vest: e.target.value })}
                className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded text-white text-sm"
                placeholder="Vest..."
              />
              <input
                value={editForm.shirt || ''}
                onChange={e => setEditForm({ ...editForm, shirt: e.target.value })}
                className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded text-white text-sm"
                placeholder="Shirt..."
              />
              <input
                value={editForm.pants || ''}
                onChange={e => setEditForm({ ...editForm, pants: e.target.value })}
                className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded text-white text-sm"
                placeholder="Pants..."
              />
              <div className="flex gap-2">
                <button
                  onClick={() => saveEdit(outfit.id)}
                  disabled={updateMutation.isPending}
                  className="px-3 py-1 bg-green-600 text-white rounded flex items-center gap-1 text-sm"
                >
                  <Check className="w-4 h-4" />
                  Save
                </button>
                <button
                  onClick={() => setEditingId(null)}
                  className="px-3 py-1 bg-zinc-700 text-white rounded flex items-center gap-1 text-sm"
                >
                  <X className="w-4 h-4" />
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <>
              <div className="flex justify-between items-start mb-2">
                <Shirt className={clsx("w-5 h-5", theme.textPrimary)} />
                <div className="flex gap-2">
                  <button
                    onClick={() => startEdit(outfit)}
                    className="p-1 text-zinc-400 hover:text-white"
                  >
                    <Edit2 className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setShowDeleteConfirm(outfit.id)}
                    className="p-1 text-zinc-400 hover:text-red-400"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
              <div className="space-y-1 text-sm">
                <div><span className="text-zinc-500">Vest:</span> <span className="text-white">{outfit.vest}</span></div>
                <div><span className="text-zinc-500">Shirt:</span> <span className="text-white">{outfit.shirt}</span></div>
                <div><span className="text-zinc-500">Pants:</span> <span className="text-white">{outfit.pants}</span></div>
              </div>
            </>
          )}
        </div>
      ))}
    </div>
  )
}

// =========================================================================
// Props Tab
// =========================================================================

function PropsTab({ props, editingId, setEditingId, setShowDeleteConfirm }: {
  props: Prop[]
  editingId: number | null
  setEditingId: (id: number | null) => void
  setShowDeleteConfirm: (id: number | null) => void
}) {
  const queryClient = useQueryClient()
  const [editForm, setEditForm] = useState<Partial<Prop>>({})

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Prop> }) =>
      apiPut(`/image-config/props/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['image-config', 'props'] })
      setEditingId(null)
    },
  })

  const startEdit = (prop: Prop) => {
    setEditingId(prop.id)
    setEditForm({ category: prop.category, description: prop.description, context: prop.context })
  }

  const saveEdit = (id: number) => {
    updateMutation.mutate({ id, data: editForm })
  }

  // Group props by category
  const grouped = props.reduce((acc, prop) => {
    if (!acc[prop.category]) acc[prop.category] = []
    acc[prop.category].push(prop)
    return acc
  }, {} as Record<string, Prop[]>)

  return (
    <div className="space-y-6">
      {Object.entries(grouped).map(([category, categoryProps]) => (
        <div key={category}>
          <h3 className="text-lg font-semibold text-white mb-3 capitalize">{category}</h3>
          <div className="grid gap-2">
            {categoryProps.map(prop => (
              <div key={prop.id} className="bg-zinc-900 rounded-lg border border-zinc-800 p-3">
                {editingId === prop.id ? (
                  <div className="space-y-2">
                    <input
                      value={editForm.description || ''}
                      onChange={e => setEditForm({ ...editForm, description: e.target.value })}
                      className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded text-white text-sm"
                      placeholder="Description..."
                    />
                    <select
                      value={editForm.context || 'all'}
                      onChange={e => setEditForm({ ...editForm, context: e.target.value })}
                      className="px-2 py-1 bg-zinc-800 border border-zinc-700 rounded text-white text-sm"
                    >
                      {PROP_CONTEXTS.map(c => (
                        <option key={c} value={c}>{c}</option>
                      ))}
                    </select>
                    <div className="flex gap-2">
                      <button
                        onClick={() => saveEdit(prop.id)}
                        disabled={updateMutation.isPending}
                        className="px-3 py-1 bg-green-600 text-white rounded flex items-center gap-1 text-sm"
                      >
                        <Check className="w-4 h-4" />
                        Save
                      </button>
                      <button
                        onClick={() => setEditingId(null)}
                        className="px-3 py-1 bg-zinc-700 text-white rounded flex items-center gap-1 text-sm"
                      >
                        <X className="w-4 h-4" />
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-white">{prop.description}</span>
                      {prop.context !== 'all' && (
                        <span className="text-xs bg-zinc-700 text-zinc-300 px-2 py-0.5 rounded">{prop.context}</span>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => startEdit(prop)}
                        className="p-1 text-zinc-400 hover:text-white"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => setShowDeleteConfirm(prop.id)}
                        className="p-1 text-zinc-400 hover:text-red-400"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

// =========================================================================
// Characters Tab
// =========================================================================

function CharactersTab({ characters, editingId, setEditingId }: {
  characters: Character[]
  editingId: number | null
  setEditingId: (id: number | null) => void
}) {
  const theme = useThemeClasses()
  const queryClient = useQueryClient()
  const [editForm, setEditForm] = useState<Partial<Character>>({})

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Character> }) =>
      apiPut(`/image-config/characters/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['image-config', 'characters'] })
      setEditingId(null)
    },
  })

  const startEdit = (char: Character) => {
    setEditingId(char.id)
    setEditForm({ appearance: char.appearance, face_details: char.face_details, clothing_rules: char.clothing_rules })
  }

  const saveEdit = (id: number) => {
    updateMutation.mutate({ id, data: editForm })
  }

  return (
    <div className="grid gap-6">
      {characters.map(char => (
        <div key={char.id} className="bg-zinc-900 rounded-lg border border-zinc-800 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              {char.character_type === 'engineer' ? (
                <User className="w-6 h-6 text-amber-400" />
              ) : (
                <Bot className="w-6 h-6 text-cyan-400" />
              )}
              <h3 className="text-xl font-bold text-white capitalize">{char.character_type}</h3>
            </div>
            <button
              onClick={() => editingId === char.id ? setEditingId(null) : startEdit(char)}
              className={clsx(
                "px-3 py-1 rounded flex items-center gap-1 text-sm",
                editingId === char.id ? "bg-zinc-700 text-white" : `bg-gradient-to-r ${theme.gradient} text-white ${theme.gradientHover}`
              )}
            >
              <Edit2 className="w-4 h-4" />
              {editingId === char.id ? 'Cancel' : 'Edit'}
            </button>
          </div>

          {editingId === char.id ? (
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-zinc-400 mb-2">Appearance</label>
                <textarea
                  value={editForm.appearance || ''}
                  onChange={e => setEditForm({ ...editForm, appearance: e.target.value })}
                  className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded text-white text-sm font-mono"
                  rows={8}
                />
              </div>
              <div>
                <label className="block text-sm text-zinc-400 mb-2">Face Details</label>
                <input
                  value={editForm.face_details || ''}
                  onChange={e => setEditForm({ ...editForm, face_details: e.target.value })}
                  className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded text-white text-sm"
                />
              </div>
              {char.character_type === 'engineer' && (
                <div>
                  <label className="block text-sm text-zinc-400 mb-2">Clothing Rules</label>
                  <input
                    value={editForm.clothing_rules || ''}
                    onChange={e => setEditForm({ ...editForm, clothing_rules: e.target.value })}
                    className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded text-white text-sm"
                  />
                </div>
              )}
              <button
                onClick={() => saveEdit(char.id)}
                disabled={updateMutation.isPending}
                className="px-4 py-2 bg-green-600 text-white rounded flex items-center gap-2"
              >
                <Save className="w-4 h-4" />
                Save Changes
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              <div>
                <h4 className="text-sm text-zinc-400 mb-2">Appearance</h4>
                <pre className="text-zinc-300 text-sm whitespace-pre-wrap bg-black rounded p-4 border border-zinc-800">
                  {char.appearance}
                </pre>
              </div>
              {char.face_details && (
                <div>
                  <h4 className="text-sm text-zinc-400 mb-1">Face Details</h4>
                  <p className="text-white text-sm">{char.face_details}</p>
                </div>
              )}
              {char.clothing_rules && (
                <div>
                  <h4 className="text-sm text-zinc-400 mb-1">Clothing Rules</h4>
                  <p className="text-white text-sm">{char.clothing_rules}</p>
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
