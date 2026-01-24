/**
 * OutfitBank page - Manage reusable outfits and outfit parts with AI assistance.
 */

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Shirt,
  Plus,
  Trash2,
  Edit,
  Loader2,
  Save,
  X,
  Sparkles,
  Link2,
  Unlink,
} from 'lucide-react'
import { clsx } from 'clsx'
import { apiGet, apiPost, apiPut, apiDelete } from '../api/client'
import AIAssistant from '../components/AIAssistant'
import { useThemeClasses } from '../hooks/useThemeClasses'
import ThemeIcon from '../components/ThemeIcon'

// Types
interface OutfitPart {
  id: number
  user_id: number
  part_type: string
  name: string
  description: string | null
}

interface Outfit {
  id: number
  user_id: number
  name: string
  description: string | null
  template_id: number | null
}

interface OutfitWithParts {
  outfit: Outfit
  parts: OutfitPart[]
}

interface GeneratedOutfit {
  name: string
  description: string
  parts: Record<string, string | null>
}

interface CharacterTemplate {
  id: number
  name: string
  description: string | null
}

const USER_ID = 1

// Part type categories
const PART_CATEGORIES = {
  'Headwear': ['hat', 'glasses'],
  'Upper Body': ['jacket', 'vest', 'cardigan', 'sweater', 'shirt', 'blouse', 'top'],
  'Neckwear': ['tie', 'scarf', 'necklace'],
  'Lower Body': ['belt', 'pants', 'skirt', 'dress'],
  'Footwear': ['shoes', 'heels', 'boots'],
  'Accessories': ['watch', 'bracelet', 'earrings', 'bag'],
}

const ALL_PART_TYPES = Object.values(PART_CATEGORIES).flat()

// Parts by template type
const PARTS_BY_TEMPLATE: Record<string, string[]> = {
  'human_male': ['shirt', 'vest', 'jacket', 'pants', 'shoes', 'tie', 'watch'],
  'human_female': ['blouse', 'jacket', 'skirt', 'pants', 'heels', 'necklace', 'earrings'],
  'non_human': ['hat', 'glasses', 'scarf'],
}

