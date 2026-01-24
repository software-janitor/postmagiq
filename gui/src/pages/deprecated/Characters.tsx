/**
 * Characters page - Manage characters with templates and AI-powered image analysis.
 */

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Users,
  Plus,
  Trash2,
  Edit,
  Upload,
  Loader2,
  User,
  Bot,
  ChevronRight,
  ChevronLeft,
  Save,
  X,
  Shirt,
  Link2,
  Unlink,
  Check,
} from 'lucide-react'
import { clsx } from 'clsx'
import { useThemeClasses } from '../hooks/useThemeClasses'
import { apiGet, apiPost, apiPut, apiDelete } from '../api/client'
import AIAssistant from '../components/AIAssistant'

// Types
interface CharacterTemplate {
  id: number
  name: string
  description: string | null
  default_parts: string | null
}

interface Character {
  id: number
  user_id: number
  name: string
  template_id: number | null
  description: string | null
  skin_tone: string | null
  face_shape: string | null
  eye_details: string | null
  hair_details: string | null
  facial_hair: string | null
  distinguishing_features: string | null
  physical_traits: string | null
  clothing_rules: string | null
  visible_parts: string | null
}

interface Outfit {
  id: number
  name: string
  description: string | null
}

interface CharacterOutfitLink {
  link_id: number
  is_default: boolean
  outfit: Outfit
}

interface CharacterAnalysisResult {
  template_type: string
  face_details: {
    skin_tone?: string
    face_shape?: string
    eye_details?: string
    hair_details?: string
    facial_hair?: string
    distinguishing_features?: string
  } | null
  physical_traits: {
    body_type?: string
    posture?: string
    height_impression?: string
    materials?: string
    colors?: string
    mechanical_features?: string
    expression_system?: string
    distinctive_elements?: string
  } | null
  outfit: Record<string, string | null> | null
  clothing_rules: string | null
  style_notes: string | null
}

const USER_ID = 1

// Wizard steps
type WizardStep = 'template' | 'input' | 'details' | 'review'

