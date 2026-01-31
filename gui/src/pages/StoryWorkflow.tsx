import { useState, useEffect, useRef, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ChevronRight,
  ChevronLeft,
  FileText,
  Wand2,
  Check,
  Loader2,
  BookOpen,
  Target,
  Lightbulb,
  AlertCircle,
  CheckCircle2,
  Circle,
  Zap,
  Pause,
  PlayCircle,
  Square,
  Mic,
  Youtube,
  Upload,
  Lock,
  Crown
} from 'lucide-react'
import { fetchAvailablePosts, PostMetadata } from '../api/posts'
import { getLatestRunForStory, getWorkflowStates, startWorkflow } from '../api/workflow'
import { apiPatch } from '../api/client'
import { clsx } from 'clsx'
import { useThemeClasses } from '../hooks/useThemeClasses'
import { useWorkflowStore } from '../stores/workflowStore'
import { useWorkspaceStore } from '../stores/workspaceStore'
import { useEffectiveFlags } from '../stores/flagsStore'
import { useWebSocket } from '../hooks/useWebSocket'
import { pauseWorkflow, resumeWorkflow, abortWorkflow, submitApproval } from '../api/workflow'
import { Send, MessageCircle, XCircle } from 'lucide-react'
import { transcribeAudio, transcribeYouTube, getUsageSummary, isPremiumTier, hasFeature, estimateCredits, type CreditEstimate } from '../api/transcription'

type Step = 'select' | 'raw' | 'workflow' | 'complete'

const STEPS: { id: Step; label: string; icon: React.ElementType }[] = [
  { id: 'select', label: 'Select Post', icon: FileText },
  { id: 'raw', label: 'Raw Content', icon: FileText },
  { id: 'workflow', label: 'Generate Post', icon: Wand2 },
  { id: 'complete', label: 'Complete', icon: Check },
]

// Type for workflow state display
interface WorkflowStateDisplay {
  id: string
  label: string
  description: string
  agents?: string[]
  type?: string
}

// Fallback workflow states - will be replaced by API data
const DEFAULT_WORKFLOW_STATES: WorkflowStateDisplay[] = [
  { id: 'start', label: 'Start', description: 'Initialize workflow' },
  { id: 'story-review', label: 'Review', description: 'Review raw story for completeness' },
  { id: 'story-feedback', label: 'Feedback', description: 'Get more details from user' },
  { id: 'story-process', label: 'Processing', description: 'Extract elements, determine shape' },
  { id: 'draft', label: 'Draft', description: 'Generate post drafts' },
  { id: 'cross-audit', label: 'Audit', description: 'Cross-audit all drafts' },
  { id: 'synthesize', label: 'Synthesize', description: 'Combine best elements' },
  { id: 'final-audit', label: 'Final Audit', description: 'Final quality check' },
  { id: 'human-approval', label: 'Approval', description: 'Human review' },
  { id: 'complete', label: 'Complete', description: 'Workflow complete' },
]

// Custom label overrides for state IDs
const STATE_LABEL_OVERRIDES: Record<string, string> = {
  'story-process': 'Story Processing',
}

// Display names for auditors
const AUDITOR_DISPLAY_NAMES: Record<string, string> = {
  'fabrication-auditor': 'Lie Detector',
  'groq-fabrication-auditor': 'Lie Detector',
  'ollama-fabrication-auditor': 'Lie Detector',
  'claude-fabrication-auditor': 'Lie Detector',
  'style-auditor': 'Randy',
  'groq-style-auditor': 'Randy',
  'ollama-style-auditor': 'Randy',
  'claude-style-auditor': 'Randy',
}

// Helper to get auditor display name
function getAuditorDisplayName(agent: string): string {
  return AUDITOR_DISPLAY_NAMES[agent] || agent
}

// Helper to format state id to label
function stateIdToLabel(id: string): string {
  if (STATE_LABEL_OVERRIDES[id]) return STATE_LABEL_OVERRIDES[id]
  return id.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
}