export default function OutfitBank() {
  const theme = useThemeClasses()
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<'outfits' | 'parts'>('outfits')

  // Outfit state
  const [showOutfitModal, setShowOutfitModal] = useState(false)
  const [editingOutfit, setEditingOutfit] = useState<Outfit | null>(null)
  const [selectedOutfit, setSelectedOutfit] = useState<number | null>(null)
  const [showPartsSelector, setShowPartsSelector] = useState(false)
  const [outfitForm, setOutfitForm] = useState({ name: '', description: '' })

  // Part state
  const [showPartModal, setShowPartModal] = useState(false)
  const [editingPart, setEditingPart] = useState<OutfitPart | null>(null)
  const [partForm, setPartForm] = useState({ part_type: '', name: '', description: '' })
  const [partFilter, setPartFilter] = useState<string | null>(null)

  // AI generation state
  const [showGenerateModal, setShowGenerateModal] = useState(false)
  const [generateForm, setGenerateForm] = useState({
    template_type: 'human_male',
    style: 'professional',
    mood: '',
    count: 3,
  })
  const [generatedOutfits, setGeneratedOutfits] = useState<GeneratedOutfit[]>([])
  const [referenceOutfitIds, setReferenceOutfitIds] = useState<number[]>([])
  const [partsToVary, setPartsToVary] = useState<string[]>([])
  const [keepParts, setKeepParts] = useState<Record<string, string>>({})
  const [showAdvancedOptions, setShowAdvancedOptions] = useState(false)
  // Track disabled parts per generated outfit (index -> set of disabled part types)
  const [disabledParts, setDisabledParts] = useState<Record<number, Set<string>>>({})

  // Queries
  const { data: templates } = useQuery({
    queryKey: ['character-templates'],
    queryFn: () => apiGet<{ templates: CharacterTemplate[] }>('/characters/templates'),
  })

  const { data: outfits, isLoading: loadingOutfits } = useQuery({
    queryKey: ['outfits', USER_ID],
    queryFn: () => apiGet<{ outfits: Outfit[] }>(`/characters/outfits/users/${USER_ID}`),
  })

  const { data: parts, isLoading: loadingParts } = useQuery({
    queryKey: ['outfit-parts', USER_ID],
    queryFn: () => apiGet<{ parts: OutfitPart[] }>(`/characters/outfit-parts/users/${USER_ID}`),
  })

  const { data: outfitWithParts } = useQuery({
    queryKey: ['outfit-with-parts', selectedOutfit],
    queryFn: () => apiGet<OutfitWithParts>(`/characters/outfits/${selectedOutfit}/with-parts`),
    enabled: !!selectedOutfit,
  })

  // Outfit mutations
  const createOutfit = useMutation({
    mutationFn: (data: { name: string; description?: string }) =>
      apiPost<{ id: number }>(`/characters/outfits/users/${USER_ID}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['outfits'] })
      setShowOutfitModal(false)
      setOutfitForm({ name: '', description: '' })
    },
  })

  const updateOutfit = useMutation({
    mutationFn: ({ id, ...data }: { id: number; name?: string; description?: string }) =>
      apiPut(`/characters/outfits/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['outfits'] })
      queryClient.invalidateQueries({ queryKey: ['outfit-with-parts'] })
      setEditingOutfit(null)
    },
  })

  const deleteOutfit = useMutation({
    mutationFn: (id: number) => apiDelete(`/characters/outfits/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['outfits'] })
      if (selectedOutfit) setSelectedOutfit(null)
    },
  })

  const addPartToOutfit = useMutation({
    mutationFn: ({ outfitId, partId }: { outfitId: number; partId: number }) =>
      apiPost(`/characters/outfits/${outfitId}/parts/${partId}`, {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['outfit-with-parts'] })
    },
  })

  const removePartFromOutfit = useMutation({
    mutationFn: ({ outfitId, partId }: { outfitId: number; partId: number }) =>
      apiDelete(`/characters/outfits/${outfitId}/parts/${partId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['outfit-with-parts'] })
    },
  })

  // Part mutations
  const createPart = useMutation({
    mutationFn: (data: { part_type: string; name: string; description?: string }) =>
      apiPost<{ id: number }>(`/characters/outfit-parts/users/${USER_ID}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['outfit-parts'] })
      setShowPartModal(false)
      setPartForm({ part_type: '', name: '', description: '' })
    },
  })

  const updatePart = useMutation({
    mutationFn: ({ id, ...data }: { id: number; part_type?: string; name?: string; description?: string }) =>
      apiPut(`/characters/outfit-parts/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['outfit-parts'] })
      queryClient.invalidateQueries({ queryKey: ['outfit-with-parts'] })
      setEditingPart(null)
    },
  })

  const deletePart = useMutation({
    mutationFn: (id: number) => apiDelete(`/characters/outfit-parts/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['outfit-parts'] })
      queryClient.invalidateQueries({ queryKey: ['outfit-with-parts'] })
    },
  })

  // AI generation mutation
  const generateOutfits = useMutation({
    mutationFn: (data: typeof generateForm & {
      reference_outfit_ids?: number[]
      parts_to_vary?: string[]
      keep_parts?: Record<string, string>
    }) =>
      apiPost<{ outfits: GeneratedOutfit[] }>('/characters/outfits/generate', data),
    onSuccess: (data) => {
      setGeneratedOutfits(data.outfits)
    },
  })

  const suggestPartDescription = useMutation({
    mutationFn: (data: { part_type: string; style_hints?: string; existing_parts?: string[] }) =>
      apiPost<{ suggestions: string[] }>('/characters/outfit-parts/suggest', data),
  })

  // Save generated outfit
  const saveGeneratedOutfit = async (outfit: GeneratedOutfit, outfitIndex: number) => {
    // Get disabled parts for this outfit
    const disabled = disabledParts[outfitIndex] || new Set<string>()

    // First create the outfit
    const result = await apiPost<{ id: number }>(`/characters/outfits/users/${USER_ID}`, {
      name: outfit.name,
      description: outfit.description,
    })
    const outfitId = result.id

    // Then create and link parts (skip disabled ones)
    for (const [partType, description] of Object.entries(outfit.parts)) {
      if (description && !disabled.has(partType)) {
        const partResult = await apiPost<{ id: number }>(`/characters/outfit-parts/users/${USER_ID}`, {
          part_type: partType,
          name: `${outfit.name} ${partType}`,
          description: description,
        })
        await apiPost(`/characters/outfits/${outfitId}/parts/${partResult.id}`, {})
      }
    }

    queryClient.invalidateQueries({ queryKey: ['outfits'] })
    queryClient.invalidateQueries({ queryKey: ['outfit-parts'] })
    setGeneratedOutfits(prev => prev.filter((_, i) => i !== outfitIndex))
    // Clean up disabled parts for removed outfit
    setDisabledParts(prev => {
      const next = { ...prev }
      delete next[outfitIndex]
      return next
    })
  }

  // Toggle a part on/off for a generated outfit
  const toggleGeneratedPart = (outfitIndex: number, partType: string) => {
    setDisabledParts(prev => {
      const current = prev[outfitIndex] || new Set<string>()
      const next = new Set(current)
      if (next.has(partType)) {
        next.delete(partType)
      } else {
        next.add(partType)
      }
      return { ...prev, [outfitIndex]: next }
    })
  }

  // Filter parts by type
  const filteredParts = partFilter
    ? parts?.parts.filter(p => p.part_type === partFilter)
    : parts?.parts

  // Group parts by category
  const partsByCategory = Object.entries(PART_CATEGORIES).map(([category, types]) => ({
    category,
    parts: filteredParts?.filter(p => types.includes(p.part_type)) || [],
  })).filter(c => c.parts.length > 0)

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <ThemeIcon className={clsx("w-6 h-6", theme.textPrimary)} />
          <h1 className="text-2xl font-bold text-white">Outfit Bank</h1>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowGenerateModal(true)}
            className={clsx("flex items-center gap-2 px-4 py-2 text-white rounded-lg transition-colors bg-gradient-to-r", theme.gradient, theme.gradientHover)}
          >
            <Sparkles className="w-4 h-4" />
            Generate with AI
          </button>
          <button
            onClick={() => activeTab === 'outfits' ? setShowOutfitModal(true) : setShowPartModal(true)}
            className={clsx("flex items-center gap-2 px-4 py-2 text-white rounded-lg transition-colors bg-gradient-to-r", theme.gradient, theme.gradientHover)}
          >
            <Plus className="w-4 h-4" />
            {activeTab === 'outfits' ? 'New Outfit' : 'New Part'}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-zinc-800">
        <button
          onClick={() => setActiveTab('outfits')}
          className={clsx(
            'px-4 py-2 text-sm font-medium transition-colors',
            activeTab === 'outfits'
              ? `${theme.textPrimary} border-b-2 ${theme.borderPrimary}`
              : 'text-zinc-400 hover:text-white'
          )}
        >
          Outfits ({outfits?.outfits.length || 0})
        </button>
        <button
          onClick={() => setActiveTab('parts')}
          className={clsx(
            'px-4 py-2 text-sm font-medium transition-colors',
            activeTab === 'parts'
              ? `${theme.textPrimary} border-b-2 ${theme.borderPrimary}`
              : 'text-zinc-400 hover:text-white'
          )}
        >
          Parts ({parts?.parts.length || 0})
        </button>
      </div>

      {/* Outfits Tab */}
      {activeTab === 'outfits' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Outfit List */}
          <div className="lg:col-span-1 space-y-2">
            {loadingOutfits ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className={clsx("w-8 h-8 animate-spin", theme.textPrimary)} />
              </div>
            ) : outfits?.outfits.length === 0 ? (
              <div className="text-center py-12 text-zinc-500">
                <Shirt className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>No outfits yet. Create your first outfit!</p>
              </div>
            ) : (
              outfits?.outfits.map(outfit => (
                <div
                  key={outfit.id}
                  onClick={() => setSelectedOutfit(outfit.id)}
                  className={clsx(
                    'p-4 rounded-lg cursor-pointer transition-colors border',
                    selectedOutfit === outfit.id
                      ? `bg-zinc-800 ${theme.borderPrimary}`
                      : 'bg-zinc-900 border-zinc-800 hover:border-zinc-700'
                  )}
                >
                  <div className="flex items-center justify-between">
                    <h3 className="font-medium text-white">{outfit.name}</h3>
                    <div className="flex gap-1">
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          setEditingOutfit(outfit)
                        }}
                        className="p-1.5 text-zinc-400 hover:text-white"
                      >
                        <Edit className="w-4 h-4" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          if (confirm('Delete this outfit?')) deleteOutfit.mutate(outfit.id)
                        }}
                        className="p-1.5 text-zinc-400 hover:text-red-400"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                  {outfit.description && (
                    <p className="text-sm text-zinc-500 mt-1 line-clamp-2">{outfit.description}</p>
                  )}
                </div>
              ))
            )}
          </div>

          {/* Selected Outfit Details */}
          <div className="lg:col-span-2 bg-zinc-900 border border-zinc-800 rounded-lg p-6">
            {!selectedOutfit ? (
              <div className="text-center py-12 text-zinc-500">
                <Shirt className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>Select an outfit to view details</p>
              </div>
            ) : (
              <>
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-xl font-semibold text-white">
                    {outfitWithParts?.outfit.name}
                  </h2>
                  <button
                    onClick={() => setShowPartsSelector(true)}
                    className="flex items-center gap-2 px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-white rounded-lg text-sm"
                  >
                    <Plus className="w-4 h-4" />
                    Add Parts
                  </button>
                </div>

                {outfitWithParts?.outfit.description && (
                  <p className="text-zinc-400 mb-6">{outfitWithParts.outfit.description}</p>
                )}

                {/* Parts in this outfit */}
                <h3 className="text-sm font-medium text-zinc-400 mb-3">Parts in this outfit</h3>
                {outfitWithParts?.parts.length === 0 ? (
                  <p className="text-sm text-zinc-500">No parts added yet</p>
                ) : (
                  <div className="space-y-2">
                    {outfitWithParts?.parts.map(part => (
                      <div
                        key={part.id}
                        className="flex items-center justify-between p-3 bg-zinc-800 rounded-lg"
                      >
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs bg-zinc-700 text-zinc-300 px-2 py-0.5 rounded">
                              {part.part_type}
                            </span>
                            <span className="text-white">{part.name}</span>
                          </div>
                          {part.description && (
                            <p className="text-sm text-zinc-500 mt-1">{part.description}</p>
                          )}
                        </div>
                        <button
                          onClick={() => removePartFromOutfit.mutate({
                            outfitId: selectedOutfit,
                            partId: part.id,
                          })}
                          className="p-1.5 text-zinc-400 hover:text-red-400"
                        >
                          <Unlink className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}

      {/* Parts Tab */}
      {activeTab === 'parts' && (
        <div className="space-y-6">
          {/* Part Type Filter */}
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setPartFilter(null)}
              className={clsx(
                'px-3 py-1.5 rounded-lg text-sm transition-colors',
                partFilter === null
                  ? `bg-gradient-to-r ${theme.gradient} text-white`
                  : 'bg-zinc-800 text-zinc-400 hover:text-white'
              )}
            >
              All
            </button>
            {ALL_PART_TYPES.map(type => (
              <button
                key={type}
                onClick={() => setPartFilter(type)}
                className={clsx(
                  'px-3 py-1.5 rounded-lg text-sm transition-colors',
                  partFilter === type
                    ? `bg-gradient-to-r ${theme.gradient} text-white`
                    : 'bg-zinc-800 text-zinc-400 hover:text-white'
                )}
              >
                {type}
              </button>
            ))}
          </div>

          {loadingParts ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className={clsx("w-8 h-8 animate-spin", theme.textPrimary)} />
            </div>
          ) : filteredParts?.length === 0 ? (
            <div className="text-center py-12 text-zinc-500">
              <Shirt className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No parts found. Create your first part!</p>
            </div>
          ) : (
            <div className="space-y-6">
              {partsByCategory.map(({ category, parts: categoryParts }) => (
                <div key={category}>
                  <h3 className="text-sm font-medium text-zinc-400 mb-3">{category}</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {categoryParts.map(part => (
                      <div
                        key={part.id}
                        className="bg-zinc-900 border border-zinc-800 rounded-lg p-4"
                      >
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded">
                            {part.part_type}
                          </span>
                          <div className="flex gap-1">
                            <button
                              onClick={() => setEditingPart(part)}
                              className="p-1.5 text-zinc-400 hover:text-white"
                            >
                              <Edit className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => {
                                if (confirm('Delete this part?')) deletePart.mutate(part.id)
                              }}
                              className="p-1.5 text-zinc-400 hover:text-red-400"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                        <h4 className="font-medium text-white">{part.name}</h4>
                        {part.description && (
                          <p className="text-sm text-zinc-500 mt-1 line-clamp-2">{part.description}</p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Create Outfit Modal */}
      {showOutfitModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg w-full max-w-md">
            <div className="flex items-center justify-between p-4 border-b border-zinc-800">
              <h2 className="text-lg font-semibold text-white">New Outfit</h2>
              <button onClick={() => setShowOutfitModal(false)} className="p-2 text-zinc-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm text-zinc-400 mb-1">Name *</label>
                <input
                  value={outfitForm.name}
                  onChange={(e) => setOutfitForm(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="e.g., Conference Speaker"
                  className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white"
                />
              </div>
              <div>
                <label className="block text-sm text-zinc-400 mb-1">Description</label>
                <textarea
                  value={outfitForm.description}
                  onChange={(e) => setOutfitForm(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="Professional but approachable"
                  rows={2}
                  className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white"
                />
              </div>
              <div className="flex justify-end gap-2 pt-4">
                <button
                  onClick={() => setShowOutfitModal(false)}
                  className="px-4 py-2 text-zinc-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  onClick={() => createOutfit.mutate(outfitForm)}
                  disabled={!outfitForm.name || createOutfit.isPending}
                  className={clsx("flex items-center gap-2 px-4 py-2 disabled:opacity-50 text-white rounded-lg bg-gradient-to-r", theme.gradient, theme.gradientHover)}
                >
                  {createOutfit.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                  Create
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Edit Outfit Modal */}
      {editingOutfit && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg w-full max-w-md">
            <div className="flex items-center justify-between p-4 border-b border-zinc-800">
              <h2 className="text-lg font-semibold text-white">Edit Outfit</h2>
              <button onClick={() => setEditingOutfit(null)} className="p-2 text-zinc-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm text-zinc-400 mb-1">Name</label>
                <input
                  value={editingOutfit.name}
                  onChange={(e) => setEditingOutfit(prev => prev ? { ...prev, name: e.target.value } : null)}
                  className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white"
                />
              </div>
              <div>
                <label className="block text-sm text-zinc-400 mb-1">Description</label>
                <textarea
                  value={editingOutfit.description || ''}
                  onChange={(e) => setEditingOutfit(prev => prev ? { ...prev, description: e.target.value } : null)}
                  rows={2}
                  className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white"
                />
              </div>
              <div className="flex justify-end gap-2 pt-4">
                <button onClick={() => setEditingOutfit(null)} className="px-4 py-2 text-zinc-400 hover:text-white">
                  Cancel
                </button>
                <button
                  onClick={() => updateOutfit.mutate({
                    id: editingOutfit.id,
                    name: editingOutfit.name,
                    description: editingOutfit.description || undefined,
                  })}
                  disabled={updateOutfit.isPending}
                  className={clsx("flex items-center gap-2 px-4 py-2 disabled:opacity-50 text-white rounded-lg bg-gradient-to-r", theme.gradient, theme.gradientHover)}
                >
                  {updateOutfit.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                  Save
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Create Part Modal */}
      {showPartModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg w-full max-w-md">
            <div className="flex items-center justify-between p-4 border-b border-zinc-800">
              <h2 className="text-lg font-semibold text-white">New Part</h2>
              <button onClick={() => setShowPartModal(false)} className="p-2 text-zinc-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm text-zinc-400 mb-1">Type *</label>
                <select
                  value={partForm.part_type}
                  onChange={(e) => setPartForm(prev => ({ ...prev, part_type: e.target.value }))}
                  className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white"
                >
                  <option value="">Select type...</option>
                  {Object.entries(PART_CATEGORIES).map(([category, types]) => (
                    <optgroup key={category} label={category}>
                      {types.map(type => (
                        <option key={type} value={type}>{type}</option>
                      ))}
                    </optgroup>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm text-zinc-400 mb-1">Name *</label>
                <input
                  value={partForm.name}
                  onChange={(e) => setPartForm(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="e.g., Navy Wool Vest"
                  className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white"
                />
              </div>
              <div>
                <label className="block text-sm text-zinc-400 mb-1">
                  Description
                  <button
                    onClick={() => {
                      if (partForm.part_type) {
                        suggestPartDescription.mutate({ part_type: partForm.part_type })
                      }
                    }}
                    disabled={!partForm.part_type || suggestPartDescription.isPending}
                    className="ml-2 text-purple-400 hover:text-purple-300 text-xs"
                  >
                    {suggestPartDescription.isPending ? 'Generating...' : 'Get AI suggestions'}
                  </button>
                </label>
                <textarea
                  value={partForm.description}
                  onChange={(e) => setPartForm(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="Detailed description for image generation"
                  rows={3}
                  className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white"
                />
                {suggestPartDescription.data?.suggestions && (
                  <div className="mt-2 space-y-1">
                    {suggestPartDescription.data.suggestions.map((suggestion, i) => (
                      <button
                        key={i}
                        onClick={() => setPartForm(prev => ({ ...prev, description: suggestion }))}
                        className="block w-full text-left text-xs text-zinc-400 hover:text-white p-2 bg-zinc-800 rounded"
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <div className="flex justify-end gap-2 pt-4">
                <button onClick={() => setShowPartModal(false)} className="px-4 py-2 text-zinc-400 hover:text-white">
                  Cancel
                </button>
                <button
                  onClick={() => createPart.mutate(partForm)}
                  disabled={!partForm.part_type || !partForm.name || createPart.isPending}
                  className={clsx("flex items-center gap-2 px-4 py-2 disabled:opacity-50 text-white rounded-lg bg-gradient-to-r", theme.gradient, theme.gradientHover)}
                >
                  {createPart.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                  Create
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Edit Part Modal */}
      {editingPart && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg w-full max-w-md">
            <div className="flex items-center justify-between p-4 border-b border-zinc-800">
              <h2 className="text-lg font-semibold text-white">Edit Part</h2>
              <button onClick={() => setEditingPart(null)} className="p-2 text-zinc-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm text-zinc-400 mb-1">Type</label>
                <select
                  value={editingPart.part_type}
                  onChange={(e) => setEditingPart(prev => prev ? { ...prev, part_type: e.target.value } : null)}
                  className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white"
                >
                  {ALL_PART_TYPES.map(type => (
                    <option key={type} value={type}>{type}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm text-zinc-400 mb-1">Name</label>
                <input
                  value={editingPart.name}
                  onChange={(e) => setEditingPart(prev => prev ? { ...prev, name: e.target.value } : null)}
                  className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white"
                />
              </div>
              <div>
                <label className="block text-sm text-zinc-400 mb-1">Description</label>
                <textarea
                  value={editingPart.description || ''}
                  onChange={(e) => setEditingPart(prev => prev ? { ...prev, description: e.target.value } : null)}
                  rows={3}
                  className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white"
                />
              </div>
              <div className="flex justify-end gap-2 pt-4">
                <button onClick={() => setEditingPart(null)} className="px-4 py-2 text-zinc-400 hover:text-white">
                  Cancel
                </button>
                <button
                  onClick={() => updatePart.mutate({
                    id: editingPart.id,
                    part_type: editingPart.part_type,
                    name: editingPart.name,
                    description: editingPart.description || undefined,
                  })}
                  disabled={updatePart.isPending}
                  className={clsx("flex items-center gap-2 px-4 py-2 disabled:opacity-50 text-white rounded-lg bg-gradient-to-r", theme.gradient, theme.gradientHover)}
                >
                  {updatePart.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                  Save
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Parts Selector Modal (for adding parts to outfit) */}
      {showPartsSelector && selectedOutfit && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg w-full max-w-lg max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between p-4 border-b border-zinc-800">
              <h2 className="text-lg font-semibold text-white">Add Parts to Outfit</h2>
              <button onClick={() => setShowPartsSelector(false)} className="p-2 text-zinc-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6">
              {parts?.parts.length === 0 ? (
                <p className="text-center text-zinc-500 py-8">
                  No parts available. Create parts in the Parts tab first.
                </p>
              ) : (
                <div className="space-y-2">
                  {parts?.parts.map(part => {
                    const isLinked = outfitWithParts?.parts.some(p => p.id === part.id)
                    return (
                      <div
                        key={part.id}
                        className="flex items-center justify-between p-3 bg-zinc-800 rounded-lg"
                      >
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs bg-zinc-700 text-zinc-300 px-2 py-0.5 rounded">
                              {part.part_type}
                            </span>
                            <span className="text-white">{part.name}</span>
                          </div>
                        </div>
                        {isLinked ? (
                          <button
                            onClick={() => removePartFromOutfit.mutate({
                              outfitId: selectedOutfit,
                              partId: part.id,
                            })}
                            className="p-1.5 text-red-400 hover:text-red-300"
                          >
                            <Unlink className="w-4 h-4" />
                          </button>
                        ) : (
                          <button
                            onClick={() => addPartToOutfit.mutate({
                              outfitId: selectedOutfit,
                              partId: part.id,
                            })}
                            className="p-1.5 text-green-400 hover:text-green-300"
                          >
                            <Link2 className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* AI Generate Modal */}
      {showGenerateModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-4 border-b border-zinc-800">
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <Sparkles className={clsx("w-5 h-5", theme.textPrimary)} />
                Generate Outfits with AI
              </h2>
              <button onClick={() => {
                setShowGenerateModal(false)
                setGeneratedOutfits([])
                setReferenceOutfitIds([])
                setPartsToVary([])
                setKeepParts({})
                setShowAdvancedOptions(false)
                setDisabledParts({})
              }} className="p-2 text-zinc-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-6">
              {/* Generation Form */}
              {generatedOutfits.length === 0 && (
                <>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm text-zinc-400 mb-1">Template Type</label>
                      <select
                        value={generateForm.template_type}
                        onChange={(e) => {
                          setGenerateForm(prev => ({ ...prev, template_type: e.target.value }))
                          setPartsToVary([])
                          setKeepParts({})
                        }}
                        className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white"
                      >
                        {templates?.templates.map(t => (
                          <option key={t.id} value={t.name}>{t.name}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm text-zinc-400 mb-1">Style</label>
                      <select
                        value={generateForm.style}
                        onChange={(e) => setGenerateForm(prev => ({ ...prev, style: e.target.value }))}
                        className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white"
                      >
                        <option value="professional">Professional</option>
                        <option value="casual">Casual</option>
                        <option value="creative">Creative</option>
                        <option value="formal">Formal</option>
                      </select>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm text-zinc-400 mb-1">Mood (optional)</label>
                      <input
                        value={generateForm.mood}
                        onChange={(e) => setGenerateForm(prev => ({ ...prev, mood: e.target.value }))}
                        placeholder="e.g., confident, relaxed"
                        className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-zinc-400 mb-1">Count</label>
                      <input
                        type="number"
                        value={generateForm.count}
                        onChange={(e) => setGenerateForm(prev => ({ ...prev, count: parseInt(e.target.value) || 1 }))}
                        min={1}
                        max={5}
                        className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white"
                      />
                    </div>
                  </div>

                  {/* Style Reference Section */}
                  {outfits && outfits.outfits.length > 0 && (
                    <div className="border-t border-zinc-800 pt-4">
                      <label className="block text-sm font-medium text-zinc-400 mb-2">
                        Style Reference (use existing outfits as style guide)
                      </label>
                      <div className="flex flex-wrap gap-2">
                        {outfits.outfits.map(outfit => (
                          <button
                            key={outfit.id}
                            onClick={() => {
                              setReferenceOutfitIds(prev =>
                                prev.includes(outfit.id)
                                  ? prev.filter(id => id !== outfit.id)
                                  : [...prev, outfit.id]
                              )
                            }}
                            className={clsx(
                              'px-3 py-1.5 rounded-lg text-sm transition-colors',
                              referenceOutfitIds.includes(outfit.id)
                                ? `bg-gradient-to-r ${theme.gradient} text-white`
                                : 'bg-zinc-800 text-zinc-400 hover:text-white'
                            )}
                          >
                            {outfit.name}
                          </button>
                        ))}
                      </div>
                      {referenceOutfitIds.length > 0 && (
                        <p className={clsx("text-xs mt-2", theme.textPrimary)}>
                          AI will match the style, colors, and formality of selected outfits
                        </p>
                      )}
                    </div>
                  )}

                  {/* Advanced Options Toggle */}
                  <button
                    onClick={() => setShowAdvancedOptions(!showAdvancedOptions)}
                    className="text-sm text-zinc-400 hover:text-white flex items-center gap-1"
                  >
                    {showAdvancedOptions ? '▼' : '▶'} Advanced: Control which parts to generate
                  </button>

                  {/* Advanced Options */}
                  {showAdvancedOptions && (
                    <div className="space-y-4 bg-zinc-800/50 rounded-lg p-4">
                      {/* Parts to Vary */}
                      <div>
                        <label className="block text-sm text-zinc-400 mb-2">
                          Parts to generate (leave empty for all)
                        </label>
                        <div className="flex flex-wrap gap-2">
                          {(PARTS_BY_TEMPLATE[generateForm.template_type] || PARTS_BY_TEMPLATE['human_male']).map(part => (
                            <button
                              key={part}
                              onClick={() => {
                                setPartsToVary(prev =>
                                  prev.includes(part)
                                    ? prev.filter(p => p !== part)
                                    : [...prev, part]
                                )
                                // Remove from keepParts if adding to vary
                                if (!partsToVary.includes(part)) {
                                  setKeepParts(prev => {
                                    const next = { ...prev }
                                    delete next[part]
                                    return next
                                  })
                                }
                              }}
                              className={clsx(
                                'px-3 py-1 rounded text-sm transition-colors',
                                partsToVary.includes(part)
                                  ? `bg-gradient-to-r ${theme.gradient} text-white`
                                  : 'bg-zinc-700 text-zinc-400 hover:text-white'
                              )}
                            >
                              {part}
                            </button>
                          ))}
                        </div>
                      </div>

                      {/* Keep Parts from Existing */}
                      {parts && parts.parts.length > 0 && (
                        <div>
                          <label className="block text-sm text-zinc-400 mb-2">
                            Keep these parts unchanged (from your library)
                          </label>
                          <div className="space-y-2 max-h-40 overflow-y-auto">
                            {(PARTS_BY_TEMPLATE[generateForm.template_type] || PARTS_BY_TEMPLATE['human_male']).map(partType => {
                              const availableParts = parts.parts.filter(p => p.part_type === partType)
                              if (availableParts.length === 0) return null
                              return (
                                <div key={partType} className="flex items-center gap-2">
                                  <span className="text-xs text-zinc-500 w-16">{partType}:</span>
                                  <select
                                    value={keepParts[partType] || ''}
                                    onChange={(e) => {
                                      if (e.target.value) {
                                        setKeepParts(prev => ({ ...prev, [partType]: e.target.value }))
                                        // Remove from partsToVary if keeping
                                        setPartsToVary(prev => prev.filter(p => p !== partType))
                                      } else {
                                        setKeepParts(prev => {
                                          const next = { ...prev }
                                          delete next[partType]
                                          return next
                                        })
                                      }
                                    }}
                                    className="flex-1 px-2 py-1 bg-zinc-700 border border-zinc-600 rounded text-white text-sm"
                                  >
                                    <option value="">Generate new</option>
                                    {availableParts.map(p => (
                                      <option key={p.id} value={p.description || p.name}>
                                        {p.name}
                                      </option>
                                    ))}
                                  </select>
                                </div>
                              )
                            })}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  <button
                    onClick={() => generateOutfits.mutate({
                      ...generateForm,
                      reference_outfit_ids: referenceOutfitIds.length > 0 ? referenceOutfitIds : undefined,
                      parts_to_vary: partsToVary.length > 0 ? partsToVary : undefined,
                      keep_parts: Object.keys(keepParts).length > 0 ? keepParts : undefined,
                    })}
                    disabled={generateOutfits.isPending}
                    className={clsx("w-full flex items-center justify-center gap-2 px-4 py-3 disabled:opacity-50 text-white rounded-lg bg-gradient-to-r", theme.gradient, theme.gradientHover)}
                  >
                    {generateOutfits.isPending ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Generating...
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-4 h-4" />
                        Generate Outfits
                      </>
                    )}
                  </button>
                </>
              )}

              {/* Generated Results */}
              {generatedOutfits.length > 0 && (
                <div className="space-y-4">
                  <p className="text-sm text-zinc-400">
                    {generatedOutfits.length} outfit{generatedOutfits.length > 1 ? 's' : ''} generated. Click parts to deselect, then save.
                  </p>
                  {generatedOutfits.map((outfit, i) => {
                    const disabled = disabledParts[i] || new Set<string>()
                    const enabledPartsCount = Object.entries(outfit.parts).filter(([part, v]) => v && !disabled.has(part)).length
                    return (
                      <div key={i} className="bg-zinc-800 rounded-lg p-4">
                        <div className="flex items-center justify-between mb-2">
                          <h3 className="font-medium text-white">{outfit.name}</h3>
                          <button
                            onClick={() => saveGeneratedOutfit(outfit, i)}
                            disabled={enabledPartsCount === 0}
                            className="flex items-center gap-1 px-3 py-1.5 bg-green-600 hover:bg-green-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded text-sm"
                          >
                            <Save className="w-3 h-3" />
                            Save ({enabledPartsCount} parts)
                          </button>
                        </div>
                        <p className="text-sm text-zinc-400 mb-3">{outfit.description}</p>
                        <div className="grid grid-cols-2 gap-2 text-sm">
                          {Object.entries(outfit.parts).filter(([, v]) => v).map(([part, desc]) => {
                            const isDisabled = disabled.has(part)
                            return (
                              <button
                                key={part}
                                onClick={() => toggleGeneratedPart(i, part)}
                                className={clsx(
                                  'text-left rounded p-2 transition-all border',
                                  isDisabled
                                    ? 'bg-zinc-900/50 border-zinc-700 opacity-50'
                                    : 'bg-zinc-900 border-transparent hover:border-zinc-600'
                                )}
                              >
                                <div className="flex items-center justify-between">
                                  <span className={clsx('text-zinc-500', isDisabled && 'line-through')}>{part}:</span>
                                  <span className={clsx(
                                    'text-xs px-1.5 py-0.5 rounded',
                                    isDisabled ? 'bg-red-900/50 text-red-400' : 'bg-green-900/50 text-green-400'
                                  )}>
                                    {isDisabled ? 'excluded' : 'included'}
                                  </span>
                                </div>
                                <span className={clsx('text-white', isDisabled && 'line-through opacity-50')}>{desc}</span>
                              </button>
                            )
                          })}
                        </div>
                      </div>
                    )
                  })}
                  <button
                    onClick={() => {
                      setGeneratedOutfits([])
                      setDisabledParts({})
                    }}
                    className="w-full px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white rounded-lg"
                  >
                    Generate More
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* AI Assistant */}
      <AIAssistant context="outfits" />
    </div>
  )
}
