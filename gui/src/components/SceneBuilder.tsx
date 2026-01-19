/**
 * SceneBuilder - AI-powered batch scene generation with review.
 */

import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Sparkles, X, Loader2, Save, Plus, Camera, Eye } from 'lucide-react'
import { clsx } from 'clsx'
import { apiPost } from '../api/client'

interface GeneratedScene {
  code: string
  name: string
  description: string
  viewpoint: string
}

interface SceneBuilderProps {
  userId: number
  onClose: () => void
}

const SENTIMENTS = ['SUCCESS', 'FAILURE', 'UNRESOLVED']
const VIEWPOINTS = ['standard', 'close_up', 'wide', 'over_shoulder']
const THEME_SUGGESTIONS = [
  'debugging',
  'deployment',
  'code review',
  'architecture',
  'meeting',
  'deadline',
  'breakthrough',
  'collaboration',
  'late night coding',
  'production incident',
]

export default function SceneBuilder({ userId, onClose }: SceneBuilderProps) {
  const queryClient = useQueryClient()

  // Generation form
  const [sentiment, setSentiment] = useState('SUCCESS')
  const [count, setCount] = useState(5)
  const [themes, setThemes] = useState<string[]>([])
  const [context, setContext] = useState('software')
  const [customTheme, setCustomTheme] = useState('')

  // Generated scenes
  const [generatedScenes, setGeneratedScenes] = useState<GeneratedScene[]>([])
  const [editingIndex, setEditingIndex] = useState<number | null>(null)

  // Preview state
  const [previewScene, setPreviewScene] = useState<GeneratedScene | null>(null)
  const [previewContent, setPreviewContent] = useState<string>('')

  // Generate scenes mutation
  const generateMutation = useMutation({
    mutationFn: () =>
      apiPost<{ scenes: GeneratedScene[] }>('/image-config/scenes/generate', {
        sentiment,
        count,
        themes: themes.length > 0 ? themes : undefined,
        context,
      }),
    onSuccess: (data) => {
      setGeneratedScenes(data.scenes)
    },
  })

  // Save scene mutation
  const saveMutation = useMutation({
    mutationFn: (scene: GeneratedScene) =>
      apiPost(`/image-config/users/${userId}/scenes`, {
        code: scene.code,
        name: scene.name,
        sentiment,
        description: scene.description,
        viewpoint: scene.viewpoint,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['image-config', 'scenes'] })
    },
  })

  // Preview mutation
  const previewMutation = useMutation({
    mutationFn: (scene: GeneratedScene) =>
      apiPost<{ preview: string }>('/image-config/scenes/preview', {
        scene: { ...scene, sentiment },
      }),
    onSuccess: (data) => {
      setPreviewContent(data.preview)
    },
  })

  const addTheme = (theme: string) => {
    if (theme && !themes.includes(theme)) {
      setThemes([...themes, theme])
    }
    setCustomTheme('')
  }

  const removeTheme = (theme: string) => {
    setThemes(themes.filter(t => t !== theme))
  }

  const saveScene = async (scene: GeneratedScene, index: number) => {
    await saveMutation.mutateAsync(scene)
    setGeneratedScenes(prev => prev.filter((_, i) => i !== index))
  }

  const updateScene = (index: number, updates: Partial<GeneratedScene>) => {
    setGeneratedScenes(prev =>
      prev.map((scene, i) => (i === index ? { ...scene, ...updates } : scene))
    )
  }

  const showPreview = (scene: GeneratedScene) => {
    setPreviewScene(scene)
    previewMutation.mutate(scene)
  }

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-zinc-800">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-purple-400" />
            <h2 className="text-lg font-semibold text-white">Scene Builder</h2>
          </div>
          <button onClick={onClose} className="p-2 text-zinc-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {/* Generation Form */}
          {generatedScenes.length === 0 && (
            <div className="space-y-6">
              {/* Sentiment Selection */}
              <div>
                <label className="block text-sm font-medium text-zinc-400 mb-2">
                  Sentiment
                </label>
                <div className="flex gap-2">
                  {SENTIMENTS.map(s => (
                    <button
                      key={s}
                      onClick={() => setSentiment(s)}
                      className={clsx(
                        'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                        sentiment === s
                          ? s === 'SUCCESS'
                            ? 'bg-cyan-600 text-white'
                            : s === 'FAILURE'
                              ? 'bg-red-600 text-white'
                              : 'bg-amber-600 text-white'
                          : 'bg-zinc-800 text-zinc-400 hover:text-white'
                      )}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>

              {/* Context */}
              <div>
                <label className="block text-sm font-medium text-zinc-400 mb-2">
                  Context
                </label>
                <div className="flex gap-2">
                  <button
                    onClick={() => setContext('software')}
                    className={clsx(
                      'px-4 py-2 rounded-lg text-sm',
                      context === 'software'
                        ? 'bg-amber-600 text-white'
                        : 'bg-zinc-800 text-zinc-400 hover:text-white'
                    )}
                  >
                    Software
                  </button>
                  <button
                    onClick={() => setContext('hardware')}
                    className={clsx(
                      'px-4 py-2 rounded-lg text-sm',
                      context === 'hardware'
                        ? 'bg-amber-600 text-white'
                        : 'bg-zinc-800 text-zinc-400 hover:text-white'
                    )}
                  >
                    Hardware
                  </button>
                </div>
              </div>

              {/* Theme Selection */}
              <div>
                <label className="block text-sm font-medium text-zinc-400 mb-2">
                  Themes (optional)
                </label>
                <div className="flex flex-wrap gap-2 mb-2">
                  {themes.map(theme => (
                    <span
                      key={theme}
                      className="flex items-center gap-1 px-3 py-1 bg-purple-600/20 text-purple-400 rounded-lg text-sm"
                    >
                      {theme}
                      <button onClick={() => removeTheme(theme)} className="hover:text-white">
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  ))}
                </div>
                <div className="flex flex-wrap gap-2">
                  {THEME_SUGGESTIONS.filter(t => !themes.includes(t)).map(theme => (
                    <button
                      key={theme}
                      onClick={() => addTheme(theme)}
                      className="px-3 py-1 bg-zinc-800 text-zinc-400 hover:text-white rounded-lg text-sm"
                    >
                      + {theme}
                    </button>
                  ))}
                </div>
                <div className="flex gap-2 mt-2">
                  <input
                    value={customTheme}
                    onChange={(e) => setCustomTheme(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && addTheme(customTheme)}
                    placeholder="Custom theme..."
                    className="flex-1 px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white text-sm"
                  />
                  <button
                    onClick={() => addTheme(customTheme)}
                    disabled={!customTheme}
                    className="px-3 py-2 bg-zinc-700 hover:bg-zinc-600 text-white rounded-lg disabled:opacity-50"
                  >
                    <Plus className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Count */}
              <div>
                <label className="block text-sm font-medium text-zinc-400 mb-2">
                  Number of scenes
                </label>
                <input
                  type="number"
                  value={count}
                  onChange={(e) => setCount(parseInt(e.target.value) || 1)}
                  min={1}
                  max={10}
                  className="w-24 px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white"
                />
              </div>

              {/* Generate Button */}
              <button
                onClick={() => generateMutation.mutate()}
                disabled={generateMutation.isPending}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white rounded-lg font-medium"
              >
                {generateMutation.isPending ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-5 h-5" />
                    Generate Scenes
                  </>
                )}
              </button>
            </div>
          )}

          {/* Generated Scenes */}
          {generatedScenes.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-sm text-zinc-400">
                  {generatedScenes.length} scene{generatedScenes.length > 1 ? 's' : ''} generated
                </p>
                <button
                  onClick={() => setGeneratedScenes([])}
                  className="text-sm text-zinc-400 hover:text-white"
                >
                  Generate more
                </button>
              </div>

              {generatedScenes.map((scene, index) => (
                <div
                  key={index}
                  className="bg-zinc-800 rounded-lg p-4 border border-zinc-700"
                >
                  {editingIndex === index ? (
                    // Edit mode
                    <div className="space-y-3">
                      <div className="grid grid-cols-2 gap-3">
                        <input
                          value={scene.code}
                          onChange={(e) => updateScene(index, { code: e.target.value })}
                          placeholder="Scene code"
                          className="px-3 py-2 bg-zinc-900 border border-zinc-600 rounded text-white text-sm"
                        />
                        <input
                          value={scene.name}
                          onChange={(e) => updateScene(index, { name: e.target.value })}
                          placeholder="Scene name"
                          className="px-3 py-2 bg-zinc-900 border border-zinc-600 rounded text-white text-sm"
                        />
                      </div>
                      <textarea
                        value={scene.description}
                        onChange={(e) => updateScene(index, { description: e.target.value })}
                        placeholder="Scene description"
                        rows={3}
                        className="w-full px-3 py-2 bg-zinc-900 border border-zinc-600 rounded text-white text-sm"
                      />
                      <div className="flex items-center justify-between">
                        <select
                          value={scene.viewpoint}
                          onChange={(e) => updateScene(index, { viewpoint: e.target.value })}
                          className="px-3 py-2 bg-zinc-900 border border-zinc-600 rounded text-white text-sm"
                        >
                          {VIEWPOINTS.map(v => (
                            <option key={v} value={v}>{v}</option>
                          ))}
                        </select>
                        <button
                          onClick={() => setEditingIndex(null)}
                          className="px-3 py-1 bg-zinc-700 text-white rounded text-sm"
                        >
                          Done
                        </button>
                      </div>
                    </div>
                  ) : (
                    // View mode
                    <>
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className={clsx(
                            'px-2 py-1 rounded text-xs font-bold',
                            sentiment === 'SUCCESS' ? 'bg-cyan-600/20 text-cyan-400' :
                            sentiment === 'FAILURE' ? 'bg-red-600/20 text-red-400' :
                            'bg-amber-600/20 text-amber-400'
                          )}>
                            {scene.code}
                          </span>
                          <span className="text-white font-medium">{scene.name}</span>
                          <span className="text-zinc-500 text-sm">[{scene.viewpoint}]</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => showPreview(scene)}
                            className="p-1.5 text-zinc-400 hover:text-purple-400"
                            title="Preview prompt"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => setEditingIndex(index)}
                            className="p-1.5 text-zinc-400 hover:text-white"
                            title="Edit"
                          >
                            <Camera className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => saveScene(scene, index)}
                            disabled={saveMutation.isPending}
                            className="flex items-center gap-1 px-3 py-1.5 bg-green-600 hover:bg-green-500 text-white rounded text-sm"
                          >
                            <Save className="w-3 h-3" />
                            Save
                          </button>
                        </div>
                      </div>
                      <p className="text-zinc-400 text-sm">{scene.description}</p>
                    </>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Preview Modal */}
        {previewScene && (
          <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-60">
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg w-full max-w-2xl max-h-[80vh] overflow-hidden">
              <div className="flex items-center justify-between p-4 border-b border-zinc-800">
                <h3 className="font-medium text-white">Prompt Preview: {previewScene.name}</h3>
                <button onClick={() => setPreviewScene(null)} className="p-2 text-zinc-400 hover:text-white">
                  <X className="w-5 h-5" />
                </button>
              </div>
              <div className="p-4 overflow-y-auto max-h-[60vh]">
                {previewMutation.isPending ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="w-6 h-6 animate-spin text-purple-500" />
                  </div>
                ) : (
                  <pre className="text-sm text-zinc-300 whitespace-pre-wrap font-mono bg-zinc-800 p-4 rounded-lg">
                    {previewContent}
                  </pre>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