export default function StoryWorkflow() {
  const theme = useThemeClasses()
  const flags = useEffectiveFlags()
  const showInternals = flags.show_internal_workflow
  const [currentStep, setCurrentStep] = useState<Step>('select')
  const [selectedPost, setSelectedPost] = useState<PostMetadata | null>(null)
  const [rawContent, setRawContent] = useState('')
  const [feedbackInput, setFeedbackInput] = useState('')
  const [submittingApproval, setSubmittingApproval] = useState(false)
  const [approvalError, setApprovalError] = useState<string | null>(null)
  const startFreshRef = useRef(false)  // Skip loading existing outputs (ref to avoid race condition)

  // Input method state for raw content step
  type InputMethod = 'type' | 'voice' | 'youtube'
  const [inputMethod, setInputMethod] = useState<InputMethod>('type')
  const [youtubeUrl, setYoutubeUrl] = useState('')
  const [audioFile, setAudioFile] = useState<File | null>(null)
  const [isTranscribing, setIsTranscribing] = useState(false)
  const [transcribeError, setTranscribeError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Live recording state
  const [isRecording, setIsRecording] = useState(false)
  const [recordingDuration, setRecordingDuration] = useState(0)
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])
  const recordingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const [previousRun, setPreviousRun] = useState<{ run_id: string; status: string; final_state: string | null } | null>(null)
  const eventLogRef = useRef<HTMLDivElement>(null)

  // Connect WebSocket for live updates
  useWebSocket()

  // Get workflow state
  const {
    running,
    paused,
    aborted,
    currentState,
    currentStory,
    awaitingApproval,
    approvalContent,
    approvalPrompt,
    auditResults,
    events,
    outputs,
    error: workflowError,
    tokens,
    cost,
    modelMetrics,
    stateMetrics,
    reset: resetWorkflow,
    setOutputs,
  } = useWorkflowStore()

  // Get current workspace for multi-tenant scoping
  const { currentWorkspace } = useWorkspaceStore()

  // Query client for invalidating queries
  const queryClient = useQueryClient()

  // Fetch available posts
  const { data: availablePosts, isLoading: postsLoading } = useQuery({
    queryKey: ['available-posts'],
    queryFn: fetchAvailablePosts,
  })

  // Fetch workflow states from config
  const { data: workflowStatesData } = useQuery({
    queryKey: ['workflow-states'],
    queryFn: getWorkflowStates,
    staleTime: 60000, // Cache for 1 minute
  })

  // Fetch workspace usage to check tier for premium features
  const { data: usageSummary } = useQuery({
    queryKey: ['workspace-usage', currentWorkspace?.id],
    queryFn: () => currentWorkspace ? getUsageSummary(currentWorkspace.id) : Promise.reject('No workspace'),
    enabled: !!currentWorkspace?.id,
    staleTime: 60000, // Cache for 1 minute
  })

  // Feature access based on new tier features
  const hasVoiceTranscription = usageSummary ? hasFeature(usageSummary, 'voice_transcription') : false
  const hasYoutubeTranscription = usageSummary ? hasFeature(usageSummary, 'youtube_transcription') : false
  const hasPremiumWorkflow = usageSummary ? hasFeature(usageSummary, 'premium_workflow') : false

  // Legacy check for backwards compatibility
  const hasPremiumFeatures = usageSummary?.subscription?.tier_slug
    ? isPremiumTier(usageSummary.subscription.tier_slug)
    : false

  // Text limit from tier
  const textLimit = usageSummary?.features?.text_limit || 50000

  // Credits info
  const creditsUsed = usageSummary?.credits?.used || 0
  const creditsLimit = usageSummary?.credits?.limit || 10
  const creditsRemaining = usageSummary?.credits?.remaining || 0
  const tierName = usageSummary?.tier?.name || 'Free Trial'
  const tierSlug = usageSummary?.tier?.slug || 'free'

  // Is this the free tier?
  const isFreeTier = tierSlug === 'free'

  // Build workflow states from API data or use defaults
  const WORKFLOW_STATES = workflowStatesData?.states
    ?.filter(s => s.type !== 'initial' || s.id === 'start') // Keep start but filter other initial states
    ?.filter(s => !['halt'].includes(s.id)) // Filter out halt state
    ?.map(s => ({
      id: s.id,
      label: stateIdToLabel(s.id),
      description: s.description || '',
      agents: s.agents,
      type: s.type,
    })) || DEFAULT_WORKFLOW_STATES

  // Auto-select first post if none selected
  useEffect(() => {
    if (availablePosts && availablePosts.length > 0 && !selectedPost) {
      setSelectedPost(availablePosts[0])
    }
  }, [availablePosts, selectedPost])

  // Auto-scroll event log
  useEffect(() => {
    if (eventLogRef.current) {
      eventLogRef.current.scrollTop = eventLogRef.current.scrollHeight
    }
  }, [events])

  // Restore step and selected post when returning to a running workflow
  useEffect(() => {
    if (running && currentStep === 'select') {
      // Workflow is running, jump to workflow step
      setCurrentStep('workflow')

      // Restore selected post from the running workflow
      if (currentStory && availablePosts) {
        const runningPost = availablePosts.find(p => p.post_id === currentStory)
        if (runningPost) {
          setSelectedPost(runningPost)
        }
      }
    }
  }, [running, currentStep, currentStory, availablePosts])

  // Only reset workflow when explicitly starting fresh from select step
  // (not when component remounts during an active workflow)
  const hasInitializedRef = useRef(false)
  useEffect(() => {
    if (currentStep === 'select' && !running && !hasInitializedRef.current) {
      hasInitializedRef.current = true
      resetWorkflow()
    }
  }, [currentStep, running, resetWorkflow])

  // Load existing outputs from database when post is selected (unless starting fresh)
  useEffect(() => {
    if (!selectedPost) return
    if (startFreshRef.current) {
      startFreshRef.current = false  // Reset flag after skipping
      setPreviousRun(null)
      return
    }

    const loadExistingOutputs = async () => {
      try {
        const response = await getLatestRunForStory(selectedPost.post_id)
        if (response.run && response.outputs) {
          // Store previous run info for resume functionality
          setPreviousRun({
            run_id: response.run.run_id,
            status: response.run.status,
            final_state: response.run.final_state,
          })

          // Map API output types to store output keys
          const mappedOutputs: typeof outputs = {}
          if (response.outputs.review) {
            mappedOutputs.reviewResult = response.outputs.review
          }
          if (response.outputs.processed) {
            mappedOutputs.processedStory = response.outputs.processed
          }
          if (response.outputs.draft) {
            mappedOutputs.drafts = response.outputs.draft
          }
          if (response.outputs.audit) {
            mappedOutputs.audits = response.outputs.audit
          }
          if (response.outputs.final_audit) {
            mappedOutputs.finalAudits = response.outputs.final_audit
          }
          if (response.outputs.final) {
            mappedOutputs.finalPost = response.outputs.final
          }
          setOutputs(mappedOutputs)
        } else {
          setPreviousRun(null)
        }
      } catch (error) {
        console.error('Failed to load existing outputs:', error)
        setPreviousRun(null)
      }
    }

    loadExistingOutputs()
  }, [selectedPost, setOutputs])

  const executeWorkflow = useMutation({
    mutationFn: (data: { story: string; content: string }) =>
      startWorkflow({
        story: data.story,
        content: data.content,
        workspaceId: currentWorkspace?.id,
      }),
  })

  const currentStepIndex = STEPS.findIndex(s => s.id === currentStep)

  const nextStep = () => {
    const next = STEPS[currentStepIndex + 1]
    if (next) setCurrentStep(next.id)
  }

  const prevStep = () => {
    const prev = STEPS[currentStepIndex - 1]
    if (prev) setCurrentStep(prev.id)
  }

  // Handle audio file selection
  const handleFileSelect = useCallback((file: File) => {
    const validTypes = ['audio/mpeg', 'audio/wav', 'audio/mp4', 'audio/m4a', 'audio/webm', 'audio/ogg', 'video/mp4', 'video/webm']
    const validExtensions = ['.mp3', '.wav', '.m4a', '.mp4', '.webm', '.ogg', '.mpeg', '.mpga']
    const ext = '.' + file.name.split('.').pop()?.toLowerCase()

    if (!validTypes.includes(file.type) && !validExtensions.includes(ext)) {
      setTranscribeError('Invalid file type. Supported: MP3, WAV, M4A, MP4, WebM, OGG')
      return
    }

    if (file.size > 25 * 1024 * 1024) {
      setTranscribeError('File too large. Maximum size is 25MB.')
      return
    }

    setAudioFile(file)
    setTranscribeError(null)
  }, [])

  // Handle file drop
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (file) handleFileSelect(file)
  }, [handleFileSelect])

  // Start live recording
  const startRecording = useCallback(async () => {
    try {
      setTranscribeError(null)
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })

      // Determine best supported format
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : MediaRecorder.isTypeSupported('audio/webm')
        ? 'audio/webm'
        : 'audio/mp4'

      const mediaRecorder = new MediaRecorder(stream, { mimeType })
      mediaRecorderRef.current = mediaRecorder
      audioChunksRef.current = []

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }

      mediaRecorder.onstop = () => {
        const blob = new Blob(audioChunksRef.current, { type: mimeType })
        setRecordedBlob(blob)
        // Stop all tracks to release microphone
        stream.getTracks().forEach(track => track.stop())
      }

      mediaRecorder.start(1000) // Collect data every second
      setIsRecording(true)
      setRecordingDuration(0)
      setRecordedBlob(null)
      setAudioFile(null)

      // Start duration timer
      recordingTimerRef.current = setInterval(() => {
        setRecordingDuration(d => d + 1)
      }, 1000)
    } catch (error) {
      if (error instanceof DOMException && error.name === 'NotAllowedError') {
        setTranscribeError('Microphone access denied. Please allow microphone access in your browser settings.')
      } else if (error instanceof DOMException && error.name === 'NotFoundError') {
        setTranscribeError('No microphone found. Please connect a microphone and try again.')
      } else {
        setTranscribeError(error instanceof Error ? error.message : 'Failed to start recording')
      }
    }
  }, [])

  // Stop live recording
  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current)
        recordingTimerRef.current = null
      }
    }
  }, [isRecording])

  // Format duration as mm:ss
  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  // Cleanup recording on unmount
  useEffect(() => {
    return () => {
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current)
      }
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
        mediaRecorderRef.current.stop()
      }
    }
  }, [])

  // Handle transcription
  const handleTranscribe = async () => {
    if (!currentWorkspace) return

    setIsTranscribing(true)
    setTranscribeError(null)

    try {
      let result
      if (inputMethod === 'voice' && (audioFile || recordedBlob)) {
        // Convert recorded blob to File if needed
        const fileToUpload = audioFile || new File(
          [recordedBlob!],
          `recording-${Date.now()}.webm`,
          { type: recordedBlob!.type }
        )
        result = await transcribeAudio(currentWorkspace.id, fileToUpload)
      } else if (inputMethod === 'youtube' && youtubeUrl) {
        result = await transcribeYouTube(currentWorkspace.id, youtubeUrl)
      } else {
        setTranscribeError('Please provide an audio file, recording, or YouTube URL')
        setIsTranscribing(false)
        return
      }

      // Set the transcribed text as raw content
      setRawContent(result.text)
      // Switch to type view so user can edit
      setInputMethod('type')
      // Clear the inputs
      setAudioFile(null)
      setRecordedBlob(null)
      setRecordingDuration(0)
      setYoutubeUrl('')
    } catch (error) {
      setTranscribeError(error instanceof Error ? error.message : 'Transcription failed')
    } finally {
      setIsTranscribing(false)
    }
  }

  const handleStartWorkflow = async () => {
    if (!selectedPost) return
    try {
      await executeWorkflow.mutateAsync({ story: selectedPost.post_id, content: rawContent })
      nextStep()
    } catch (error) {
      console.error('Workflow failed:', error)
    }
  }

  const handlePostSelect = (postId: string) => {
    const post = availablePosts?.find(p => p.post_id === postId)
    if (post) setSelectedPost(post)
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <h1 className="text-2xl font-bold text-white">Create New Story</h1>

      {/* Step Indicator */}
      <div className="flex items-center justify-between">
        {STEPS.map((step, index) => {
          const Icon = step.icon
          const isActive = step.id === currentStep
          const isComplete = index < currentStepIndex

          return (
            <div key={step.id} className="flex items-center">
              <div className={clsx(
                'flex items-center gap-2 px-4 py-2 rounded-lg transition-colors',
                isActive && 'bg-blue-600 text-white',
                isComplete && 'bg-green-600/20 text-green-400',
                !isActive && !isComplete && 'bg-slate-800 text-slate-400'
              )}>
                <Icon className="w-5 h-5" />
                <span className="text-sm font-medium">{step.label}</span>
              </div>
              {index < STEPS.length - 1 && (
                <ChevronRight className="w-5 h-5 text-slate-600 mx-2" />
              )}
            </div>
          )
        })}
      </div>

      {/* Step Content */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
        {currentStep === 'select' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-semibold text-white mb-2">Select Post</h2>
              <p className="text-slate-400">
                Choose the next post to work on from available unfinished posts.
              </p>
            </div>

            {postsLoading ? (
              <div className="flex items-center gap-2 text-slate-400">
                <Loader2 className="w-5 h-5 animate-spin" />
                Loading posts...
              </div>
            ) : availablePosts && availablePosts.length > 0 ? (
              <>
                {/* Post Dropdown */}
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-2">
                    Available Posts
                  </label>
                  <select
                    value={selectedPost?.post_id || ''}
                    onChange={(e) => handlePostSelect(e.target.value)}
                    className="w-full px-4 py-3 bg-slate-900 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
                  >
                    {availablePosts.map((post) => (
                      <option key={post.post_id} value={post.post_id}>
                        Post {post.post_number} (Ch{post.chapter}): {post.topic}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Post Metadata Display */}
                {selectedPost && (
                  <div className="space-y-4">
                    {/* Post Info Cards */}
                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-slate-900 rounded-lg p-4">
                        <div className="flex items-center gap-2 text-blue-400 mb-2">
                          <BookOpen className="w-4 h-4" />
                          <span className="text-sm font-medium">Chapter {selectedPost.chapter}</span>
                        </div>
                        <div className="text-white font-medium">{selectedPost.topic}</div>
                        <div className="text-slate-400 text-sm mt-1">
                          {selectedPost.shape && <span className="mr-3">Shape: {selectedPost.shape}</span>}
                          {selectedPost.cadence && <span>Cadence: {selectedPost.cadence}</span>}
                        </div>
                      </div>

                      <div className="bg-slate-900 rounded-lg p-4">
                        <div className={clsx('flex items-center gap-2 mb-2', theme.textPrimary)}>
                          <Target className="w-4 h-4" />
                          <span className="text-sm font-medium">Enemy</span>
                        </div>
                        <div className="text-slate-300 text-sm">{selectedPost.enemy}</div>
                      </div>
                    </div>

                    {/* Guidance */}
                    <div className="bg-slate-900 rounded-lg p-4">
                      <div className="flex items-center gap-2 text-green-400 mb-3">
                        <Lightbulb className="w-4 h-4" />
                        <span className="text-sm font-medium">Story Guidance</span>
                      </div>
                      <div className="text-slate-300 text-sm whitespace-pre-wrap leading-relaxed">
                        {selectedPost.guidance}
                      </div>
                    </div>

                    {/* Status */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 text-sm">
                        <span className="text-slate-400">Status:</span>
                        <span className={clsx(
                          'px-2 py-1 rounded',
                          selectedPost.status.toLowerCase().includes('ready') && 'bg-green-500/20 text-green-400',
                          selectedPost.status.toLowerCase().includes('not started') && 'bg-slate-700 text-slate-400',
                          selectedPost.status.toLowerCase().includes('needs') && theme.bgMuted,
                          selectedPost.status.toLowerCase().includes('needs') && theme.textPrimary,
                        )}>
                          {selectedPost.status}
                        </span>
                      </div>

                      {/* Previous run actions */}
                      {previousRun && (outputs.drafts || outputs.finalPost || outputs.processedStory) && (
                        <div className="flex gap-2">
                          <button
                            onClick={() => {
                              // Jump to workflow step with existing outputs
                              setCurrentStep('workflow')
                            }}
                            className="px-3 py-1 text-sm bg-green-600/20 text-green-400 border border-green-600/50 rounded hover:bg-green-600/30 transition-colors flex items-center gap-1"
                          >
                            <PlayCircle className="w-4 h-4" />
                            Resume Previous Run
                          </button>
                          <button
                            onClick={() => {
                              startFreshRef.current = true  // Set ref before reset to prevent reload
                              resetWorkflow()
                              setPreviousRun(null)
                              setRawContent('')
                            }}
                            className={clsx('px-3 py-1 text-sm rounded transition-colors', theme.bgMuted, theme.textPrimary, theme.borderHover)}
                          >
                            Start Fresh
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="text-center py-8 text-slate-400">
                No unfinished posts found. All posts are complete!
              </div>
            )}

            <div className="flex justify-end">
              <button
                onClick={nextStep}
                disabled={!selectedPost}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                Next <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {currentStep === 'raw' && (
          <div className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold text-white">Raw Story Content</h2>
              {selectedPost && (
                <p className="text-slate-400 mt-1">
                  Post {selectedPost.post_number}: {selectedPost.topic}
                </p>
              )}
            </div>

            {/* Quick reminder of guidance - only shown when show_internal_workflow flag is true */}
            {showInternals && selectedPost && (
              <div className="bg-slate-900/50 rounded-lg p-3 border border-slate-700">
                <div className="text-xs text-slate-500 uppercase tracking-wide mb-1">Remember</div>
                <div className="text-sm text-slate-400">
                  {selectedPost.shape === 'FULL' && 'Include: failure, misunderstanding, AI amplification, fix, and scar.'}
                  {selectedPost.shape === 'PARTIAL' && 'No resolution needed. End messy.'}
                  {selectedPost.shape === 'OBSERVATION' && 'Just share what you noticed. No lesson required.'}
                  {selectedPost.shape === 'SHORT' && 'One idea, under 200 words.'}
                  {!selectedPost.shape && 'Tell your story with specific details.'}
                </div>
              </div>
            )}

            {/* Input method tabs */}
            <div className="flex gap-1 bg-slate-800 p-1 rounded-lg">
              <button
                onClick={() => setInputMethod('type')}
                className={clsx(
                  'flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors',
                  inputMethod === 'type'
                    ? 'bg-slate-700 text-white'
                    : 'text-slate-400 hover:text-white'
                )}
              >
                <FileText className="w-4 h-4" />
                Type
              </button>
              <button
                onClick={() => hasVoiceTranscription ? setInputMethod('voice') : null}
                disabled={!hasVoiceTranscription}
                className={clsx(
                  'flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors',
                  inputMethod === 'voice'
                    ? 'bg-slate-700 text-white'
                    : hasVoiceTranscription
                      ? 'text-slate-400 hover:text-white'
                      : 'text-slate-600 cursor-not-allowed'
                )}
              >
                {hasVoiceTranscription ? (
                  <Mic className="w-4 h-4" />
                ) : (
                  <Lock className="w-4 h-4" />
                )}
                Voice
                {!hasVoiceTranscription && <Crown className="w-3 h-3 text-amber-500" />}
              </button>
              <button
                onClick={() => hasYoutubeTranscription ? setInputMethod('youtube') : null}
                disabled={!hasYoutubeTranscription}
                className={clsx(
                  'flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors',
                  inputMethod === 'youtube'
                    ? 'bg-slate-700 text-white'
                    : hasYoutubeTranscription
                      ? 'text-slate-400 hover:text-white'
                      : 'text-slate-600 cursor-not-allowed'
                )}
              >
                {hasYoutubeTranscription ? (
                  <Youtube className="w-4 h-4" />
                ) : (
                  <Lock className="w-4 h-4" />
                )}
                YouTube
                {!hasYoutubeTranscription && <Crown className="w-3 h-3 text-amber-500" />}
              </button>
            </div>

            {/* Free trial upgrade banner */}
            {isFreeTier && (
              <div className="flex items-center gap-3 text-sm bg-gradient-to-r from-slate-800/50 to-amber-900/20 border border-amber-700/30 rounded-lg px-4 py-3">
                <Zap className="w-5 h-5 text-amber-500 flex-shrink-0" />
                <div className="flex-1">
                  <span className="text-slate-300">Free Trial: {creditsLimit} credits</span>
                  <span className="text-slate-500 mx-2">•</span>
                  <a href="/settings" className="text-amber-500 hover:text-amber-400 font-medium">
                    Upgrade to Base ($3.50/mo)
                  </a>
                </div>
              </div>
            )}

            {/* Credits and text limit info */}
            <div className="flex items-center justify-between text-sm text-slate-400">
              <div className="flex items-center gap-4">
                <span>
                  {rawContent.length.toLocaleString()} / {textLimit.toLocaleString()} characters
                </span>
                {rawContent.length > textLimit && (
                  <span className="text-red-400 flex items-center gap-1">
                    <AlertCircle className="w-4 h-4" />
                    Over limit
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <span className={clsx(
                  creditsRemaining < 3 ? 'text-amber-400' : 'text-slate-400'
                )}>
                  {creditsRemaining} / {creditsLimit} credits remaining
                </span>
              </div>
            </div>

            {/* Feature locked prompts */}
            {!hasVoiceTranscription && (inputMethod === 'type') && (
              <div className="flex items-center gap-2 text-sm text-slate-400 bg-slate-800/50 rounded-lg px-3 py-2">
                <Crown className="w-4 h-4 text-amber-500" />
                <span>Upgrade to Pro ($10/mo) to unlock Voice transcription</span>
              </div>
            )}

            {/* Type input */}
            {inputMethod === 'type' && (
              <textarea
                value={rawContent}
                onChange={(e) => setRawContent(e.target.value)}
                placeholder="Paste your raw story content here...

What happened? What did you learn? What went wrong?
Include specific details: error messages, tools used, time spent, etc."
                rows={15}
                className="w-full px-4 py-3 bg-slate-900 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 font-mono text-sm"
              />
            )}

            {/* Voice input */}
            {inputMethod === 'voice' && (
              <div className="space-y-4">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="audio/*,video/mp4,video/webm"
                  onChange={(e) => {
                    const file = e.target.files?.[0]
                    if (file) handleFileSelect(file)
                  }}
                  className="hidden"
                />

                {/* Live recording section */}
                <div className="bg-slate-900 rounded-lg p-6 border border-slate-700">
                  <div className="text-center space-y-4">
                    {isRecording ? (
                      <>
                        {/* Recording in progress */}
                        <div className="flex items-center justify-center gap-3">
                          <div className="w-4 h-4 bg-red-500 rounded-full animate-pulse" />
                          <span className="text-red-400 font-medium">Recording...</span>
                          <span className="text-white font-mono text-lg">{formatDuration(recordingDuration)}</span>
                        </div>
                        {/* Audio level indicator */}
                        <div className="flex justify-center gap-1">
                          {[...Array(12)].map((_, i) => (
                            <div
                              key={i}
                              className="w-1 bg-red-500 rounded-full animate-pulse"
                              style={{
                                height: `${Math.random() * 24 + 8}px`,
                                animationDelay: `${i * 0.1}s`
                              }}
                            />
                          ))}
                        </div>
                        <button
                          onClick={stopRecording}
                          className="px-6 py-3 bg-red-600 text-white rounded-full hover:bg-red-500 flex items-center justify-center gap-2 mx-auto"
                        >
                          <Square className="w-5 h-5 fill-current" />
                          Stop Recording
                        </button>
                      </>
                    ) : recordedBlob ? (
                      <>
                        {/* Recording complete */}
                        <CheckCircle2 className="w-12 h-12 mx-auto text-green-500" />
                        <p className="text-white font-medium">Recording Complete</p>
                        <p className="text-sm text-slate-400">{formatDuration(recordingDuration)} recorded</p>
                        {/* Audio preview */}
                        <audio
                          controls
                          src={URL.createObjectURL(recordedBlob)}
                          className="mx-auto"
                        />
                        <div className="flex gap-2 justify-center">
                          <button
                            onClick={() => {
                              setRecordedBlob(null)
                              setRecordingDuration(0)
                            }}
                            className="px-4 py-2 text-sm text-slate-400 hover:text-white"
                          >
                            Discard
                          </button>
                          <button
                            onClick={startRecording}
                            className="px-4 py-2 text-sm bg-slate-700 text-white rounded-lg hover:bg-slate-600"
                          >
                            Record Again
                          </button>
                        </div>
                      </>
                    ) : (
                      <>
                        {/* Ready to record */}
                        <Mic className="w-12 h-12 mx-auto text-slate-500" />
                        <p className="text-white">Record your story</p>
                        <p className="text-sm text-slate-500">Click to start recording from your microphone</p>
                        <button
                          onClick={startRecording}
                          className="px-6 py-3 bg-blue-600 text-white rounded-full hover:bg-blue-500 flex items-center justify-center gap-2 mx-auto"
                        >
                          <Mic className="w-5 h-5" />
                          Start Recording
                        </button>
                      </>
                    )}
                  </div>
                </div>

                {/* Divider */}
                {!isRecording && !recordedBlob && (
                  <div className="flex items-center gap-4">
                    <div className="flex-1 border-t border-slate-700" />
                    <span className="text-slate-500 text-sm">or upload a file</span>
                    <div className="flex-1 border-t border-slate-700" />
                  </div>
                )}

                {/* Drop zone - only show when not recording */}
                {!isRecording && !recordedBlob && (
                  <div
                    onDrop={handleDrop}
                    onDragOver={(e) => e.preventDefault()}
                    onClick={() => fileInputRef.current?.click()}
                    className={clsx(
                      'border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors',
                      audioFile
                        ? 'border-green-500 bg-green-500/10'
                        : 'border-slate-600 hover:border-slate-500 bg-slate-900/50'
                    )}
                  >
                    {audioFile ? (
                      <div className="space-y-2">
                        <CheckCircle2 className="w-10 h-10 mx-auto text-green-500" />
                        <p className="text-white font-medium">{audioFile.name}</p>
                        <p className="text-sm text-slate-400">
                          {(audioFile.size / 1024 / 1024).toFixed(1)} MB
                        </p>
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            setAudioFile(null)
                          }}
                          className="text-sm text-red-400 hover:text-red-300"
                        >
                          Remove
                        </button>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        <Upload className="w-10 h-10 mx-auto text-slate-500" />
                        <p className="text-white text-sm">Drop audio file or click to browse</p>
                        <p className="text-xs text-slate-500">
                          MP3, WAV, M4A, MP4, WebM, OGG (max 25MB)
                        </p>
                      </div>
                    )}
                  </div>
                )}

                {/* Transcribe button */}
                <button
                  onClick={handleTranscribe}
                  disabled={(!audioFile && !recordedBlob) || isTranscribing || isRecording}
                  className="w-full px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {isTranscribing ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Transcribing...
                    </>
                  ) : (
                    <>
                      <Mic className="w-5 h-5" />
                      Transcribe {recordedBlob ? 'Recording' : 'Audio'}
                    </>
                  )}
                </button>
              </div>
            )}

            {/* YouTube input */}
            {inputMethod === 'youtube' && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-slate-400 mb-2">YouTube Video URL</label>
                  <input
                    type="url"
                    value={youtubeUrl}
                    onChange={(e) => setYoutubeUrl(e.target.value)}
                    placeholder="https://www.youtube.com/watch?v=..."
                    className="w-full px-4 py-3 bg-slate-900 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
                  />
                  <p className="text-xs text-slate-500 mt-2">
                    Maximum video duration: 1 hour. Audio will be extracted and transcribed.
                  </p>
                </div>

                {/* Transcribe button */}
                <button
                  onClick={handleTranscribe}
                  disabled={!youtubeUrl || isTranscribing}
                  className="w-full px-4 py-3 bg-red-600 text-white rounded-lg hover:bg-red-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {isTranscribing ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Transcribing...
                    </>
                  ) : (
                    <>
                      <Youtube className="w-5 h-5" />
                      Transcribe YouTube Video
                    </>
                  )}
                </button>
              </div>
            )}

            {/* Transcription error */}
            {transcribeError && (
              <div className="flex items-center gap-2 text-red-400 bg-red-900/20 rounded-lg px-4 py-3">
                <AlertCircle className="w-5 h-5 flex-shrink-0" />
                <span>{transcribeError}</span>
              </div>
            )}

            <div className="flex justify-between">
              <button
                onClick={prevStep}
                className="px-6 py-2 bg-slate-700 text-white rounded-lg hover:bg-slate-600 flex items-center gap-2"
              >
                <ChevronLeft className="w-4 h-4" /> Back
              </button>
              <button
                onClick={handleStartWorkflow}
                disabled={!rawContent || executeWorkflow.isPending}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {executeWorkflow.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Starting...
                  </>
                ) : (
                  <>
                    Start Workflow <Wand2 className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {currentStep === 'workflow' && (
          <div className="space-y-4">
            {/* Workflow State Progress - only shown when show_internal_workflow flag is true */}
            {showInternals && (() => {
              // Determine which state to use for progress: live state or previous run's final state
              const effectiveState = currentState || previousRun?.final_state
              const effectiveStateIndex = WORKFLOW_STATES.findIndex(s => s.id === effectiveState)

              return (
            <div className="bg-slate-900 rounded-lg p-4 border border-slate-700">
              <div className="flex items-center gap-1 overflow-x-auto pb-2">
                {WORKFLOW_STATES.map((state, index) => {
                  const stateIndex = effectiveStateIndex

                  // Only mark as complete if:
                  // 1. Current state is 'complete', OR
                  // 2. We have a valid state index and this state comes before it
                  const isComplete = effectiveState === 'complete' ||
                    (stateIndex >= 0 && index < stateIndex)
                  const isCurrent = state.id === effectiveState
                  const isPending = !isComplete && !isCurrent

                  return (
                    <div key={state.id} className="flex items-center">
                      <div className={clsx(
                        'flex flex-col items-center min-w-[70px]',
                      )}>
                        <div className={clsx(
                          'w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium border-2 transition-colors',
                          isComplete && 'bg-green-600 border-green-600 text-white',
                          isCurrent && 'bg-blue-600 border-blue-600 text-white animate-pulse',
                          isPending && 'bg-slate-800 border-slate-600 text-slate-500',
                        )}>
                          {isComplete ? (
                            <CheckCircle2 className="w-4 h-4" />
                          ) : isCurrent ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <Circle className="w-3 h-3" />
                          )}
                        </div>
                        <span className={clsx(
                          'text-xs mt-1 text-center',
                          isComplete && 'text-green-400',
                          isCurrent && 'text-blue-400 font-medium',
                          isPending && 'text-slate-500',
                        )}>
                          {state.label}
                        </span>
                      </div>
                      {index < WORKFLOW_STATES.length - 1 && (
                        <div className={clsx(
                          'w-4 h-0.5 mx-1',
                          isComplete ? 'bg-green-600' : 'bg-slate-700',
                        )} />
                      )}
                    </div>
                  )
                })}
              </div>
              {effectiveState && (
                <div className="mt-2 pt-2 border-t border-slate-700">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400 text-sm">
                      {WORKFLOW_STATES.find(s => s.id === effectiveState)?.description || effectiveState}
                    </span>
                    {/* Show agents for fan-out states */}
                    {(() => {
                      const stateConfig = WORKFLOW_STATES.find(s => s.id === effectiveState)
                      if (stateConfig?.agents && stateConfig.agents.length > 0) {
                        return (
                          <div className="flex items-center gap-1">
                            <span className="text-xs text-slate-500 mr-1">Agents:</span>
                            {stateConfig.agents.map(agent => (
                              <span
                                key={agent}
                                className="px-2 py-0.5 bg-blue-600/20 text-blue-400 text-xs rounded-full"
                              >
                                {agent}
                              </span>
                            ))}
                          </div>
                        )
                      }
                      return null
                    })()}
                  </div>
                </div>
              )}
            </div>
              )
            })()}

            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-white">
                  {aborted ? 'Workflow Aborted' : paused ? 'Workflow Paused' : running ? 'Workflow Running' : workflowError ? 'Workflow Error' : 'Workflow Complete'}
                </h2>
                <p className="text-slate-400">
                  {selectedPost?.topic}
                </p>
              </div>
              {/* Status badge and controls */}
              <div className="flex items-center gap-2">
                {running && !awaitingApproval && (
                  <>
                    {paused ? (
                      <button
                        onClick={() => resumeWorkflow()}
                        className="px-3 py-1 bg-green-600 text-white rounded-lg hover:bg-green-500 flex items-center gap-2 text-sm"
                      >
                        <PlayCircle className="w-4 h-4" /> Resume
                      </button>
                    ) : (
                      <button
                        onClick={() => pauseWorkflow()}
                        className="px-3 py-1 bg-yellow-600 text-white rounded-lg hover:bg-yellow-500 flex items-center gap-2 text-sm"
                      >
                        <Pause className="w-4 h-4" /> Pause
                      </button>
                    )}
                    <button
                      onClick={() => abortWorkflow()}
                      className="px-3 py-1 bg-red-600 text-white rounded-lg hover:bg-red-500 flex items-center gap-2 text-sm"
                    >
                      <Square className="w-4 h-4" /> Abort
                    </button>
                  </>
                )}
                <div className={clsx(
                  'px-3 py-1 rounded-full text-sm font-medium flex items-center gap-2',
                  awaitingApproval && 'bg-purple-600/20 text-purple-400',
                  aborted && 'bg-red-600/20 text-red-400',
                  paused && !aborted && 'bg-yellow-600/20 text-yellow-400',
                  running && !paused && !awaitingApproval && 'bg-blue-600/20 text-blue-400',
                  !running && !workflowError && !aborted && 'bg-green-600/20 text-green-400',
                  workflowError && 'bg-red-600/20 text-red-400',
                )}>
                  {awaitingApproval && <MessageCircle className="w-4 h-4" />}
                  {aborted && <XCircle className="w-4 h-4" />}
                  {paused && !aborted && !awaitingApproval && <Pause className="w-4 h-4" />}
                  {!running && !workflowError && !aborted && <CheckCircle2 className="w-4 h-4" />}
                  {workflowError && <AlertCircle className="w-4 h-4" />}
                  {awaitingApproval
                    ? (showInternals ? `Waiting: ${currentState}` : 'Waiting for Input')
                    : aborted
                    ? 'Aborted'
                    : paused
                    ? (showInternals ? `Paused: ${currentState}` : 'Paused')
                    : running
                    ? (showInternals ? `State: ${currentState || 'starting'}` : '')
                    : workflowError
                    ? 'Failed'
                    : 'Complete'}
                </div>
              </div>
            </div>

            {/* Progress bar — visible to all users */}
            {(running || (!running && !workflowError && !aborted && currentState === 'complete')) && (() => {
              const effectiveState = currentState || previousRun?.final_state
              const totalStates = WORKFLOW_STATES.length
              const currentIdx = WORKFLOW_STATES.findIndex(s => s.id === effectiveState)
              // If complete, fill to 100%. Otherwise use index position.
              const isWorkflowComplete = effectiveState === 'complete' || (!running && !workflowError && !aborted)
              const progressPercent = isWorkflowComplete
                ? 100
                : currentIdx >= 0
                ? Math.round(((currentIdx + 1) / totalStates) * 100)
                : 0
              const currentLabel = WORKFLOW_STATES.find(s => s.id === effectiveState)?.label || effectiveState || 'Starting'

              return (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-slate-400">
                      {isWorkflowComplete ? 'Complete' : currentLabel}
                    </span>
                    <span className="text-slate-500 text-xs">
                      {progressPercent}%
                    </span>
                  </div>
                  <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden flex">
                    <div
                      className={clsx(
                        'h-full transition-all duration-500 ease-out',
                        isWorkflowComplete ? 'bg-green-500 rounded-full' : 'bg-blue-500 rounded-l-full',
                      )}
                      style={{ width: `${progressPercent}%` }}
                    />
                    {!isWorkflowComplete && progressPercent < 100 && (
                      <div
                        className="h-full rounded-r-full progress-wave"
                        style={{ width: `${100 - progressPercent}%` }}
                      />
                    )}
                  </div>
                </div>
              )
            })()}

            {/* Metrics - only shown when show_internal_workflow flag is true */}
            {showInternals && (tokens > 0 || cost > 0) && (
              <div className="space-y-2">
                {/* Total metrics */}
                <div className="flex gap-4 text-sm">
                  <div className="bg-slate-900 px-3 py-1 rounded">
                    <span className="text-slate-400">Tokens:</span>{' '}
                    <span className="text-white">{tokens.toLocaleString()}</span>
                  </div>
                  <div className="bg-slate-900 px-3 py-1 rounded">
                    <span className="text-slate-400">API Cost:</span>{' '}
                    <span className="text-white">${cost.toFixed(4)}</span>
                  </div>
                </div>
                {/* Per-model breakdown */}
                {Object.keys(modelMetrics).length > 0 && (
                  <div className="flex flex-wrap gap-2 text-xs">
                    <span className="text-slate-500 self-center">By Model:</span>
                    {Object.entries(modelMetrics)
                      .sort((a, b) => b[1].cost_usd - a[1].cost_usd)
                      .map(([model, metrics]) => (
                        <div key={model} className="bg-slate-900 px-2 py-1 rounded flex items-center gap-2">
                          <span className="text-blue-400 font-medium">{model}</span>
                          <span className="text-slate-500">|</span>
                          <span className="text-slate-400">{metrics.tokens.toLocaleString()} tok</span>
                          <span className="text-slate-500">|</span>
                          <span className="text-slate-400">${metrics.cost_usd.toFixed(4)}</span>
                        </div>
                      ))}
                  </div>
                )}
                {/* Per-state breakdown */}
                {Object.keys(stateMetrics).length > 0 && (
                  <div className="flex flex-wrap gap-2 text-xs">
                    <span className="text-slate-500 self-center">By State:</span>
                    {Object.entries(stateMetrics)
                      .sort((a, b) => b[1].cost_usd - a[1].cost_usd)
                      .map(([state, metrics]) => (
                        <div key={state} className="bg-slate-900 px-2 py-1 rounded flex items-center gap-2">
                          <span className="text-purple-400 font-medium">{state}</span>
                          <span className="text-slate-500">|</span>
                          <span className="text-slate-400">{metrics.tokens.toLocaleString()} tok</span>
                          <span className="text-slate-500">|</span>
                          <span className="text-slate-400">${metrics.cost_usd.toFixed(4)}</span>
                        </div>
                      ))}
                  </div>
                )}
              </div>
            )}

            {/* Error display */}
            {workflowError && (
              <div className="bg-red-900/30 border border-red-700 rounded-lg p-4">
                <div className="flex items-center gap-2 text-red-400 font-medium mb-1">
                  <AlertCircle className="w-4 h-4" />
                  Error
                </div>
                <p className="text-red-300 text-sm">{workflowError}</p>
              </div>
            )}

            {/* Modal Popup - shown when awaiting approval */}
            {awaitingApproval && (
              <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
                <div className={clsx(
                  "bg-slate-800 rounded-xl p-6 max-w-2xl w-full max-h-[90vh] overflow-auto shadow-2xl border",
                  approvalContent?.includes("Loop detected") ? "border-amber-500" : "border-purple-500"
                )}>
                  <div className={clsx(
                    "flex items-center gap-3 font-semibold text-lg mb-4",
                    approvalContent?.includes("Loop detected") ? "text-amber-400" : "text-purple-400"
                  )}>
                    {approvalContent?.includes("Loop detected") ? (
                      <>
                        <AlertCircle className="w-6 h-6" />
                        Loop Detected - AI Keeps Asking Questions
                      </>
                    ) : (
                      <>
                        <MessageCircle className="w-6 h-6" />
                        {currentState === 'story-feedback' ? 'Reviewer Has Questions' : 'Your Input Needed'}
                      </>
                    )}
                  </div>

                  {/* Show the approval content (e.g., reviewer questions) */}
                  {approvalContent && (
                    <div className="bg-slate-900 rounded-lg p-4 mb-4 max-h-80 overflow-auto border border-slate-700">
                      <div className="text-xs text-purple-400 uppercase tracking-wide mb-3 font-medium">
                        {currentState === 'story-feedback' ? 'Please answer these questions to strengthen your story:' : 'Review the content below:'}
                      </div>
                      {(() => {
                        // Try to parse JSON and extract questions
                        try {
                          const jsonMatch = approvalContent.match(/```json\s*([\s\S]*?)\s*```/) ||
                                           approvalContent.match(/(\{[\s\S]*\})/);
                          if (jsonMatch) {
                            const data = JSON.parse(jsonMatch[1]);
                            return (
                              <div className="space-y-4">
                                {data.feedback && (
                                  <div className="text-slate-300 text-sm border-b border-slate-700 pb-3">
                                    <span className="font-medium text-slate-200">Summary:</span> {data.feedback}
                                  </div>
                                )}
                                {data.questions && data.questions.length > 0 && (
                                  <div className="space-y-2">
                                    <div className="font-medium text-slate-200 text-sm">Questions:</div>
                                    <ol className="list-decimal list-inside space-y-2">
                                      {data.questions.map((q: string, i: number) => (
                                        <li key={i} className="text-slate-300 text-sm">{q}</li>
                                      ))}
                                    </ol>
                                  </div>
                                )}
                                {data.missing && data.missing.length > 0 && (
                                  <div className="space-y-2">
                                    <div className="font-medium text-slate-200 text-sm">Missing Details:</div>
                                    <ul className="list-disc list-inside space-y-1">
                                      {data.missing.map((m: string, i: number) => (
                                        <li key={i} className="text-slate-400 text-sm">{m}</li>
                                      ))}
                                    </ul>
                                  </div>
                                )}
                              </div>
                            )
                          }
                        } catch (e) {
                          // Fall through to raw display
                        }
                        return (
                          <div className="text-slate-200 whitespace-pre-wrap text-sm leading-relaxed">
                            {approvalContent}
                          </div>
                        )
                      })()}
                    </div>
                  )}

                  {/* Show audit results from state machine (available to all users) */}
                  {auditResults && auditResults.length > 0 && (
                    <div className="bg-amber-900/20 rounded-lg p-4 mb-4 border border-amber-700/50">
                      <div className="text-xs text-amber-400 uppercase tracking-wide mb-3 font-medium">
                        Audit Results
                      </div>
                      <div className="space-y-3">
                        {auditResults.map((result, idx) => (
                          <div key={idx} className="border-b border-amber-700/30 pb-2 last:border-b-0 last:pb-0">
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-xs text-amber-300 font-medium uppercase">{getAuditorDisplayName(result.agent)}</span>
                              <div className="flex items-center gap-2">
                                {result.score != null && (
                                  <span className={clsx(
                                    'text-xs px-2 py-0.5 rounded',
                                    result.score >= 7 && 'bg-green-600/20 text-green-400',
                                    result.score >= 4 && result.score < 7 && 'bg-amber-600/20 text-amber-400',
                                    result.score < 4 && 'bg-red-600/20 text-red-400',
                                  )}>
                                    Score: {result.score}
                                  </span>
                                )}
                                {result.decision && (
                                  <span className={clsx(
                                    'text-xs px-2 py-0.5 rounded',
                                    result.decision === 'proceed' && 'bg-green-600/20 text-green-400',
                                    result.decision === 'retry' && 'bg-amber-600/20 text-amber-400',
                                    result.decision === 'halt' && 'bg-red-600/20 text-red-400',
                                  )}>
                                    {result.decision}
                                  </span>
                                )}
                              </div>
                            </div>
                            {result.feedback && (
                              <p className="text-amber-200/80 text-sm">{result.feedback}</p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Show final audit results when at human-approval state - only for internal users */}
                  {showInternals && currentState === 'human-approval' && outputs.finalAudits && Object.keys(outputs.finalAudits).length > 0 && (
                    <div className="bg-amber-900/20 rounded-lg p-4 mb-4 border border-amber-700/50">
                      <div className="text-xs text-amber-400 uppercase tracking-wide mb-3 font-medium">
                        Final Audit Results
                      </div>
                      <div className="space-y-3">
                        {Object.entries(outputs.finalAudits).map(([agent, auditContent]) => {
                          let parsed: { score?: number; decision?: string; feedback?: string; issues?: Array<{ severity?: string; issue?: string; fix?: string }> } | null = null
                          try {
                            const jsonMatch = auditContent.match(/```json\s*([\s\S]*?)\s*```/) ||
                                             auditContent.match(/(\{[\s\S]*\})/)
                            if (jsonMatch) {
                              parsed = JSON.parse(jsonMatch[1])
                            }
                          } catch (e) { /* ignore */ }

                          return (
                            <div key={agent} className="border-b border-amber-700/30 pb-2 last:border-b-0 last:pb-0">
                              <div className="flex items-center justify-between mb-1">
                                <span className="text-xs text-amber-300 font-medium uppercase">{agent}</span>
                                {parsed && (
                                  <div className="flex items-center gap-2">
                                    <span className={clsx(
                                      'text-xs px-2 py-0.5 rounded',
                                      parsed.score && parsed.score >= 7 && 'bg-green-600/20 text-green-400',
                                      parsed.score && parsed.score >= 4 && parsed.score < 7 && 'bg-amber-600/20 text-amber-400',
                                      parsed.score && parsed.score < 4 && 'bg-red-600/20 text-red-400',
                                    )}>
                                      Score: {parsed.score}
                                    </span>
                                    <span className={clsx(
                                      'text-xs px-2 py-0.5 rounded',
                                      parsed.decision === 'proceed' && 'bg-green-600/20 text-green-400',
                                      parsed.decision === 'retry' && 'bg-amber-600/20 text-amber-400',
                                      parsed.decision === 'halt' && 'bg-red-600/20 text-red-400',
                                    )}>
                                      {parsed.decision}
                                    </span>
                                  </div>
                                )}
                              </div>
                              {parsed?.feedback && (
                                <p className="text-amber-200/80 text-sm">{parsed.feedback}</p>
                              )}
                              {parsed?.issues && parsed.issues.length > 0 && (
                                <ul className="mt-1 space-y-1">
                                  {parsed.issues.map((issue, i) => (
                                    <li key={i} className={clsx(
                                      'text-xs pl-2 border-l-2',
                                      issue.severity === 'major' && 'border-red-500 text-red-300',
                                      issue.severity === 'minor' && 'border-amber-500 text-amber-300',
                                      !issue.severity && 'border-slate-500 text-slate-300',
                                    )}>
                                      {issue.issue}{issue.fix && <span className="text-slate-400"> → {issue.fix}</span>}
                                    </li>
                                  ))}
                                </ul>
                              )}
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  )}

                  {/* Prompt */}
                  {approvalPrompt && (
                    <p className="text-slate-400 text-sm mb-4 italic">{approvalPrompt}</p>
                  )}

                  {/* Circuit break: simplified buttons, no text input */}
                  {approvalContent?.includes("Loop detected") ? (
                    <div className="space-y-4">
                      {/* Error display for circuit break */}
                      {approvalError && (
                        <div className="bg-red-900/30 border border-red-700 rounded-lg p-3 flex items-center gap-2">
                          <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
                          <span className="text-red-300 text-sm">{approvalError}</span>
                          <button
                            onClick={() => setApprovalError(null)}
                            className="ml-auto text-red-400 hover:text-red-300"
                          >
                            <XCircle className="w-4 h-4" />
                          </button>
                        </div>
                      )}
                      <div className="flex gap-3 justify-end pt-4 border-t border-slate-700">
                      <button
                        onClick={async () => {
                          setSubmittingApproval(true)
                          setApprovalError(null)
                          try {
                            await submitApproval('abort')
                          } catch (e) {
                            setApprovalError(e instanceof Error ? e.message : 'Failed to abort')
                          } finally {
                            setSubmittingApproval(false)
                          }
                        }}
                        disabled={submittingApproval}
                        className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-500 disabled:opacity-50 flex items-center gap-2 text-sm"
                      >
                        <XCircle className="w-4 h-4" />
                        Abort Workflow
                      </button>

                      <button
                        onClick={async () => {
                          setSubmittingApproval(true)
                          setApprovalError(null)
                          try {
                            await submitApproval('approved')
                          } catch (e) {
                            setApprovalError(e instanceof Error ? e.message : 'Failed to approve')
                          } finally {
                            setSubmittingApproval(false)
                          }
                        }}
                        disabled={submittingApproval}
                        className={clsx('px-6 py-2 text-white rounded-lg disabled:opacity-50 flex items-center gap-2 text-sm font-medium bg-gradient-to-r', theme.gradient, theme.gradientHover)}
                      >
                        <Zap className="w-4 h-4" />
                        Skip & Continue
                      </button>
                      </div>
                    </div>
                  ) : (
                    /* Normal approval: text input and multiple options */
                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">
                          {currentState === 'story-feedback' ? 'Your Answers:' : 'Your Feedback:'}
                        </label>
                        <textarea
                          value={feedbackInput}
                          onChange={(e) => setFeedbackInput(e.target.value)}
                          placeholder={currentState === 'story-feedback'
                            ? "Answer the questions above with specific details...\n\nExample:\n1. The bold claim was when Gemini said 'I fixed the authentication bug' but it had actually deleted the entire auth module.\n2. I was building schematics for an ESP32-based sensor array.\n3. The moment was when Claude found a bug in 30 seconds that I'd been fighting with Gemini for 2 hours."
                            : "Provide your feedback..."
                          }
                          rows={8}
                          className="w-full px-4 py-3 bg-slate-900 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-purple-500 text-sm"
                          autoFocus
                        />
                      </div>

                      {/* Approval error display */}
                      {approvalError && (
                        <div className="bg-red-900/30 border border-red-700 rounded-lg p-3 flex items-center gap-2">
                          <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
                          <span className="text-red-300 text-sm">{approvalError}</span>
                          <button
                            onClick={() => setApprovalError(null)}
                            className="ml-auto text-red-400 hover:text-red-300"
                          >
                            <XCircle className="w-4 h-4" />
                          </button>
                        </div>
                      )}

                      {/* Action buttons */}
                      <div className="flex gap-3 justify-end pt-2 border-t border-slate-700">
                        <button
                          onClick={async () => {
                            setSubmittingApproval(true)
                            setApprovalError(null)
                            try {
                              await submitApproval('abort')
                              setFeedbackInput('')
                            } catch (e) {
                              setApprovalError(e instanceof Error ? e.message : 'Failed to cancel workflow')
                            } finally {
                              setSubmittingApproval(false)
                            }
                          }}
                          disabled={submittingApproval}
                          className="px-4 py-2 bg-slate-700 text-slate-300 rounded-lg hover:bg-slate-600 disabled:opacity-50 flex items-center gap-2 text-sm"
                        >
                          <XCircle className="w-4 h-4" />
                          Cancel
                        </button>

                        <button
                          onClick={async () => {
                            if (!feedbackInput.trim()) return
                            setSubmittingApproval(true)
                            setApprovalError(null)
                            try {
                              await submitApproval('feedback', feedbackInput)
                              setFeedbackInput('')
                            } catch (e) {
                              setApprovalError(e instanceof Error ? e.message : 'Failed to submit feedback')
                            } finally {
                              setSubmittingApproval(false)
                            }
                          }}
                          disabled={submittingApproval || !feedbackInput.trim()}
                          className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 text-sm font-medium"
                        >
                          <Send className="w-4 h-4" />
                          Submit Feedback
                        </button>

                        <button
                          onClick={async () => {
                            setSubmittingApproval(true)
                            setApprovalError(null)
                            try {
                              await submitApproval('approved')
                              setFeedbackInput('')
                            } catch (e) {
                              setApprovalError(e instanceof Error ? e.message : 'Failed to approve')
                            } finally {
                              setSubmittingApproval(false)
                            }
                          }}
                          disabled={submittingApproval}
                          className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-500 disabled:opacity-50 flex items-center gap-2 text-sm font-medium"
                        >
                          <Check className="w-4 h-4" />
                          Approved
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Event Log - only shown when show_internal_workflow flag is true */}
            {showInternals && (
              <div className="bg-slate-900 rounded-lg border border-slate-700">
                <div className="px-4 py-2 border-b border-slate-700 flex items-center justify-between">
                  <span className="text-sm font-medium text-slate-400">Activity Log</span>
                  <span className="text-xs text-slate-500">{events.length} events</span>
                </div>
                <div
                  ref={eventLogRef}
                  className="h-64 overflow-auto p-4 space-y-2"
                >
                  {events.length === 0 ? (
                    <div className="text-slate-500 text-sm">Waiting for workflow to start...</div>
                  ) : (
                    events.map((event) => (
                      <div key={event.id} className="flex gap-3 text-sm">
                        <div className="flex-shrink-0 mt-0.5">
                          {event.type.includes('error') ? (
                            <AlertCircle className="w-4 h-4 text-red-400" />
                          ) : event.type.includes('complete') ? (
                            <CheckCircle2 className="w-4 h-4 text-green-400" />
                          ) : event.type.includes('start') || event.type.includes('enter') ? (
                            <Zap className="w-4 h-4 text-blue-400" />
                          ) : (
                            <Circle className="w-3 h-3 text-slate-500 mt-0.5" />
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className={clsx(
                            event.type.includes('error') && 'text-red-300',
                            event.type.includes('complete') && 'text-green-300',
                            !event.type.includes('error') && !event.type.includes('complete') && 'text-slate-300',
                          )}>
                            {event.message}
                          </div>
                          {event.details && (
                            <div className="text-slate-500 text-xs mt-1 truncate">
                              {event.details.slice(0, 150)}...
                            </div>
                          )}
                        </div>
                        <div className="text-slate-600 text-xs flex-shrink-0">
                          {new Date(event.timestamp).toLocaleTimeString()}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}

            {/* Outputs Section */}
            <div className="space-y-3">
              {/* Review Result - only shown when show_internal_workflow flag is true */}
              {showInternals && outputs.reviewResult && (
                <details className="bg-slate-900 rounded-lg border border-slate-700">
                  <summary className="px-4 py-2 cursor-pointer text-sm font-medium text-slate-400 hover:text-slate-300">
                    Story Review Result
                  </summary>
                  <div className="px-4 pb-4 pt-2">
                    <div className="text-white whitespace-pre-wrap text-sm font-mono bg-slate-950 p-3 rounded max-h-64 overflow-auto">
                      {outputs.reviewResult}
                    </div>
                  </div>
                </details>
              )}

              {/* Processed Story */}
              {outputs.processedStory && (
                <details className="bg-slate-900 rounded-lg border border-slate-700" open>
                  <summary className="px-4 py-2 cursor-pointer text-sm font-medium text-green-400 hover:text-green-300">
                    ✓ Processed Story Template
                  </summary>
                  <div className="px-4 pb-4 pt-2">
                    <div className="text-white whitespace-pre-wrap text-sm font-mono bg-slate-950 p-3 rounded max-h-96 overflow-auto">
                      {outputs.processedStory}
                    </div>
                  </div>
                </details>
              )}

              {/* Drafts - only shown when show_internal_workflow flag is true */}
              {showInternals && outputs.drafts && Object.keys(outputs.drafts).length > 0 && (
                <details className="bg-slate-900 rounded-lg border border-slate-700">
                  <summary className="px-4 py-2 cursor-pointer text-sm font-medium text-slate-400 hover:text-slate-300">
                    Drafts ({Object.keys(outputs.drafts).length})
                  </summary>
                  <div className="px-4 pb-4 pt-2 space-y-2">
                    {Object.entries(outputs.drafts).map(([agent, draft]) => (
                      <div key={agent}>
                        <div className="text-xs text-slate-500 uppercase mb-1">{agent}</div>
                        <div className="text-slate-300 whitespace-pre-wrap text-sm bg-slate-950 p-3 rounded max-h-48 overflow-auto">
                          {draft}
                        </div>
                      </div>
                    ))}
                  </div>
                </details>
              )}

              {/* Cross-Audits - only shown when show_internal_workflow flag is true */}
              {showInternals && outputs.audits && Object.keys(outputs.audits).length > 0 && (
                <details className="bg-slate-900 rounded-lg border border-slate-700">
                  <summary className={clsx('px-4 py-2 cursor-pointer text-sm font-medium', theme.textPrimary)}>
                    Cross-Audit Feedback ({Object.keys(outputs.audits).length})
                  </summary>
                  <div className="px-4 pb-4 pt-2 space-y-2">
                    {Object.entries(outputs.audits).map(([agent, auditContent]) => {
                      // Try to parse JSON audit result for nicer display
                      let parsed: { score?: number; decision?: string; feedback?: string; issues?: Array<{ severity?: string; issue?: string; fix?: string }> } | null = null
                      try {
                        const jsonMatch = auditContent.match(/```json\s*([\s\S]*?)\s*```/) ||
                                         auditContent.match(/(\{[\s\S]*\})/)
                        if (jsonMatch) {
                          parsed = JSON.parse(jsonMatch[1])
                        }
                      } catch (e) { /* ignore parse errors */ }

                      return (
                        <div key={agent} className="border border-slate-700 rounded p-3">
                          <div className="flex items-center justify-between mb-2">
                            <div className="text-xs text-slate-500 uppercase">{getAuditorDisplayName(agent)}</div>
                            {parsed && (
                              <div className="flex items-center gap-2">
                                <span className={clsx(
                                  'text-xs px-2 py-0.5 rounded',
                                  parsed.score && parsed.score >= 7 && 'bg-green-600/20 text-green-400',
                                  parsed.score && parsed.score >= 4 && parsed.score < 7 && 'bg-amber-600/20 text-amber-400',
                                  parsed.score && parsed.score < 4 && 'bg-red-600/20 text-red-400',
                                )}>
                                  Score: {parsed.score}
                                </span>
                                <span className={clsx(
                                  'text-xs px-2 py-0.5 rounded',
                                  parsed.decision === 'proceed' && 'bg-green-600/20 text-green-400',
                                  parsed.decision === 'retry' && 'bg-amber-600/20 text-amber-400',
                                  parsed.decision === 'halt' && 'bg-red-600/20 text-red-400',
                                )}>
                                  {parsed.decision}
                                </span>
                              </div>
                            )}
                          </div>
                          {parsed ? (
                            <div className="space-y-2">
                              {parsed.feedback && (
                                <p className="text-slate-300 text-sm">{parsed.feedback}</p>
                              )}
                              {parsed.issues && parsed.issues.length > 0 && (
                                <ul className="text-sm space-y-1">
                                  {parsed.issues.map((issue, i) => (
                                    <li key={i} className={clsx(
                                      'pl-2 border-l-2',
                                      issue.severity === 'major' && 'border-red-500 text-red-300',
                                      issue.severity === 'minor' && 'border-amber-500 text-amber-300',
                                      !issue.severity && 'border-slate-500 text-slate-300',
                                    )}>
                                      <strong>{issue.issue}</strong>
                                      {issue.fix && <span className="text-slate-400"> → {issue.fix}</span>}
                                    </li>
                                  ))}
                                </ul>
                              )}
                            </div>
                          ) : (
                            <div className="text-slate-300 whitespace-pre-wrap text-sm bg-slate-950 p-2 rounded max-h-32 overflow-auto">
                              {auditContent}
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                </details>
              )}

              {/* Final Audits - only shown when show_internal_workflow flag is true */}
              {showInternals && outputs.finalAudits && Object.keys(outputs.finalAudits).length > 0 && (
                <details className="bg-slate-900 rounded-lg border border-red-700" open>
                  <summary className="px-4 py-2 cursor-pointer text-sm font-medium text-red-400 hover:text-red-300">
                    Final Audit Feedback ({Object.keys(outputs.finalAudits).length}) - Review Required
                  </summary>
                  <div className="px-4 pb-4 pt-2 space-y-2">
                    {Object.entries(outputs.finalAudits).map(([agent, auditContent]) => {
                      let parsed: { score?: number; decision?: string; feedback?: string; issues?: Array<{ severity?: string; issue?: string; fix?: string }> } | null = null
                      try {
                        const jsonMatch = auditContent.match(/```json\s*([\s\S]*?)\s*```/) ||
                                         auditContent.match(/(\{[\s\S]*\})/)
                        if (jsonMatch) {
                          parsed = JSON.parse(jsonMatch[1])
                        }
                      } catch (e) { /* ignore parse errors */ }

                      return (
                        <div key={agent} className="border border-red-700/50 rounded p-3 bg-red-900/10">
                          <div className="flex items-center justify-between mb-2">
                            <div className="text-xs text-red-400 uppercase font-medium">{agent}</div>
                            {parsed && (
                              <div className="flex items-center gap-2">
                                <span className={clsx(
                                  'text-xs px-2 py-0.5 rounded font-medium',
                                  parsed.score && parsed.score >= 7 && 'bg-green-600/20 text-green-400',
                                  parsed.score && parsed.score >= 4 && parsed.score < 7 && 'bg-amber-600/20 text-amber-400',
                                  parsed.score && parsed.score < 4 && 'bg-red-600/20 text-red-400',
                                )}>
                                  Score: {parsed.score}
                                </span>
                                <span className={clsx(
                                  'text-xs px-2 py-0.5 rounded font-medium',
                                  parsed.decision === 'proceed' && 'bg-green-600/20 text-green-400',
                                  parsed.decision === 'retry' && 'bg-amber-600/20 text-amber-400',
                                  parsed.decision === 'halt' && 'bg-red-600/20 text-red-400',
                                )}>
                                  {parsed.decision}
                                </span>
                              </div>
                            )}
                          </div>
                          {parsed ? (
                            <div className="space-y-2">
                              {parsed.feedback && (
                                <p className="text-red-200 text-sm font-medium">{parsed.feedback}</p>
                              )}
                              {parsed.issues && parsed.issues.length > 0 && (
                                <ul className="text-sm space-y-1">
                                  {parsed.issues.map((issue, i) => (
                                    <li key={i} className={clsx(
                                      'pl-2 border-l-2',
                                      issue.severity === 'major' && 'border-red-500 text-red-300',
                                      issue.severity === 'minor' && 'border-amber-500 text-amber-300',
                                      !issue.severity && 'border-slate-500 text-slate-300',
                                    )}>
                                      <strong>{issue.issue}</strong>
                                      {issue.fix && <span className="text-slate-400"> → {issue.fix}</span>}
                                    </li>
                                  ))}
                                </ul>
                              )}
                            </div>
                          ) : (
                            <div className="text-red-200 whitespace-pre-wrap text-sm bg-slate-950 p-2 rounded max-h-48 overflow-auto">
                              {auditContent}
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                </details>
              )}

              {/* Final Post Preview */}
              <div className="bg-slate-900 rounded-lg p-4 border border-slate-700">
                <h3 className="text-sm font-medium text-slate-400 mb-2">Final Post</h3>
                <div className="text-white whitespace-pre-wrap text-sm">
                  {outputs.finalPost || (running ? 'Will appear when workflow completes...' : 'No output yet')}
                </div>

                {/* Mark as Complete button for resumed runs */}
                {!running && outputs.finalPost && previousRun && selectedPost && (
                  <div className="mt-4 pt-4 border-t border-slate-700">
                    <button
                      onClick={async () => {
                        try {
                          // Update post status to 'ready' - finished posts page reads from database
                          await apiPatch(`/v1/w/${currentWorkspace?.id}/posts/${selectedPost.post_id}`, { status: 'ready' })
                          alert('Post marked as complete! It will now appear in Finished Posts.')
                          // Refresh posts list and reset selection
                          await queryClient.invalidateQueries({ queryKey: ['available-posts'] })
                          setSelectedPost(null)
                          setCurrentStep('select')
                          resetWorkflow()
                        } catch (e) {
                          console.error('Failed to mark post complete:', e)
                          alert('Failed to mark post complete: ' + (e instanceof Error ? e.message : 'Unknown error'))
                        }
                      }}
                      className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-500 flex items-center gap-2"
                    >
                      <Check className="w-4 h-4" />
                      Mark as Complete
                    </button>
                  </div>
                )}
              </div>
            </div>

            <div className="flex justify-between">
              <button
                onClick={() => {
                  resetWorkflow()
                  prevStep()
                }}
                disabled={running}
                className="px-6 py-2 bg-slate-700 text-white rounded-lg hover:bg-slate-600 flex items-center gap-2 disabled:opacity-50"
              >
                <ChevronLeft className="w-4 h-4" /> Back
              </button>
              <div className="flex gap-2">
                {workflowError && (
                  <button
                    onClick={async () => {
                      resetWorkflow()
                      // Start workflow without advancing step
                      if (selectedPost) {
                        try {
                          await executeWorkflow.mutateAsync({ story: selectedPost.post_id, content: rawContent })
                        } catch (error) {
                          console.error('Retry failed:', error)
                        }
                      }
                    }}
                    className={clsx('px-6 py-2 text-white rounded-lg flex items-center gap-2 bg-gradient-to-r', theme.gradient, theme.gradientHover)}
                  >
                    <Wand2 className="w-4 h-4" /> Retry
                  </button>
                )}
                <button
                  onClick={nextStep}
                  disabled={running || (!outputs.finalPost && !previousRun)}
                  className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {previousRun && !outputs.finalPost ? 'Continue' : 'Finish'} <Check className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        )}

        {currentStep === 'complete' && (
          <div className="space-y-4 text-center py-8">
            <div className="w-16 h-16 bg-green-600 rounded-full flex items-center justify-center mx-auto">
              <Check className="w-8 h-8 text-white" />
            </div>
            <h2 className="text-lg font-semibold text-white">Story Complete!</h2>
            <p className="text-slate-400">
              Your post has been generated and saved.
            </p>
            <div className="flex justify-center gap-4 pt-4">
              <button
                onClick={async () => {
                  // Refresh posts list to show next available post
                  await queryClient.invalidateQueries({ queryKey: ['available-posts'] })
                  setCurrentStep('select')
                  setSelectedPost(null)
                  setRawContent('')
                  resetWorkflow()
                }}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-500"
              >
                Create Another Story
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
