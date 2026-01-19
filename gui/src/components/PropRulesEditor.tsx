/**
 * PropRulesEditor - Configure prop selection rules for scenes and contexts.
 */

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Settings, X, Plus, Trash2, Loader2, CheckSquare, XSquare, Scale } from 'lucide-react'
import { clsx } from 'clsx'
import { apiGet, apiPost, apiPut, apiDelete } from '../api/client'

interface PropCategory {
  id: number
  user_id: number
  name: string
  description: string | null
  context: string
  is_system: boolean
}

interface ScenePropRule {
  id: number
  scene_id: number
  prop_category_id: number | null
  prop_id: number | null
  required: boolean
  excluded: boolean
  max_count: number
}

interface ContextPropRule {
  id: number
  user_id: number
  context: string
  prop_category_id: number
  weight: number
}

interface Scene {
  id: number
  code: string
  name: string
  sentiment: string
}

interface Prop {
  id: number
  category: string
  description: string
  context: string
}

interface PropRulesEditorProps {
  userId: number
  onClose: () => void
}

const CONTEXTS = ['all', 'software', 'hardware']

export default function PropRulesEditor({ userId, onClose }: PropRulesEditorProps) {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<'categories' | 'scene-rules' | 'context-rules'>('categories')
  const [selectedScene, setSelectedScene] = useState<number | null>(null)

  // Editing states
  const [editingCategory, setEditingCategory] = useState<PropCategory | null>(null)
  const [newCategoryName, setNewCategoryName] = useState('')
  const [newCategoryDesc, setNewCategoryDesc] = useState('')
  const [newCategoryContext, setNewCategoryContext] = useState('all')

  // Fetch prop categories
  const { data: categories, isLoading: loadingCategories } = useQuery({
    queryKey: ['prop-categories', userId],
    queryFn: () => apiGet<{ categories: PropCategory[] }>(`/image-config/users/${userId}/prop-categories`),
  })

  // Fetch scenes for scene rules tab
  const { data: scenes } = useQuery({
    queryKey: ['image-config', 'scenes', userId],
    queryFn: () => apiGet<{ scenes: Scene[] }>(`/image-config/users/${userId}/scenes`),
  })

  // Fetch props
  const { data: props } = useQuery({
    queryKey: ['image-config', 'props', userId],
    queryFn: () => apiGet<{ props: Prop[] }>(`/image-config/users/${userId}/props`),
  })

  // Fetch scene-specific rules when a scene is selected
  const { data: sceneRules } = useQuery({
    queryKey: ['scene-prop-rules', selectedScene],
    queryFn: () => apiGet<{ rules: ScenePropRule[] }>(`/image-config/scenes/${selectedScene}/prop-rules`),
    enabled: !!selectedScene,
  })

  // Fetch context rules
  const { data: contextRules } = useQuery({
    queryKey: ['context-prop-rules', userId],
    queryFn: () => apiGet<{ rules: ContextPropRule[] }>(`/image-config/users/${userId}/context-prop-rules`),
  })

  // Category mutations
  const createCategoryMutation = useMutation({
    mutationFn: (data: { name: string; description: string | null; context: string }) =>
      apiPost(`/image-config/users/${userId}/prop-categories`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prop-categories', userId] })
      setNewCategoryName('')
      setNewCategoryDesc('')
      setNewCategoryContext('all')
    },
  })

  const updateCategoryMutation = useMutation({
    mutationFn: (data: { id: number; updates: Record<string, string | undefined> }) =>
      apiPut(`/image-config/prop-categories/${data.id}`, data.updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prop-categories', userId] })
      setEditingCategory(null)
    },
  })

  const deleteCategoryMutation = useMutation({
    mutationFn: (id: number) => apiDelete(`/image-config/prop-categories/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prop-categories', userId] })
    },
  })

  // Scene rule mutations
  const addSceneRuleMutation = useMutation({
    mutationFn: (data: { scene_id: number; prop_category_id?: number; prop_id?: number; required?: boolean; excluded?: boolean; max_count?: number }) =>
      apiPost(`/image-config/scenes/${data.scene_id}/prop-rules`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scene-prop-rules', selectedScene] })
    },
  })

  const removeSceneRuleMutation = useMutation({
    mutationFn: (ruleId: number) => apiDelete(`/image-config/prop-rules/${ruleId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scene-prop-rules', selectedScene] })
    },
  })

  // Context rule mutations
  const setContextRuleMutation = useMutation({
    mutationFn: (data: { context: string; prop_category_id: number; weight: number }) =>
      apiPost(`/image-config/users/${userId}/context-prop-rules`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['context-prop-rules', userId] })
    },
  })

  const removeContextRuleMutation = useMutation({
    mutationFn: (ruleId: number) => apiDelete(`/image-config/context-prop-rules/${ruleId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['context-prop-rules', userId] })
    },
  })

  // Helpers
  const getCategoryName = (id: number | null) =>
    categories?.categories.find(c => c.id === id)?.name || 'Unknown'

  const getPropDesc = (id: number | null) =>
    props?.props.find(p => p.id === id)?.description || 'Unknown prop'

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-zinc-800">
          <div className="flex items-center gap-2">
            <Settings className="w-5 h-5 text-green-400" />
            <h2 className="text-lg font-semibold text-white">Prop Selection Rules</h2>
          </div>
          <button onClick={onClose} className="p-2 text-zinc-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-zinc-800">
          <button
            onClick={() => setActiveTab('categories')}
            className={clsx(
              'px-4 py-3 text-sm font-medium',
              activeTab === 'categories'
                ? 'text-green-400 border-b-2 border-green-400'
                : 'text-zinc-400 hover:text-white'
            )}
          >
            Categories
          </button>
          <button
            onClick={() => setActiveTab('scene-rules')}
            className={clsx(
              'px-4 py-3 text-sm font-medium',
              activeTab === 'scene-rules'
                ? 'text-green-400 border-b-2 border-green-400'
                : 'text-zinc-400 hover:text-white'
            )}
          >
            Scene Rules
          </button>
          <button
            onClick={() => setActiveTab('context-rules')}
            className={clsx(
              'px-4 py-3 text-sm font-medium',
              activeTab === 'context-rules'
                ? 'text-green-400 border-b-2 border-green-400'
                : 'text-zinc-400 hover:text-white'
            )}
          >
            Context Weights
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {/* Categories Tab */}
          {activeTab === 'categories' && (
            <div className="space-y-6">
              {/* Add new category */}
              <div className="bg-zinc-800 rounded-lg p-4">
                <h3 className="text-sm font-medium text-zinc-300 mb-3">Add Category</h3>
                <div className="grid grid-cols-3 gap-3">
                  <input
                    value={newCategoryName}
                    onChange={(e) => setNewCategoryName(e.target.value)}
                    placeholder="Category name"
                    className="px-3 py-2 bg-zinc-900 border border-zinc-700 rounded text-white text-sm"
                  />
                  <input
                    value={newCategoryDesc}
                    onChange={(e) => setNewCategoryDesc(e.target.value)}
                    placeholder="Description (optional)"
                    className="px-3 py-2 bg-zinc-900 border border-zinc-700 rounded text-white text-sm"
                  />
                  <div className="flex gap-2">
                    <select
                      value={newCategoryContext}
                      onChange={(e) => setNewCategoryContext(e.target.value)}
                      className="flex-1 px-3 py-2 bg-zinc-900 border border-zinc-700 rounded text-white text-sm"
                    >
                      {CONTEXTS.map(ctx => (
                        <option key={ctx} value={ctx}>{ctx}</option>
                      ))}
                    </select>
                    <button
                      onClick={() => createCategoryMutation.mutate({
                        name: newCategoryName,
                        description: newCategoryDesc || null,
                        context: newCategoryContext,
                      })}
                      disabled={!newCategoryName || createCategoryMutation.isPending}
                      className="px-3 py-2 bg-green-600 hover:bg-green-500 text-white rounded disabled:opacity-50"
                    >
                      <Plus className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>

              {/* Category list */}
              {loadingCategories ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-green-500" />
                </div>
              ) : (
                <div className="space-y-2">
                  {categories?.categories.map(cat => (
                    <div
                      key={cat.id}
                      className="flex items-center justify-between p-3 bg-zinc-800 rounded-lg"
                    >
                      {editingCategory?.id === cat.id ? (
                        <div className="flex-1 grid grid-cols-3 gap-3">
                          <input
                            value={editingCategory.name}
                            onChange={(e) => setEditingCategory({ ...editingCategory, name: e.target.value })}
                            className="px-3 py-2 bg-zinc-900 border border-zinc-600 rounded text-white text-sm"
                          />
                          <input
                            value={editingCategory.description || ''}
                            onChange={(e) => setEditingCategory({ ...editingCategory, description: e.target.value })}
                            className="px-3 py-2 bg-zinc-900 border border-zinc-600 rounded text-white text-sm"
                          />
                          <div className="flex gap-2">
                            <select
                              value={editingCategory.context}
                              onChange={(e) => setEditingCategory({ ...editingCategory, context: e.target.value })}
                              className="flex-1 px-3 py-2 bg-zinc-900 border border-zinc-600 rounded text-white text-sm"
                            >
                              {CONTEXTS.map(ctx => (
                                <option key={ctx} value={ctx}>{ctx}</option>
                              ))}
                            </select>
                            <button
                              onClick={() => updateCategoryMutation.mutate({
                                id: cat.id,
                                updates: {
                                  name: editingCategory.name,
                                  description: editingCategory.description || undefined,
                                  context: editingCategory.context,
                                },
                              })}
                              className="px-3 py-2 bg-green-600 text-white rounded text-sm"
                            >
                              Save
                            </button>
                            <button
                              onClick={() => setEditingCategory(null)}
                              className="px-3 py-2 bg-zinc-700 text-white rounded text-sm"
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      ) : (
                        <>
                          <div className="flex items-center gap-3">
                            <span className="text-white font-medium">{cat.name}</span>
                            {cat.description && (
                              <span className="text-zinc-500 text-sm">- {cat.description}</span>
                            )}
                            <span className={clsx(
                              'px-2 py-0.5 rounded text-xs',
                              cat.context === 'all' ? 'bg-zinc-700 text-zinc-300' :
                              cat.context === 'software' ? 'bg-blue-600/20 text-blue-400' :
                              'bg-amber-600/20 text-amber-400'
                            )}>
                              {cat.context}
                            </span>
                            {cat.is_system && (
                              <span className="text-xs text-zinc-500">(system)</span>
                            )}
                          </div>
                          <div className="flex items-center gap-2">
                            {!cat.is_system && (
                              <>
                                <button
                                  onClick={() => setEditingCategory(cat)}
                                  className="p-1.5 text-zinc-400 hover:text-white"
                                >
                                  <Settings className="w-4 h-4" />
                                </button>
                                <button
                                  onClick={() => deleteCategoryMutation.mutate(cat.id)}
                                  className="p-1.5 text-zinc-400 hover:text-red-400"
                                >
                                  <Trash2 className="w-4 h-4" />
                                </button>
                              </>
                            )}
                          </div>
                        </>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Scene Rules Tab */}
          {activeTab === 'scene-rules' && (
            <div className="space-y-6">
              {/* Scene selector */}
              <div className="bg-zinc-800 rounded-lg p-4">
                <label className="block text-sm font-medium text-zinc-300 mb-2">
                  Select Scene
                </label>
                <select
                  value={selectedScene || ''}
                  onChange={(e) => setSelectedScene(e.target.value ? Number(e.target.value) : null)}
                  className="w-full px-3 py-2 bg-zinc-900 border border-zinc-700 rounded text-white"
                >
                  <option value="">Choose a scene...</option>
                  {scenes?.scenes.map(scene => (
                    <option key={scene.id} value={scene.id}>
                      [{scene.code}] {scene.name}
                    </option>
                  ))}
                </select>
              </div>

              {selectedScene && (
                <>
                  {/* Add rule */}
                  <div className="bg-zinc-800 rounded-lg p-4">
                    <h3 className="text-sm font-medium text-zinc-300 mb-3">Add Rule</h3>
                    <div className="flex gap-3 mb-3">
                      <select
                        id="new-rule-category"
                        className="flex-1 px-3 py-2 bg-zinc-900 border border-zinc-700 rounded text-white text-sm"
                      >
                        <option value="">Any category</option>
                        {categories?.categories.map(cat => (
                          <option key={cat.id} value={cat.id}>{cat.name}</option>
                        ))}
                      </select>
                      <select
                        id="new-rule-prop"
                        className="flex-1 px-3 py-2 bg-zinc-900 border border-zinc-700 rounded text-white text-sm"
                      >
                        <option value="">Any prop</option>
                        {props?.props.map(prop => (
                          <option key={prop.id} value={prop.id}>[{prop.category}] {prop.description.slice(0, 40)}</option>
                        ))}
                      </select>
                    </div>
                    <div className="flex items-center gap-4">
                      <button
                        onClick={() => {
                          const catEl = document.getElementById('new-rule-category') as HTMLSelectElement
                          const propEl = document.getElementById('new-rule-prop') as HTMLSelectElement
                          addSceneRuleMutation.mutate({
                            scene_id: selectedScene,
                            prop_category_id: catEl.value ? Number(catEl.value) : undefined,
                            prop_id: propEl.value ? Number(propEl.value) : undefined,
                            required: true,
                          })
                        }}
                        className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-500 text-white rounded text-sm"
                      >
                        <CheckSquare className="w-4 h-4" />
                        Add Required
                      </button>
                      <button
                        onClick={() => {
                          const catEl = document.getElementById('new-rule-category') as HTMLSelectElement
                          const propEl = document.getElementById('new-rule-prop') as HTMLSelectElement
                          addSceneRuleMutation.mutate({
                            scene_id: selectedScene,
                            prop_category_id: catEl.value ? Number(catEl.value) : undefined,
                            prop_id: propEl.value ? Number(propEl.value) : undefined,
                            excluded: true,
                          })
                        }}
                        className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded text-sm"
                      >
                        <XSquare className="w-4 h-4" />
                        Add Excluded
                      </button>
                    </div>
                  </div>

                  {/* Existing rules */}
                  <div className="space-y-2">
                    <h3 className="text-sm font-medium text-zinc-400">Current Rules</h3>
                    {sceneRules?.rules.length === 0 ? (
                      <p className="text-sm text-zinc-500 py-4">No rules for this scene</p>
                    ) : (
                      sceneRules?.rules.map(rule => (
                        <div
                          key={rule.id}
                          className="flex items-center justify-between p-3 bg-zinc-800 rounded-lg"
                        >
                          <div className="flex items-center gap-3">
                            <span className={clsx(
                              'px-2 py-1 rounded text-xs font-bold',
                              rule.required ? 'bg-green-600/20 text-green-400' : 'bg-red-600/20 text-red-400'
                            )}>
                              {rule.required ? 'REQUIRED' : 'EXCLUDED'}
                            </span>
                            {rule.prop_category_id && (
                              <span className="text-white">Category: {getCategoryName(rule.prop_category_id)}</span>
                            )}
                            {rule.prop_id && (
                              <span className="text-zinc-400 text-sm">Prop: {getPropDesc(rule.prop_id).slice(0, 50)}</span>
                            )}
                            {rule.max_count > 1 && (
                              <span className="text-zinc-500 text-xs">max: {rule.max_count}</span>
                            )}
                          </div>
                          <button
                            onClick={() => removeSceneRuleMutation.mutate(rule.id)}
                            className="p-1.5 text-zinc-400 hover:text-red-400"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      ))
                    )}
                  </div>
                </>
              )}
            </div>
          )}

          {/* Context Rules Tab */}
          {activeTab === 'context-rules' && (
            <div className="space-y-6">
              <p className="text-sm text-zinc-400">
                Set selection weights for prop categories in different contexts. Higher weight = more likely to be selected.
              </p>

              {['software', 'hardware'].map(ctx => (
                <div key={ctx} className="bg-zinc-800 rounded-lg p-4">
                  <h3 className={clsx(
                    'text-sm font-medium mb-3',
                    ctx === 'software' ? 'text-blue-400' : 'text-amber-400'
                  )}>
                    {ctx.charAt(0).toUpperCase() + ctx.slice(1)} Context
                  </h3>
                  <div className="space-y-2">
                    {categories?.categories.map(cat => {
                      const rule = contextRules?.rules.find(
                        r => r.context === ctx && r.prop_category_id === cat.id
                      )
                      return (
                        <div key={cat.id} className="flex items-center gap-3">
                          <span className="w-32 text-sm text-white truncate">{cat.name}</span>
                          <div className="flex items-center gap-2 flex-1">
                            <Scale className="w-4 h-4 text-zinc-500" />
                            <input
                              type="range"
                              min="0"
                              max="5"
                              value={rule?.weight ?? 1}
                              onChange={(e) => setContextRuleMutation.mutate({
                                context: ctx,
                                prop_category_id: cat.id,
                                weight: Number(e.target.value),
                              })}
                              className="flex-1"
                            />
                            <span className="w-8 text-center text-sm text-zinc-400">
                              {rule?.weight ?? 1}
                            </span>
                          </div>
                          {rule && (
                            <button
                              onClick={() => removeContextRuleMutation.mutate(rule.id)}
                              className="p-1 text-zinc-400 hover:text-red-400"
                              title="Reset to default"
                            >
                              <Trash2 className="w-3 h-3" />
                            </button>
                          )}
                        </div>
                      )
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