export default function Characters() {
  const theme = useThemeClasses()
  const queryClient = useQueryClient()
  const [showWizard, setShowWizard] = useState(false)
  const [editingCharacter, setEditingCharacter] = useState<Character | null>(null)
  const [selectedCharacter, setSelectedCharacter] = useState<number | null>(null)
  const [showOutfitModal, setShowOutfitModal] = useState(false)

  // Wizard state
  const [wizardStep, setWizardStep] = useState<WizardStep>('template')
  const [selectedTemplate, setSelectedTemplate] = useState<CharacterTemplate | null>(null)
  const [inputMode, setInputMode] = useState<'image' | 'manual'>('manual')
  const [, setAnalysisResult] = useState<CharacterAnalysisResult | null>(null)
  const [characterForm, setCharacterForm] = useState({
    name: '',
    description: '',
    skin_tone: '',
    face_shape: '',
    eye_details: '',
    hair_details: '',
    facial_hair: '',
    distinguishing_features: '',
    physical_traits: '',
    clothing_rules: '',
  })

  // Queries
  const { data: templates } = useQuery({
    queryKey: ['character-templates'],
    queryFn: () => apiGet<{ templates: CharacterTemplate[] }>('/characters/templates'),
  })

  const { data: characters, isLoading: loadingCharacters } = useQuery({
    queryKey: ['characters', USER_ID],
    queryFn: () => apiGet<{ characters: Character[] }>(`/characters/users/${USER_ID}`),
  })

  const { data: outfits } = useQuery({
    queryKey: ['outfits', USER_ID],
    queryFn: () => apiGet<{ outfits: Outfit[] }>(`/characters/outfits/users/${USER_ID}`),
  })

  const { data: characterOutfits } = useQuery({
    queryKey: ['character-outfits', selectedCharacter],
    queryFn: () => apiGet<{ outfits: CharacterOutfitLink[] }>(`/characters/${selectedCharacter}/outfits`),
    enabled: !!selectedCharacter,
  })

  // Mutations
  const createCharacter = useMutation({
    mutationFn: (data: Partial<Character>) => apiPost<{ id: number }>(`/characters/users/${USER_ID}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['characters'] })
      resetWizard()
    },
  })

  const updateCharacter = useMutation({
    mutationFn: ({ id, ...data }: Partial<Character> & { id: number }) =>
      apiPut(`/characters/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['characters'] })
      setEditingCharacter(null)
    },
  })

  const deleteCharacter = useMutation({
    mutationFn: (id: number) => apiDelete(`/characters/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['characters'] })
      if (selectedCharacter === editingCharacter?.id) {
        setSelectedCharacter(null)
      }
    },
  })

  const linkOutfit = useMutation({
    mutationFn: ({ characterId, outfitId, isDefault }: { characterId: number; outfitId: number; isDefault: boolean }) =>
      apiPost(`/characters/${characterId}/outfits`, { outfit_id: outfitId, is_default: isDefault }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['character-outfits'] })
    },
  })

  const unlinkOutfit = useMutation({
    mutationFn: ({ characterId, outfitId }: { characterId: number; outfitId: number }) =>
      apiDelete(`/characters/${characterId}/outfits/${outfitId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['character-outfits'] })
    },
  })

  const setDefaultOutfit = useMutation({
    mutationFn: ({ characterId, outfitId }: { characterId: number; outfitId: number }) =>
      apiPost(`/characters/${characterId}/outfits/${outfitId}/set-default`, {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['character-outfits'] })
    },
  })

  const [analyzing, setAnalyzing] = useState(false)

  const analyzeImage = async (file: File) => {
    setAnalyzing(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('template_type', selectedTemplate?.name || 'human_male')

      const response = await fetch(`/api/characters/users/${USER_ID}/analyze-image`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) throw new Error('Analysis failed')
      const result = await response.json() as CharacterAnalysisResult
      setAnalysisResult(result)

      // Populate form with analysis results
      if (result.face_details) {
        setCharacterForm(prev => ({
          ...prev,
          skin_tone: result.face_details?.skin_tone || '',
          face_shape: result.face_details?.face_shape || '',
          eye_details: result.face_details?.eye_details || '',
          hair_details: result.face_details?.hair_details || '',
          facial_hair: result.face_details?.facial_hair || '',
          distinguishing_features: result.face_details?.distinguishing_features || '',
        }))
      }
      if (result.physical_traits) {
        const traits = result.physical_traits
        const traitsStr = Object.entries(traits)
          .filter(([, v]) => v)
          .map(([k, v]) => `${k}: ${v}`)
          .join('; ')
        setCharacterForm(prev => ({
          ...prev,
          physical_traits: traitsStr,
        }))
      }
      if (result.clothing_rules) {
        setCharacterForm(prev => ({
          ...prev,
          clothing_rules: result.clothing_rules || '',
        }))
      }

      setWizardStep('details')
    } catch (error) {
      console.error('Analysis error:', error)
    } finally {
      setAnalyzing(false)
    }
  }

  const resetWizard = () => {
    setShowWizard(false)
    setWizardStep('template')
    setSelectedTemplate(null)
    setInputMode('manual')
    setAnalysisResult(null)
    setCharacterForm({
      name: '',
      description: '',
      skin_tone: '',
      face_shape: '',
      eye_details: '',
      hair_details: '',
      facial_hair: '',
      distinguishing_features: '',
      physical_traits: '',
      clothing_rules: '',
    })
  }

  const handleCreateCharacter = () => {
    createCharacter.mutate({
      name: characterForm.name,
      template_id: selectedTemplate?.id,
      description: characterForm.description || null,
      skin_tone: characterForm.skin_tone || null,
      face_shape: characterForm.face_shape || null,
      eye_details: characterForm.eye_details || null,
      hair_details: characterForm.hair_details || null,
      facial_hair: characterForm.facial_hair || null,
      distinguishing_features: characterForm.distinguishing_features || null,
      physical_traits: characterForm.physical_traits || null,
      clothing_rules: characterForm.clothing_rules || null,
    })
  }

  const getTemplateIcon = (name: string) => {
    if (name.includes('human')) return User
    return Bot
  }

  const isHumanTemplate = (template: CharacterTemplate | null) => {
    return template?.name?.includes('human') ?? true
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Users className={clsx('w-6 h-6', theme.textPrimary)} />
          <h1 className="text-2xl font-bold text-white">Characters</h1>
        </div>
        <button
          onClick={() => setShowWizard(true)}
          className={clsx('flex items-center gap-2 px-4 py-2 text-white rounded-lg transition-colors bg-gradient-to-r', theme.gradient, theme.gradientHover)}
        >
          <Plus className="w-4 h-4" />
          New Character
        </button>
      </div>

      {/* Character List */}
      {loadingCharacters ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className={clsx('w-8 h-8 animate-spin', theme.textPrimary)} />
        </div>
      ) : characters?.characters.length === 0 ? (
        <div className="text-center py-12 text-zinc-500">
          <Users className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>No characters yet. Create your first character!</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {characters?.characters.map(character => {
            const template = templates?.templates.find(t => t.id === character.template_id)
            const Icon = template ? getTemplateIcon(template.name) : User

            return (
              <div
                key={character.id}
                className={clsx(
                  'bg-zinc-900 border rounded-lg p-4 cursor-pointer transition-colors',
                  selectedCharacter === character.id
                    ? theme.border
                    : 'border-zinc-800 hover:border-zinc-700'
                )}
                onClick={() => setSelectedCharacter(character.id)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 bg-zinc-800 rounded-full flex items-center justify-center">
                      <Icon className="w-6 h-6 text-zinc-400" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-white">{character.name}</h3>
                      <p className="text-xs text-zinc-500">
                        {template?.name || 'No template'}
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-1">
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        setEditingCharacter(character)
                      }}
                      className="p-2 text-zinc-400 hover:text-white"
                    >
                      <Edit className="w-4 h-4" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        if (confirm('Delete this character?')) {
                          deleteCharacter.mutate(character.id)
                        }
                      }}
                      className="p-2 text-zinc-400 hover:text-red-400"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {character.description && (
                  <p className="mt-3 text-sm text-zinc-400 line-clamp-2">
                    {character.description}
                  </p>
                )}

                {/* Face details preview */}
                {(character.skin_tone || character.hair_details) && (
                  <div className="mt-3 flex flex-wrap gap-1">
                    {character.skin_tone && (
                      <span className="text-xs bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded">
                        {character.skin_tone}
                      </span>
                    )}
                    {character.hair_details && (
                      <span className="text-xs bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded">
                        {character.hair_details.slice(0, 30)}...
                      </span>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Selected Character Details */}
      {selectedCharacter && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 mt-6">
          {(() => {
            const character = characters?.characters.find(c => c.id === selectedCharacter)
            if (!character) return null
            const template = templates?.templates.find(t => t.id === character.template_id)

            return (
              <>
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-xl font-semibold text-white">{character.name}</h2>
                  <button
                    onClick={() => {
                      setShowOutfitModal(true)
                    }}
                    className="flex items-center gap-2 px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-white rounded-lg text-sm"
                  >
                    <Shirt className="w-4 h-4" />
                    Manage Outfits
                  </button>
                </div>

                <div className="grid grid-cols-2 gap-6">
                  {/* Face Details */}
                  {isHumanTemplate(template ?? null) && (
                    <div>
                      <h3 className="text-sm font-medium text-zinc-400 mb-3">Face Details</h3>
                      <div className="space-y-2">
                        {character.skin_tone && (
                          <div className="text-sm">
                            <span className="text-zinc-500">Skin Tone:</span>{' '}
                            <span className="text-white">{character.skin_tone}</span>
                          </div>
                        )}
                        {character.face_shape && (
                          <div className="text-sm">
                            <span className="text-zinc-500">Face Shape:</span>{' '}
                            <span className="text-white">{character.face_shape}</span>
                          </div>
                        )}
                        {character.eye_details && (
                          <div className="text-sm">
                            <span className="text-zinc-500">Eyes:</span>{' '}
                            <span className="text-white">{character.eye_details}</span>
                          </div>
                        )}
                        {character.hair_details && (
                          <div className="text-sm">
                            <span className="text-zinc-500">Hair:</span>{' '}
                            <span className="text-white">{character.hair_details}</span>
                          </div>
                        )}
                        {character.facial_hair && (
                          <div className="text-sm">
                            <span className="text-zinc-500">Facial Hair:</span>{' '}
                            <span className="text-white">{character.facial_hair}</span>
                          </div>
                        )}
                        {character.distinguishing_features && (
                          <div className="text-sm">
                            <span className="text-zinc-500">Features:</span>{' '}
                            <span className="text-white">{character.distinguishing_features}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Physical Traits */}
                  {character.physical_traits && (
                    <div>
                      <h3 className="text-sm font-medium text-zinc-400 mb-3">Physical Traits</h3>
                      <p className="text-sm text-white">{character.physical_traits}</p>
                    </div>
                  )}

                  {/* Clothing Rules */}
                  {character.clothing_rules && (
                    <div className="col-span-2">
                      <h3 className="text-sm font-medium text-zinc-400 mb-3">Clothing Rules</h3>
                      <p className="text-sm text-white">{character.clothing_rules}</p>
                    </div>
                  )}
                </div>

                {/* Linked Outfits */}
                <div className="mt-6 pt-6 border-t border-zinc-800">
                  <h3 className="text-sm font-medium text-zinc-400 mb-3">Linked Outfits</h3>
                  {characterOutfits?.outfits.length === 0 ? (
                    <p className="text-sm text-zinc-500">No outfits linked yet</p>
                  ) : (
                    <div className="flex flex-wrap gap-2">
                      {characterOutfits?.outfits.map(link => (
                        <div
                          key={link.link_id}
                          className={clsx(
                            'flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm',
                            link.is_default
                              ? clsx(theme.bgMuted, theme.textPrimary, 'border', theme.border)
                              : 'bg-zinc-800 text-zinc-300'
                          )}
                        >
                          <Shirt className="w-3 h-3" />
                          {link.outfit.name}
                          {link.is_default && <span className="text-xs">(default)</span>}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </>
            )
          })()}
        </div>
      )}

      {/* Creation Wizard Modal */}
      {showWizard && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            {/* Wizard Header */}
            <div className="flex items-center justify-between p-4 border-b border-zinc-800">
              <div className="flex items-center gap-4">
                <h2 className="text-lg font-semibold text-white">Create Character</h2>
                <div className="flex gap-1">
                  {(['template', 'input', 'details', 'review'] as WizardStep[]).map((step, i) => (
                    <div
                      key={step}
                      className={clsx(
                        'w-2 h-2 rounded-full',
                        wizardStep === step
                          ? theme.bgActive
                          : i < ['template', 'input', 'details', 'review'].indexOf(wizardStep)
                            ? 'opacity-50'
                            : 'bg-zinc-700'
                      )}
                    />
                  ))}
                </div>
              </div>
              <button onClick={resetWizard} className="p-2 text-zinc-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Step: Template Selection */}
            {wizardStep === 'template' && (
              <div className="p-6">
                <h3 className="text-sm font-medium text-zinc-400 mb-4">Choose a template</h3>
                <div className="grid grid-cols-2 gap-4">
                  {templates?.templates.map(template => {
                    const Icon = getTemplateIcon(template.name)
                    return (
                      <button
                        key={template.id}
                        onClick={() => {
                          setSelectedTemplate(template)
                          setWizardStep('input')
                        }}
                        className={clsx(
                          'p-4 border rounded-lg text-left transition-colors',
                          selectedTemplate?.id === template.id
                            ? clsx(theme.border, theme.bgMuted)
                            : 'border-zinc-700 hover:border-zinc-600'
                        )}
                      >
                        <Icon className="w-8 h-8 text-zinc-400 mb-2" />
                        <h4 className="font-medium text-white">{template.name}</h4>
                        {template.description && (
                          <p className="text-sm text-zinc-500 mt-1">{template.description}</p>
                        )}
                      </button>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Step: Input Mode */}
            {wizardStep === 'input' && (
              <div className="p-6">
                <h3 className="text-sm font-medium text-zinc-400 mb-4">How do you want to define this character?</h3>
                <div className="grid grid-cols-2 gap-4">
                  <button
                    onClick={() => {
                      setInputMode('image')
                    }}
                    className={clsx(
                      'p-6 border rounded-lg text-center transition-colors',
                      inputMode === 'image'
                        ? clsx(theme.border, theme.bgMuted)
                        : 'border-zinc-700 hover:border-zinc-600'
                    )}
                  >
                    <Upload className="w-8 h-8 text-zinc-400 mx-auto mb-2" />
                    <h4 className="font-medium text-white">Upload Image</h4>
                    <p className="text-sm text-zinc-500 mt-1">
                      AI will analyze the image and extract details
                    </p>
                  </button>
                  <button
                    onClick={() => {
                      setInputMode('manual')
                      setWizardStep('details')
                    }}
                    className={clsx(
                      'p-6 border rounded-lg text-center transition-colors',
                      inputMode === 'manual'
                        ? clsx(theme.border, theme.bgMuted)
                        : 'border-zinc-700 hover:border-zinc-600'
                    )}
                  >
                    <Edit className="w-8 h-8 text-zinc-400 mx-auto mb-2" />
                    <h4 className="font-medium text-white">Manual Entry</h4>
                    <p className="text-sm text-zinc-500 mt-1">
                      Describe the character yourself
                    </p>
                  </button>
                </div>

                {inputMode === 'image' && (
                  <div className="mt-6">
                    <label className="block">
                      <div className="flex flex-col items-center justify-center p-8 border-2 border-dashed border-zinc-700 rounded-lg hover:border-zinc-600 cursor-pointer">
                        {analyzing ? (
                          <>
                            <Loader2 className={clsx('w-8 h-8 animate-spin mb-2', theme.textPrimary)} />
                            <span className="text-zinc-400">Analyzing image...</span>
                          </>
                        ) : (
                          <>
                            <Upload className="w-8 h-8 text-zinc-500 mb-2" />
                            <span className="text-zinc-400">Click to upload an image</span>
                            <span className="text-xs text-zinc-600 mt-1">PNG, JPG up to 10MB</span>
                          </>
                        )}
                      </div>
                      <input
                        type="file"
                        accept="image/*"
                        className="hidden"
                        onChange={(e) => {
                          const file = e.target.files?.[0]
                          if (file) analyzeImage(file)
                        }}
                        disabled={analyzing}
                      />
                    </label>
                  </div>
                )}

                <div className="flex justify-between mt-6">
                  <button
                    onClick={() => setWizardStep('template')}
                    className="flex items-center gap-2 px-4 py-2 text-zinc-400 hover:text-white"
                  >
                    <ChevronLeft className="w-4 h-4" />
                    Back
                  </button>
                </div>
              </div>
            )}

            {/* Step: Details */}
            {wizardStep === 'details' && (
              <div className="p-6">
                <h3 className="text-sm font-medium text-zinc-400 mb-4">Character Details</h3>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm text-zinc-400 mb-1">Name *</label>
                    <input
                      value={characterForm.name}
                      onChange={(e) => setCharacterForm(prev => ({ ...prev, name: e.target.value }))}
                      placeholder="e.g., Engineer, Robot Sidekick"
                      className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white"
                    />
                  </div>

                  <div>
                    <label className="block text-sm text-zinc-400 mb-1">Description</label>
                    <textarea
                      value={characterForm.description}
                      onChange={(e) => setCharacterForm(prev => ({ ...prev, description: e.target.value }))}
                      placeholder="Brief description of the character"
                      rows={2}
                      className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white"
                    />
                  </div>

                  {isHumanTemplate(selectedTemplate) && (
                    <>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm text-zinc-400 mb-1">Skin Tone</label>
                          <input
                            value={characterForm.skin_tone}
                            onChange={(e) => setCharacterForm(prev => ({ ...prev, skin_tone: e.target.value }))}
                            placeholder="e.g., warm olive"
                            className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white"
                          />
                        </div>
                        <div>
                          <label className="block text-sm text-zinc-400 mb-1">Face Shape</label>
                          <input
                            value={characterForm.face_shape}
                            onChange={(e) => setCharacterForm(prev => ({ ...prev, face_shape: e.target.value }))}
                            placeholder="e.g., oval, square"
                            className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white"
                          />
                        </div>
                      </div>

                      <div>
                        <label className="block text-sm text-zinc-400 mb-1">Eye Details</label>
                        <input
                          value={characterForm.eye_details}
                          onChange={(e) => setCharacterForm(prev => ({ ...prev, eye_details: e.target.value }))}
                          placeholder="e.g., brown eyes, tired expression"
                          className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white"
                        />
                      </div>

                      <div>
                        <label className="block text-sm text-zinc-400 mb-1">Hair Details</label>
                        <input
                          value={characterForm.hair_details}
                          onChange={(e) => setCharacterForm(prev => ({ ...prev, hair_details: e.target.value }))}
                          placeholder="e.g., short dark hair, graying at temples"
                          className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white"
                        />
                      </div>

                      <div>
                        <label className="block text-sm text-zinc-400 mb-1">Facial Hair</label>
                        <input
                          value={characterForm.facial_hair}
                          onChange={(e) => setCharacterForm(prev => ({ ...prev, facial_hair: e.target.value }))}
                          placeholder="e.g., clean shaven, stubble"
                          className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white"
                        />
                      </div>

                      <div>
                        <label className="block text-sm text-zinc-400 mb-1">Distinguishing Features</label>
                        <input
                          value={characterForm.distinguishing_features}
                          onChange={(e) => setCharacterForm(prev => ({ ...prev, distinguishing_features: e.target.value }))}
                          placeholder="e.g., small scar on chin, freckles"
                          className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white"
                        />
                      </div>
                    </>
                  )}

                  <div>
                    <label className="block text-sm text-zinc-400 mb-1">Physical Traits</label>
                    <textarea
                      value={characterForm.physical_traits}
                      onChange={(e) => setCharacterForm(prev => ({ ...prev, physical_traits: e.target.value }))}
                      placeholder={isHumanTemplate(selectedTemplate)
                        ? "e.g., athletic build, tall, relaxed posture"
                        : "e.g., brushed aluminum body, LED panel eyes, antenna ears"
                      }
                      rows={2}
                      className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white"
                    />
                  </div>

                  <div>
                    <label className="block text-sm text-zinc-400 mb-1">Clothing Rules</label>
                    <textarea
                      value={characterForm.clothing_rules}
                      onChange={(e) => setCharacterForm(prev => ({ ...prev, clothing_rules: e.target.value }))}
                      placeholder="e.g., Vest always buttoned. Shirt collar open. Sleeves rolled to forearms."
                      rows={2}
                      className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white"
                    />
                  </div>
                </div>

                <div className="flex justify-between mt-6">
                  <button
                    onClick={() => setWizardStep('input')}
                    className="flex items-center gap-2 px-4 py-2 text-zinc-400 hover:text-white"
                  >
                    <ChevronLeft className="w-4 h-4" />
                    Back
                  </button>
                  <button
                    onClick={() => setWizardStep('review')}
                    disabled={!characterForm.name}
                    className={clsx('flex items-center gap-2 px-4 py-2 disabled:opacity-50 text-white rounded-lg bg-gradient-to-r', theme.gradient, theme.gradientHover)}
                  >
                    Review
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}

            {/* Step: Review */}
            {wizardStep === 'review' && (
              <div className="p-6">
                <h3 className="text-sm font-medium text-zinc-400 mb-4">Review Character</h3>

                <div className="bg-zinc-800 rounded-lg p-4 space-y-3">
                  <div>
                    <span className="text-zinc-500 text-sm">Name:</span>
                    <span className="text-white ml-2">{characterForm.name}</span>
                  </div>
                  <div>
                    <span className="text-zinc-500 text-sm">Template:</span>
                    <span className="text-white ml-2">{selectedTemplate?.name}</span>
                  </div>
                  {characterForm.description && (
                    <div>
                      <span className="text-zinc-500 text-sm">Description:</span>
                      <span className="text-white ml-2">{characterForm.description}</span>
                    </div>
                  )}
                  {characterForm.skin_tone && (
                    <div>
                      <span className="text-zinc-500 text-sm">Skin Tone:</span>
                      <span className="text-white ml-2">{characterForm.skin_tone}</span>
                    </div>
                  )}
                  {characterForm.hair_details && (
                    <div>
                      <span className="text-zinc-500 text-sm">Hair:</span>
                      <span className="text-white ml-2">{characterForm.hair_details}</span>
                    </div>
                  )}
                  {characterForm.physical_traits && (
                    <div>
                      <span className="text-zinc-500 text-sm">Physical Traits:</span>
                      <span className="text-white ml-2">{characterForm.physical_traits}</span>
                    </div>
                  )}
                  {characterForm.clothing_rules && (
                    <div>
                      <span className="text-zinc-500 text-sm">Clothing Rules:</span>
                      <span className="text-white ml-2">{characterForm.clothing_rules}</span>
                    </div>
                  )}
                </div>

                <div className="flex justify-between mt-6">
                  <button
                    onClick={() => setWizardStep('details')}
                    className="flex items-center gap-2 px-4 py-2 text-zinc-400 hover:text-white"
                  >
                    <ChevronLeft className="w-4 h-4" />
                    Back
                  </button>
                  <button
                    onClick={handleCreateCharacter}
                    disabled={createCharacter.isPending}
                    className={clsx('flex items-center gap-2 px-4 py-2 disabled:opacity-50 text-white rounded-lg bg-gradient-to-r', theme.gradient, theme.gradientHover)}
                  >
                    {createCharacter.isPending ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Save className="w-4 h-4" />
                    )}
                    Create Character
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Edit Character Modal */}
      {editingCharacter && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-4 border-b border-zinc-800">
              <h2 className="text-lg font-semibold text-white">Edit Character</h2>
              <button onClick={() => setEditingCharacter(null)} className="p-2 text-zinc-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm text-zinc-400 mb-1">Name</label>
                <input
                  value={editingCharacter.name}
                  onChange={(e) => setEditingCharacter(prev => prev ? { ...prev, name: e.target.value } : null)}
                  className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white"
                />
              </div>

              <div>
                <label className="block text-sm text-zinc-400 mb-1">Description</label>
                <textarea
                  value={editingCharacter.description || ''}
                  onChange={(e) => setEditingCharacter(prev => prev ? { ...prev, description: e.target.value } : null)}
                  rows={2}
                  className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white"
                />
              </div>

              <div>
                <label className="block text-sm text-zinc-400 mb-1">Clothing Rules</label>
                <textarea
                  value={editingCharacter.clothing_rules || ''}
                  onChange={(e) => setEditingCharacter(prev => prev ? { ...prev, clothing_rules: e.target.value } : null)}
                  rows={2}
                  className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white"
                />
              </div>

              <div className="flex justify-end gap-2 pt-4">
                <button
                  onClick={() => setEditingCharacter(null)}
                  className="px-4 py-2 text-zinc-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  onClick={() => {
                    updateCharacter.mutate({
                      id: editingCharacter.id,
                      name: editingCharacter.name,
                      description: editingCharacter.description,
                      clothing_rules: editingCharacter.clothing_rules,
                    })
                  }}
                  disabled={updateCharacter.isPending}
                  className={clsx('flex items-center gap-2 px-4 py-2 disabled:opacity-50 text-white rounded-lg bg-gradient-to-r', theme.gradient, theme.gradientHover)}
                >
                  {updateCharacter.isPending ? (
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

      {/* Outfit Link Modal */}
      {showOutfitModal && selectedCharacter && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg w-full max-w-lg">
            <div className="flex items-center justify-between p-4 border-b border-zinc-800">
              <h2 className="text-lg font-semibold text-white">Manage Outfits</h2>
              <button onClick={() => setShowOutfitModal(false)} className="p-2 text-zinc-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6">
              <h3 className="text-sm font-medium text-zinc-400 mb-3">Available Outfits</h3>
              {outfits?.outfits.length === 0 ? (
                <p className="text-sm text-zinc-500 py-4 text-center">
                  No outfits available. Create outfits in the Outfit Bank first.
                </p>
              ) : (
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {outfits?.outfits.map(outfit => {
                    const linked = characterOutfits?.outfits.find(o => o.outfit.id === outfit.id)
                    return (
                      <div
                        key={outfit.id}
                        className="flex items-center justify-between p-3 bg-zinc-800 rounded-lg"
                      >
                        <div className="flex items-center gap-3">
                          <Shirt className="w-4 h-4 text-zinc-400" />
                          <div>
                            <span className="text-white">{outfit.name}</span>
                            {linked?.is_default && (
                              <span className={clsx('ml-2 text-xs', theme.textPrimary)}>(default)</span>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {linked ? (
                            <>
                              {!linked.is_default && (
                                <button
                                  onClick={() => setDefaultOutfit.mutate({
                                    characterId: selectedCharacter,
                                    outfitId: outfit.id,
                                  })}
                                  className={clsx('p-1.5 text-zinc-400', theme.borderHover)}
                                  title="Set as default"
                                >
                                  <Check className="w-4 h-4" />
                                </button>
                              )}
                              <button
                                onClick={() => unlinkOutfit.mutate({
                                  characterId: selectedCharacter,
                                  outfitId: outfit.id,
                                })}
                                className="p-1.5 text-zinc-400 hover:text-red-400"
                                title="Unlink"
                              >
                                <Unlink className="w-4 h-4" />
                              </button>
                            </>
                          ) : (
                            <button
                              onClick={() => linkOutfit.mutate({
                                characterId: selectedCharacter,
                                outfitId: outfit.id,
                                isDefault: false,
                              })}
                              className="p-1.5 text-zinc-400 hover:text-green-400"
                              title="Link"
                            >
                              <Link2 className="w-4 h-4" />
                            </button>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* AI Assistant */}
      <AIAssistant context="characters" />
    </div>
  )
}
