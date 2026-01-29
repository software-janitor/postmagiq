import { useState, useEffect } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  ChevronRight,
  ChevronLeft,
  Mic,
  Upload,
  PenTool,
  Loader2,
  Check,
  Sparkles,
  RefreshCw,
} from 'lucide-react'
import { clsx } from 'clsx'
import {
  fetchVoicePrompts,
  saveSample,
  fetchSampleStatus,
  analyzeVoice,
  fetchWorkspaceVoiceProfile,
  VoicePrompt,
  VoiceProfile,
} from '../api/voice'
import { useWorkspaceStore } from '../stores/workspaceStore'
import AIAssistant from '../components/AIAssistant'

type Mode = 'select' | 'write' | 'upload'
type Step = 'existing' | 'mode' | 'input' | 'analyze' | 'complete'

export default function VoiceLearning() {
  const [step, setStep] = useState<Step>('existing')
  const [mode, setMode] = useState<Mode>('select')
  const workspaceId = useWorkspaceStore((state) => state.currentWorkspaceId)
  const [hasExistingProfile, setHasExistingProfile] = useState(false)

  // Check for existing voice profile
  const { data: existingProfile, isLoading: profileLoading, isError: profileError } = useQuery({
    queryKey: ['existing-voice-profile', workspaceId],
    queryFn: () => fetchWorkspaceVoiceProfile(workspaceId!),
    enabled: !!workspaceId && step === 'existing',
    retry: false,
  })

  // Write mode state
  const [prompts, setPrompts] = useState<VoicePrompt[]>([])
  const [selectedPrompts, setSelectedPrompts] = useState<string[]>([])
  const [currentPromptIndex, setCurrentPromptIndex] = useState(0)
  const [responses, setResponses] = useState<Record<string, string>>({})

  // Upload mode state
  const [uploads, setUploads] = useState<Array<{ title: string; content: string }>>([
    { title: '', content: '' },
  ])

  // Analysis result
  const [profile, setProfile] = useState<VoiceProfile | null>(null)

  // Process existing profile when it loads
  useEffect(() => {
    if (step === 'existing' && !profileLoading) {
      if (profileError) {
        // API returned 404 - no profile exists, go to mode selection
        setStep('mode')
      } else if (existingProfile?.id) {
        setHasExistingProfile(true)
        setProfile(existingProfile)
      } else {
        // No existing profile, go to mode selection
        setStep('mode')
      }
    }
  }, [existingProfile, profileLoading, profileError, step])

  // Queries
  const { data: promptsData } = useQuery({
    queryKey: ['voice-prompts', workspaceId],
    queryFn: () => fetchVoicePrompts(workspaceId!),
    enabled: !!workspaceId,
  })

  const { refetch: refetchStatus } = useQuery({
    queryKey: ['sample-status', workspaceId],
    queryFn: () => fetchSampleStatus(workspaceId!),
    enabled: !!workspaceId,
  })

  useEffect(() => {
    if (promptsData?.prompts) {
      setPrompts(promptsData.prompts)
    }
  }, [promptsData])

  // Mutations
  const saveSampleMutation = useMutation({
    mutationFn: (request: { source_type: 'prompt' | 'upload'; content: string; prompt_id?: string; title?: string }) =>
      saveSample(workspaceId!, request),
    onSuccess: () => {
      refetchStatus()
    },
  })

  const analyzeMutation = useMutation({
    mutationFn: () => analyzeVoice(workspaceId!),
    onSuccess: (data) => {
      const analysis = data.analysis
      setProfile({
        id: data.profile_id,
        workspace_id: workspaceId,
        name: null,
        tone: analysis.tone,
        sentence_patterns: JSON.stringify(analysis.sentence_patterns),
        vocabulary_level: analysis.vocabulary_level,
        signature_phrases: analysis.signature_phrases.join(', '),
        storytelling_style: analysis.storytelling_style,
        emotional_register: analysis.emotional_register,
        is_library: false,
        is_shared: false,
        source_sample_count: 0,
      })
      setStep('complete')
    },
  })

  const handlePromptSelect = (promptId: string) => {
    if (selectedPrompts.includes(promptId)) {
      setSelectedPrompts(selectedPrompts.filter((id) => id !== promptId))
    } else if (selectedPrompts.length < 3) {
      setSelectedPrompts([...selectedPrompts, promptId])
    }
  }

  const handleStartWriting = () => {
    setStep('input')
  }

  const handleResponseChange = (value: string) => {
    const currentPromptId = selectedPrompts[currentPromptIndex]
    setResponses({ ...responses, [currentPromptId]: value })
  }

  const handleNextPrompt = async () => {
    // Save current response
    const currentPromptId = selectedPrompts[currentPromptIndex]

    await saveSampleMutation.mutateAsync({
      source_type: 'prompt',
      content: responses[currentPromptId],
      prompt_id: currentPromptId,
    })

    if (currentPromptIndex < selectedPrompts.length - 1) {
      setCurrentPromptIndex(currentPromptIndex + 1)
    } else {
      setStep('analyze')
    }
  }

  const handleAddUpload = () => {
    setUploads([...uploads, { title: '', content: '' }])
  }

  const handleUploadChange = (
    index: number,
    field: 'title' | 'content',
    value: string
  ) => {
    const newUploads = [...uploads]
    newUploads[index][field] = value
    setUploads(newUploads)
  }

  const handleSaveUploads = async () => {
    for (const upload of uploads) {
      if (upload.content.trim()) {
        await saveSampleMutation.mutateAsync({
          source_type: 'upload',
          content: upload.content,
          title: upload.title || undefined,
        })
      }
    }
    setStep('analyze')
  }

  const getWordCount = (text: string) => text.split(/\s+/).filter(Boolean).length

  // Parse signature_phrases string to array for display
  const parseSignaturePhrases = (phrases: string | null): string[] => {
    if (!phrases) return []
    return phrases.split(',').map(p => p.trim()).filter(Boolean)
  }

  const getTotalUploadWords = () =>
    uploads.reduce((sum, u) => sum + getWordCount(u.content), 0)

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <h1 className="text-2xl font-bold text-white">Voice Learning</h1>

      {/* Step indicator - hide when checking existing profile */}
      {step !== 'existing' && (
        <div className="flex items-center gap-4">
          {['Mode', 'Input', 'Analyze', 'Complete'].map((label, index) => {
            const stepNames: Step[] = ['mode', 'input', 'analyze', 'complete']
            const isActive = stepNames[index] === step
            const isComplete = stepNames.indexOf(step) > index
            return (
              <div key={label} className="flex items-center">
                <div
                  className={clsx(
                    'px-4 py-2 rounded-lg text-sm font-medium',
                    isActive && 'bg-blue-600 text-white',
                    isComplete && 'bg-green-600/20 text-green-400',
                    !isActive && !isComplete && 'bg-slate-800 text-slate-400'
                  )}
                >
                  {label}
                </div>
                {index < 3 && <ChevronRight className="w-5 h-5 text-slate-600 mx-2" />}
              </div>
            )
          })}
        </div>
      )}

      <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
        {/* Loading existing profile */}
        {step === 'existing' && profileLoading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
            <span className="ml-3 text-slate-400">Checking for existing voice profile...</span>
          </div>
        )}

        {/* Existing Profile Display */}
        {step === 'existing' && hasExistingProfile && profile && (
          <div className="space-y-6">
            <div className="text-center">
              <div className="w-16 h-16 bg-green-600 rounded-full flex items-center justify-center mx-auto mb-4">
                <Mic className="w-8 h-8 text-white" />
              </div>
              <h2 className="text-lg font-semibold text-white">
                Your Voice Profile
              </h2>
              <p className="text-slate-400 mt-2">
                We've already analyzed your writing style. Here's your voice profile.
              </p>
            </div>

            {/* Profile Display */}
            <div className="bg-slate-900 rounded-lg p-6 space-y-4">
              {profile.tone && (
                <div>
                  <h3 className="text-blue-400 text-sm font-medium mb-1">Tone</h3>
                  <p className="text-white">{profile.tone}</p>
                </div>
              )}

              {profile.storytelling_style && (
                <div>
                  <h3 className="text-blue-400 text-sm font-medium mb-1">
                    Storytelling Style
                  </h3>
                  <p className="text-white">{profile.storytelling_style}</p>
                </div>
              )}

              {profile.emotional_register && (
                <div>
                  <h3 className="text-blue-400 text-sm font-medium mb-1">
                    Emotional Register
                  </h3>
                  <p className="text-white">{profile.emotional_register}</p>
                </div>
              )}

              {profile.vocabulary_level && (
                <div>
                  <h3 className="text-blue-400 text-sm font-medium mb-1">
                    Vocabulary Level
                  </h3>
                  <p className="text-white">{profile.vocabulary_level}</p>
                </div>
              )}

              {profile.signature_phrases && parseSignaturePhrases(profile.signature_phrases).length > 0 && (
                <div>
                  <h3 className="text-blue-400 text-sm font-medium mb-1">
                    Signature Phrases
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {parseSignaturePhrases(profile.signature_phrases).map((phrase, index) => (
                      <span
                        key={index}
                        className="px-2 py-1 bg-slate-800 rounded text-sm text-slate-300"
                      >
                        "{phrase}"
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="flex gap-4 pt-4">
              <a
                href="/story"
                className="flex-1 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-500 text-center"
              >
                Start Writing Content
              </a>
              <button
                onClick={() => {
                  setHasExistingProfile(false)
                  setProfile(null)
                  setStep('mode')
                }}
                className="px-6 py-3 bg-slate-700 text-white rounded-lg hover:bg-slate-600 flex items-center gap-2"
              >
                <RefreshCw className="w-4 h-4" />
                Update Voice Profile
              </button>
            </div>
          </div>
        )}

        {/* Mode Selection */}
        {step === 'mode' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-semibold text-white mb-2">
                Help Us Learn Your Voice
              </h2>
              <p className="text-slate-400">
                We'll analyze your writing to understand your unique style. Choose how
                you'd like to provide samples.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <button
                onClick={() => {
                  setMode('write')
                }}
                className={clsx(
                  'p-6 rounded-lg border text-left transition-colors',
                  mode === 'write'
                    ? 'bg-blue-600/20 border-blue-500'
                    : 'bg-slate-900 border-slate-600 hover:border-slate-500'
                )}
              >
                <PenTool className="w-8 h-8 text-blue-400 mb-3" />
                <h3 className="text-white font-semibold mb-1">Write New Samples</h3>
                <p className="text-slate-400 text-sm">
                  Answer 3 prompts (~500 words each)
                </p>
              </button>

              <button
                onClick={() => {
                  setMode('upload')
                }}
                className={clsx(
                  'p-6 rounded-lg border text-left transition-colors',
                  mode === 'upload'
                    ? 'bg-blue-600/20 border-blue-500'
                    : 'bg-slate-900 border-slate-600 hover:border-slate-500'
                )}
              >
                <Upload className="w-8 h-8 text-green-400 mb-3" />
                <h3 className="text-white font-semibold mb-1">Upload Existing</h3>
                <p className="text-slate-400 text-sm">
                  Paste blog posts, articles, etc.
                </p>
              </button>
            </div>

            {/* Write Mode: Prompt Selection */}
            {mode === 'write' && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-white font-medium">Select 3 Prompts</h3>
                  <span className="text-slate-400 text-sm">
                    {selectedPrompts.length}/3 selected
                  </span>
                </div>
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {prompts.map((prompt) => (
                    <button
                      key={prompt.id}
                      onClick={() => handlePromptSelect(prompt.id)}
                      className={clsx(
                        'w-full p-4 rounded-lg border text-left transition-colors',
                        selectedPrompts.includes(prompt.id)
                          ? 'bg-blue-600/20 border-blue-500'
                          : 'bg-slate-900 border-slate-700 hover:border-slate-600'
                      )}
                    >
                      <p className="text-white">{prompt.prompt}</p>
                      <p className="text-slate-500 text-sm mt-1">
                        Reveals: {prompt.reveals}
                      </p>
                    </button>
                  ))}
                </div>
                <button
                  onClick={handleStartWriting}
                  disabled={selectedPrompts.length !== 3}
                  className="w-full px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Start Writing
                </button>
              </div>
            )}

            {/* Upload Mode */}
            {mode === 'upload' && (
              <div className="space-y-4">
                <p className="text-slate-400 text-sm">
                  Paste your existing writing. Minimum 1500 words total.
                </p>
                <button
                  onClick={() => setStep('input')}
                  className="w-full px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-500"
                >
                  Continue to Upload
                </button>
              </div>
            )}
          </div>
        )}

        {/* Write Mode Input */}
        {step === 'input' && mode === 'write' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-white">
                Prompt {currentPromptIndex + 1} of {selectedPrompts.length}
              </h2>
              <span className="text-slate-400 text-sm">
                {getWordCount(responses[selectedPrompts[currentPromptIndex]] || '')}/500
                words
              </span>
            </div>

            <div className="p-4 bg-slate-900 rounded-lg">
              <p className="text-white">
                {prompts.find((p) => p.id === selectedPrompts[currentPromptIndex])?.prompt}
              </p>
            </div>

            <textarea
              value={responses[selectedPrompts[currentPromptIndex]] || ''}
              onChange={(e) => handleResponseChange(e.target.value)}
              placeholder="Write your response here... Be natural, write like you're telling a colleague."
              rows={12}
              className="w-full px-4 py-3 bg-slate-900 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
            />

            <div className="flex justify-between">
              <button
                onClick={() =>
                  currentPromptIndex > 0
                    ? setCurrentPromptIndex(currentPromptIndex - 1)
                    : setStep('mode')
                }
                className="px-6 py-2 bg-slate-700 text-white rounded-lg hover:bg-slate-600 flex items-center gap-2"
              >
                <ChevronLeft className="w-4 h-4" /> Back
              </button>
              <button
                onClick={handleNextPrompt}
                disabled={
                  getWordCount(responses[selectedPrompts[currentPromptIndex]] || '') < 50 ||
                  saveSampleMutation.isPending
                }
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-500 disabled:opacity-50 flex items-center gap-2"
              >
                {saveSampleMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Saving...
                  </>
                ) : currentPromptIndex < selectedPrompts.length - 1 ? (
                  <>
                    Next Prompt <ChevronRight className="w-4 h-4" />
                  </>
                ) : (
                  <>
                    Analyze Voice <Sparkles className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* Upload Mode Input */}
        {step === 'input' && mode === 'upload' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-white">Upload Content</h2>
              <span
                className={clsx(
                  'text-sm',
                  getTotalUploadWords() >= 1500 ? 'text-green-400' : 'text-slate-400'
                )}
              >
                {getTotalUploadWords()}/1500 words minimum
              </span>
            </div>

            <div className="space-y-4 max-h-96 overflow-y-auto">
              {uploads.map((upload, index) => (
                <div key={index} className="bg-slate-900 rounded-lg p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400 text-sm">Sample {index + 1}</span>
                    <span className="text-slate-500 text-sm">
                      {getWordCount(upload.content)} words
                    </span>
                  </div>
                  <input
                    type="text"
                    value={upload.title}
                    onChange={(e) => handleUploadChange(index, 'title', e.target.value)}
                    placeholder="Title (optional)"
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-white text-sm focus:outline-none focus:border-blue-500"
                  />
                  <textarea
                    value={upload.content}
                    onChange={(e) => handleUploadChange(index, 'content', e.target.value)}
                    placeholder="Paste your content here..."
                    rows={6}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-white text-sm placeholder-slate-500 focus:outline-none focus:border-blue-500"
                  />
                </div>
              ))}
            </div>

            <button
              onClick={handleAddUpload}
              className="w-full px-4 py-2 bg-slate-700 text-slate-300 rounded-lg hover:bg-slate-600 text-sm"
            >
              + Add Another Sample
            </button>

            <div className="flex justify-between">
              <button
                onClick={() => setStep('mode')}
                className="px-6 py-2 bg-slate-700 text-white rounded-lg hover:bg-slate-600 flex items-center gap-2"
              >
                <ChevronLeft className="w-4 h-4" /> Back
              </button>
              <button
                onClick={handleSaveUploads}
                disabled={getTotalUploadWords() < 500 || saveSampleMutation.isPending}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-500 disabled:opacity-50 flex items-center gap-2"
              >
                {saveSampleMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    Analyze Voice <Sparkles className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* Analyze */}
        {step === 'analyze' && (
          <div className="space-y-6 text-center py-8">
            {analyzeMutation.isPending ? (
              <>
                <div className="w-16 h-16 bg-blue-600/20 rounded-full flex items-center justify-center mx-auto">
                  <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
                </div>
                <h2 className="text-lg font-semibold text-white">
                  Analyzing Your Voice...
                </h2>
                <p className="text-slate-400">
                  Our AI is studying your writing patterns, tone, and style.
                </p>
              </>
            ) : (
              <>
                <div className="w-16 h-16 bg-blue-600/20 rounded-full flex items-center justify-center mx-auto">
                  <Mic className="w-8 h-8 text-blue-400" />
                </div>
                <h2 className="text-lg font-semibold text-white">
                  Ready to Analyze
                </h2>
                <p className="text-slate-400">
                  We've saved your writing samples. Click below to analyze your voice.
                </p>
                <button
                  onClick={() => analyzeMutation.mutate()}
                  className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-500 flex items-center gap-2 mx-auto"
                >
                  <Sparkles className="w-5 h-5" />
                  Analyze My Voice
                </button>
              </>
            )}
          </div>
        )}

        {/* Complete */}
        {step === 'complete' && profile && (
          <div className="space-y-6">
            <div className="text-center">
              <div className="w-16 h-16 bg-green-600 rounded-full flex items-center justify-center mx-auto mb-4">
                <Check className="w-8 h-8 text-white" />
              </div>
              <h2 className="text-lg font-semibold text-white">
                Voice Profile Created!
              </h2>
            </div>

            {/* Profile Display */}
            <div className="bg-slate-900 rounded-lg p-6 space-y-4">
              <div>
                <h3 className="text-blue-400 text-sm font-medium mb-1">Tone</h3>
                <p className="text-white">{profile.tone}</p>
              </div>

              <div>
                <h3 className="text-blue-400 text-sm font-medium mb-1">
                  Storytelling Style
                </h3>
                <p className="text-white">{profile.storytelling_style}</p>
              </div>

              <div>
                <h3 className="text-blue-400 text-sm font-medium mb-1">
                  Emotional Register
                </h3>
                <p className="text-white">{profile.emotional_register}</p>
              </div>

              <div>
                <h3 className="text-blue-400 text-sm font-medium mb-1">
                  Vocabulary Level
                </h3>
                <p className="text-white">{profile.vocabulary_level}</p>
              </div>

              {profile.signature_phrases && parseSignaturePhrases(profile.signature_phrases).length > 0 && (
                <div>
                  <h3 className="text-blue-400 text-sm font-medium mb-1">
                    Signature Phrases
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {parseSignaturePhrases(profile.signature_phrases).map((phrase, index) => (
                      <span
                        key={index}
                        className="px-2 py-1 bg-slate-800 rounded text-sm text-slate-300"
                      >
                        "{phrase}"
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="flex justify-center gap-4">
              <a
                href="/story"
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-500"
              >
                Start Writing Content
              </a>
            </div>
          </div>
        )}
      </div>

      {/* AI Assistant */}
      <AIAssistant context="voice" />
    </div>
  )
}
