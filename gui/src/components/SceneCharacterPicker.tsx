/**
 * SceneCharacterPicker - Select characters for a scene with outfit override options.
 */

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Users, X, Plus, Loader2, Shirt, Check, Trash2 } from 'lucide-react'
import { clsx } from 'clsx'
import { apiGet, apiPost, apiPut, apiDelete } from '../api/client'

interface Character {
  id: number
  name: string
  template_id: number | null
  description: string | null
}

interface Outfit {
  id: number
  name: string
  description: string | null
}

interface SceneCharacter {
  id: number
  scene_id: number
  character_id: number
  outfit_id: number | null
  position: string | null
}

interface CharacterOutfitLink {
  link_id: number
  is_default: boolean
  outfit: Outfit
}

interface SceneCharacterPickerProps {
  sceneId: number
  userId: number
  onClose: () => void
}

export default function SceneCharacterPicker({ sceneId, userId, onClose }: SceneCharacterPickerProps) {
  const queryClient = useQueryClient()
  const [selectedCharacter, setSelectedCharacter] = useState<number | null>(null)

  // Fetch all characters for the user
  const { data: characters } = useQuery({
    queryKey: ['characters', userId],
    queryFn: () => apiGet<{ characters: Character[] }>(`/characters/users/${userId}`),
  })

  // Fetch characters linked to this scene
  const { data: sceneCharacters, isLoading: loadingSceneChars } = useQuery({
    queryKey: ['scene-characters', sceneId],
    queryFn: () => apiGet<{ characters: SceneCharacter[] }>(`/image-config/scenes/${sceneId}/characters`),
  })

  // Fetch outfits for the selected character
  const { data: characterOutfits } = useQuery({
    queryKey: ['character-outfits', selectedCharacter],
    queryFn: () => apiGet<{ outfits: CharacterOutfitLink[] }>(`/characters/${selectedCharacter}/outfits`),
    enabled: !!selectedCharacter,
  })

  // Add character to scene
  const addCharacterMutation = useMutation({
    mutationFn: (data: { character_id: number; outfit_id?: number; position?: string }) =>
      apiPost(`/image-config/scenes/${sceneId}/characters`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scene-characters', sceneId] })
    },
  })

  // Update character in scene
  const updateCharacterMutation = useMutation({
    mutationFn: (data: { character_id: number; outfit_id?: number; position?: string }) =>
      apiPut(`/image-config/scenes/${sceneId}/characters/${data.character_id}`, {
        outfit_id: data.outfit_id,
        position: data.position,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scene-characters', sceneId] })
    },
  })

  // Remove character from scene
  const removeCharacterMutation = useMutation({
    mutationFn: (characterId: number) =>
      apiDelete(`/image-config/scenes/${sceneId}/characters/${characterId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scene-characters', sceneId] })
    },
  })

  // Get character by ID
  const getCharacter = (id: number) => characters?.characters.find(c => c.id === id)

  // Check if character is already in scene
  const isInScene = (characterId: number) =>
    sceneCharacters?.characters.some(sc => sc.character_id === characterId)

  // Get scene character link
  const getSceneCharacter = (characterId: number) =>
    sceneCharacters?.characters.find(sc => sc.character_id === characterId)

  // Positions for characters
  const POSITIONS = ['left', 'center', 'right', 'background']

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg w-full max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-zinc-800">
          <div className="flex items-center gap-2">
            <Users className="w-5 h-5 text-amber-400" />
            <h2 className="text-lg font-semibold text-white">Characters in Scene</h2>
          </div>
          <button onClick={onClose} className="p-2 text-zinc-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {loadingSceneChars ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-amber-500" />
            </div>
          ) : (
            <div className="space-y-6">
              {/* Characters currently in scene */}
              <div>
                <h3 className="text-sm font-medium text-zinc-400 mb-3">In this scene</h3>
                {sceneCharacters?.characters.length === 0 ? (
                  <p className="text-sm text-zinc-500 py-4">No characters added yet</p>
                ) : (
                  <div className="space-y-2">
                    {sceneCharacters?.characters.map(sc => {
                      const character = getCharacter(sc.character_id)
                      if (!character) return null

                      return (
                        <div
                          key={sc.id}
                          className="flex items-center justify-between p-3 bg-zinc-800 rounded-lg"
                        >
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 bg-zinc-700 rounded-full flex items-center justify-center">
                              <Users className="w-4 h-4 text-zinc-400" />
                            </div>
                            <div>
                              <div className="text-white font-medium">{character.name}</div>
                              <div className="flex items-center gap-2 text-xs text-zinc-500">
                                {sc.position && (
                                  <span className="bg-zinc-700 px-2 py-0.5 rounded">{sc.position}</span>
                                )}
                                {sc.outfit_id && (
                                  <span className="flex items-center gap-1">
                                    <Shirt className="w-3 h-3" />
                                    Custom outfit
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center gap-2">
                            {/* Position selector */}
                            <select
                              value={sc.position || ''}
                              onChange={(e) => updateCharacterMutation.mutate({
                                character_id: sc.character_id,
                                outfit_id: sc.outfit_id ?? undefined,
                                position: e.target.value || undefined,
                              })}
                              className="px-2 py-1 bg-zinc-700 border border-zinc-600 rounded text-sm text-white"
                            >
                              <option value="">Position...</option>
                              {POSITIONS.map(pos => (
                                <option key={pos} value={pos}>{pos}</option>
                              ))}
                            </select>

                            {/* Outfit override button */}
                            <button
                              onClick={() => setSelectedCharacter(sc.character_id)}
                              className={clsx(
                                'p-2 rounded',
                                sc.outfit_id
                                  ? 'bg-amber-600/20 text-amber-400'
                                  : 'text-zinc-400 hover:text-white'
                              )}
                              title="Set outfit override"
                            >
                              <Shirt className="w-4 h-4" />
                            </button>

                            {/* Remove button */}
                            <button
                              onClick={() => removeCharacterMutation.mutate(sc.character_id)}
                              className="p-2 text-zinc-400 hover:text-red-400"
                              title="Remove from scene"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>

              {/* Available characters to add */}
              <div>
                <h3 className="text-sm font-medium text-zinc-400 mb-3">Add character</h3>
                {characters?.characters.length === 0 ? (
                  <p className="text-sm text-zinc-500">
                    No characters available. Create characters first.
                  </p>
                ) : (
                  <div className="grid grid-cols-2 gap-2">
                    {characters?.characters
                      .filter(c => !isInScene(c.id))
                      .map(character => (
                        <button
                          key={character.id}
                          onClick={() => addCharacterMutation.mutate({ character_id: character.id })}
                          disabled={addCharacterMutation.isPending}
                          className="flex items-center gap-2 p-3 bg-zinc-800 hover:bg-zinc-700 rounded-lg text-left transition-colors"
                        >
                          <div className="w-8 h-8 bg-zinc-700 rounded-full flex items-center justify-center">
                            <Users className="w-4 h-4 text-zinc-400" />
                          </div>
                          <div>
                            <div className="text-white text-sm">{character.name}</div>
                            {character.description && (
                              <div className="text-xs text-zinc-500 truncate max-w-[150px]">
                                {character.description}
                              </div>
                            )}
                          </div>
                          <Plus className="w-4 h-4 text-zinc-400 ml-auto" />
                        </button>
                      ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Outfit override modal */}
        {selectedCharacter && (
          <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-60">
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg w-full max-w-md">
              <div className="flex items-center justify-between p-4 border-b border-zinc-800">
                <h3 className="font-medium text-white">
                  Outfit for {getCharacter(selectedCharacter)?.name}
                </h3>
                <button onClick={() => setSelectedCharacter(null)} className="p-2 text-zinc-400 hover:text-white">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="p-4 space-y-2">
                {/* Use default option */}
                <button
                  onClick={() => {
                    const sc = getSceneCharacter(selectedCharacter)
                    if (sc) {
                      updateCharacterMutation.mutate({
                        character_id: selectedCharacter,
                        position: sc.position ?? undefined,
                      })
                    }
                    setSelectedCharacter(null)
                  }}
                  className="w-full flex items-center justify-between p-3 bg-zinc-800 hover:bg-zinc-700 rounded-lg"
                >
                  <span className="text-white">Use default outfit</span>
                  {!getSceneCharacter(selectedCharacter)?.outfit_id && (
                    <Check className="w-4 h-4 text-green-400" />
                  )}
                </button>

                {/* Available outfits */}
                {characterOutfits?.outfits.map(link => (
                  <button
                    key={link.link_id}
                    onClick={() => {
                      const sc = getSceneCharacter(selectedCharacter)
                      updateCharacterMutation.mutate({
                        character_id: selectedCharacter,
                        outfit_id: link.outfit.id,
                        position: sc?.position ?? undefined,
                      })
                      setSelectedCharacter(null)
                    }}
                    className="w-full flex items-center justify-between p-3 bg-zinc-800 hover:bg-zinc-700 rounded-lg"
                  >
                    <div className="flex items-center gap-2">
                      <Shirt className="w-4 h-4 text-zinc-400" />
                      <span className="text-white">{link.outfit.name}</span>
                      {link.is_default && (
                        <span className="text-xs text-zinc-500">(default)</span>
                      )}
                    </div>
                    {getSceneCharacter(selectedCharacter)?.outfit_id === link.outfit.id && (
                      <Check className="w-4 h-4 text-green-400" />
                    )}
                  </button>
                ))}

                {characterOutfits?.outfits.length === 0 && (
                  <p className="text-sm text-zinc-500 text-center py-4">
                    No outfits linked to this character. Link outfits in the Characters page.
                  </p>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
