import { useState, useEffect } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  ChevronRight,
  ChevronLeft,
  Zap,
  MessageSquare,
  Send,
  Loader2,
  Check,
  Target,
  BookOpen,
  RefreshCw,
  Sparkles,
} from 'lucide-react'
import { clsx } from 'clsx'
import { useThemeClasses } from '../hooks/useThemeClasses'
import {
  fetchExistingStrategy,
  submitQuickModeV1,
  sendDeepMessageV1,
  generateFromDeepV1,
  approvePlanV1,
  fetchContentStylesV1,
  GeneratedPlan,
  DeepModeState,
  ExistingStrategy,
  V1ContentStyle,
} from '../api/onboarding'
import { useWorkspaceStore } from '../stores/workspaceStore'
import StrategyChatPanel, { ExtractedStrategy } from '../components/StrategyChatPanel'

type Mode = 'select' | 'quick' | 'deep' | 'chat'
type Step = 'existing' | 'mode' | 'setup' | 'chat' | 'plan' | 'complete'

const getErrorMessage = (error: unknown) => {
  if (error instanceof Error) return error.message
  return String(error)
}

const normalizePlan = (rawPlan: GeneratedPlan | null): GeneratedPlan => {
  const safeChapters = Array.isArray(rawPlan?.chapters) ? rawPlan.chapters : []
  return {
    signature_thesis: rawPlan?.signature_thesis || '',
    chapters: safeChapters.map((chapter, index) => ({
      chapter_number: Number(chapter.chapter_number) || index + 1,
      title: chapter.title || `Chapter ${index + 1}`,
      theme: chapter.theme || '',
      theme_description: chapter.theme_description || '',
      posts: Array.isArray(chapter.posts)
        ? chapter.posts.map((post, postIndex) => ({
            post_number: Number(post.post_number) || postIndex + 1,
            topic: post.topic || '',
            shape: post.shape || '',
            cadence: post.cadence || '',
          }))
        : [],
    })),
  }
}

// Default questions for quick mode (no longer fetched from server)
const QUICK_QUESTIONS = [
  { id: 'professional_role', question: 'What is your professional role?', type: 'text' as const, placeholder: 'e.g., Marketing Director, Software Engineer, Consultant' },
  { id: 'known_for', question: 'What do you want to be known for?', type: 'text' as const, placeholder: 'e.g., AI expertise, growth marketing, leadership insights' },
  { id: 'target_audience', question: 'Who is your target audience?', type: 'text' as const, placeholder: 'e.g., CTOs, early-stage founders, marketing professionals' },
  { id: 'content_style', question: 'What content style do you prefer?', type: 'text' as const, placeholder: 'e.g., educational, storytelling, thought leadership' },
  { id: 'posts_per_week', question: 'How many posts per week?', type: 'text' as const, placeholder: 'e.g., 2, 3, 5' },
]

export default function Onboarding() {
  const theme = useThemeClasses()
  const [step, setStep] = useState<Step>('existing')
  const [mode, setMode] = useState<Mode>('select')
  const [existingStrategy, setExistingStrategy] = useState<ExistingStrategy | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const workspaceId = useWorkspaceStore((s) => s.currentWorkspaceId)

  // Check for existing strategy
  const { data: strategyData, isLoading: strategyLoading } = useQuery({
    queryKey: ['existing-strategy', workspaceId],
    queryFn: () => fetchExistingStrategy(),
    enabled: !!workspaceId && step === 'existing',
  })

  // Process strategy data when it loads
  useEffect(() => {
    if (strategyData && step === 'existing') {
      if (strategyData.exists) {
        setExistingStrategy(strategyData)
      } else {
        // No existing strategy, go to mode selection
        setStep('mode')
      }
    }
  }, [strategyData, step])

  // Quick mode state
  const [currentQuestion, setCurrentQuestion] = useState(0)
  const [answers, setAnswers] = useState<Record<string, string>>({})

  // Deep mode state
  const [deepState, setDeepState] = useState<DeepModeState | null>(null)
  const [deepInput, setDeepInput] = useState('')
  const [contentStyles, setContentStyles] = useState<V1ContentStyle[]>([])
  const [selectedStyle, setSelectedStyle] = useState('mixed')
  const availableStyles =
    contentStyles.length > 0
      ? contentStyles
      : [
          {
            id: 'mixed',
            name: 'Mixed',
            description: 'Combination based on topic',
          },
        ]

  // Generated plan
  const [plan, setPlan] = useState<GeneratedPlan | null>(null)

  // Mutations using v1 workspace-scoped endpoints
  const deepMessageMutation = useMutation({
    mutationFn: (payload: { message: string; forceReady?: boolean }) =>
      sendDeepMessageV1(workspaceId!, {
        message: payload.message,
        state: deepState,
        force_ready: payload.forceReady,
      }),
    onSuccess: (data) => {
      setDeepState(data.state)
      setErrorMessage(null)
    },
    onError: (error) => {
      setErrorMessage(`Failed to send message: ${getErrorMessage(error)}`)
    },
  })

  const quickSubmitMutation = useMutation({
    mutationFn: () =>
      submitQuickModeV1(workspaceId!, {
        professional_role: answers.professional_role || '',
        known_for: answers.known_for || '',
        target_audience: answers.target_audience || '',
        content_style: answers.content_style || 'mixed',
        posts_per_week: parseInt(answers.posts_per_week || '2'),
      }),
    onSuccess: (data) => {
      setPlan(normalizePlan(data.plan))
      setStep('plan')
      setErrorMessage(null)
    },
    onError: (error) => {
      setErrorMessage(`Failed to generate plan: ${getErrorMessage(error)}`)
    },
  })

  const deepGenerateMutation = useMutation({
    mutationFn: () =>
      generateFromDeepV1(workspaceId!, {
        content_style: selectedStyle,
        state: deepState!,
      }),
    onSuccess: (data) => {
      setPlan(normalizePlan(data.plan))
      setStep('plan')
      setErrorMessage(null)
    },
    onError: (error) => {
      setErrorMessage(`Failed to generate plan: ${getErrorMessage(error)}`)
    },
  })

  const approveMutation = useMutation({
    mutationFn: () =>
      approvePlanV1(workspaceId!, {
        plan: plan!,
        positioning: answers.positioning || answers.known_for || 'Content Creator',
        target_audience: answers.target_audience || 'Professionals',
        content_style:
          mode === 'quick'
            ? answers.content_style || 'mixed'
            : mode === 'chat'
              ? answers.content_style || 'mixed'
              : selectedStyle,
        onboarding_mode:
          mode === 'deep' ? 'deep' : mode === 'chat' ? 'chat' : 'quick',
        transcript:
          mode === 'deep'
            ? JSON.stringify(deepState?.messages)
            : undefined,
      }),
    onSuccess: () => {
      setStep('complete')
      setErrorMessage(null)
    },
    onError: (error) => {
      setErrorMessage(`Failed to save plan: ${getErrorMessage(error)}`)
    },
  })

  const handleModeSelect = async (selectedMode: Mode) => {
    if (!workspaceId) {
      setErrorMessage('No workspace selected')
      return
    }
    setErrorMessage(null)
    setMode(selectedMode)

    if (selectedMode === 'quick') {
      setStep('setup')
    } else if (selectedMode === 'chat') {
      setStep('chat')
    } else if (selectedMode === 'deep') {
      // Load content styles for deep mode
      try {
        const stylesResult = await fetchContentStylesV1(workspaceId)
        setContentStyles(stylesResult.styles)
      } catch (error) {
        setContentStyles([])
        setErrorMessage(`Failed to load content styles: ${getErrorMessage(error)}`)
      }
      // Start deep mode by sending initial message
      try {
        const response = await sendDeepMessageV1(workspaceId, {
          message: "Let's start building my content strategy.",
          state: null,
        })
        setDeepState(response.state)
        setStep('setup')
      } catch (error) {
        setErrorMessage(`Failed to start deep discovery: ${getErrorMessage(error)}`)
      }
    }
  }

  // Handle strategy from AI chat
  const handleChatStrategyReady = ({
    strategy,
    plan,
  }: {
    strategy: ExtractedStrategy
    plan?: GeneratedPlan
  }) => {
    // Convert chat strategy to generated plan format if no plan returned
    const chatPlan: GeneratedPlan = plan || {
      signature_thesis: strategy.signature_thesis || '',
      chapters: (strategy.chapter_themes || []).map((theme, i) => ({
        chapter_number: i + 1,
        title: theme,
        theme: theme,
        theme_description: '',
        posts: [],
      })),
    }
    setPlan(normalizePlan(chatPlan))
    // Store extracted info for plan approval
    setAnswers({
      known_for: strategy.positioning || '',
      positioning: strategy.positioning || '',
      target_audience: strategy.target_audience || '',
      content_style: strategy.content_style || 'mixed',
    })
    setSelectedStyle(strategy.content_style || 'mixed')
    setStep('plan')
  }

  const handleQuickAnswer = (value: string) => {
    const questionId = QUICK_QUESTIONS[currentQuestion].id
    setAnswers({ ...answers, [questionId]: value })
  }

  const handleQuickNext = async () => {
    if (currentQuestion < QUICK_QUESTIONS.length - 1) {
      setCurrentQuestion(currentQuestion + 1)
    } else {
      // Submit all answers
      await quickSubmitMutation.mutateAsync()
    }
  }

  const handleDeepSend = async () => {
    if (!deepInput.trim()) return
    if (!deepState) {
      setErrorMessage('Deep discovery is not ready yet.')
      return
    }
    await deepMessageMutation.mutateAsync({ message: deepInput })
    setDeepInput('')
  }

  const handleForceReady = async () => {
    if (!deepState) {
      setErrorMessage('Deep discovery is not ready yet.')
      return
    }
    await deepMessageMutation.mutateAsync({
      message: "I'm ready to generate the plan.",
      forceReady: true,
    })
  }

  const handleGeneratePlan = async () => {
    if (!deepState) {
      setErrorMessage('Deep discovery is not ready yet.')
      return
    }
    await deepGenerateMutation.mutateAsync()
  }

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <h1 className="text-2xl font-bold text-white">Content Strategy Setup</h1>

      {/* Step indicator - hide when checking existing strategy */}
      {step !== 'existing' && (
        <div className="flex items-center gap-4">
          {['Mode', 'Setup', 'Plan', 'Complete'].map((label, index) => {
            const stepNames: Step[] = ['mode', 'setup', 'plan', 'complete']
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
        {errorMessage && (
          <div className="mb-4 rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
            {errorMessage}
          </div>
        )}
        {/* Loading existing strategy */}
        {step === 'existing' && strategyLoading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
            <span className="ml-3 text-slate-400">Checking for existing strategy...</span>
          </div>
        )}

        {/* Existing Strategy Display */}
        {step === 'existing' && existingStrategy?.exists && (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-semibold text-white mb-2">
                Your Current Strategy
              </h2>
              <p className="text-slate-400">
                You already have a content strategy set up. Here's what you're working on.
              </p>
            </div>

            {/* Signature Thesis */}
            {existingStrategy.goal?.signature_thesis && (
              <div className="p-4 bg-blue-600/20 border border-blue-500 rounded-lg">
                <div className="flex items-center gap-2 text-blue-400 mb-2">
                  <Target className="w-5 h-5" />
                  <span className="font-medium">Signature Thesis</span>
                </div>
                <p className="text-white">{existingStrategy.goal.signature_thesis}</p>
              </div>
            )}

            {/* Strategy Details */}
            <div className="grid grid-cols-2 gap-4">
              {existingStrategy.goal?.positioning && (
                <div className="p-3 bg-slate-900 rounded-lg">
                  <span className="text-slate-400 text-sm">Positioning</span>
                  <p className="text-white">{existingStrategy.goal.positioning}</p>
                </div>
              )}
              {existingStrategy.goal?.target_audience && (
                <div className="p-3 bg-slate-900 rounded-lg">
                  <span className="text-slate-400 text-sm">Target Audience</span>
                  <p className="text-white">{existingStrategy.goal.target_audience}</p>
                </div>
              )}
              {existingStrategy.goal?.content_style && (
                <div className="p-3 bg-slate-900 rounded-lg">
                  <span className="text-slate-400 text-sm">Content Style</span>
                  <p className="text-white capitalize">{existingStrategy.goal.content_style}</p>
                </div>
              )}
            </div>

            {/* Chapters */}
            {existingStrategy.chapters && existingStrategy.chapters.length > 0 && (
              <div className="space-y-3">
                <h3 className="text-white font-medium flex items-center gap-2">
                  <BookOpen className="w-5 h-5 text-slate-400" />
                  {existingStrategy.chapters.length} Chapters
                </h3>
                <div className="space-y-2">
                  {existingStrategy.chapters.map((chapter) => (
                    <div
                      key={chapter.id}
                      className="p-3 bg-slate-900 rounded-lg flex items-center justify-between"
                    >
                      <div>
                        <span className="text-white font-medium">
                          Chapter {chapter.chapter_number}: {chapter.title}
                        </span>
                        {chapter.theme && (
                          <p className="text-slate-400 text-sm">Theme: {chapter.theme}</p>
                        )}
                      </div>
                      <div className="text-right">
                        <span className="text-green-400">{chapter.completed_count}</span>
                        <span className="text-slate-500">/{chapter.post_count} posts</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-4 pt-4">
              <a
                href="/story"
                className="flex-1 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-500 text-center"
              >
                Continue Writing
              </a>
              <button
                onClick={() => {
                  setExistingStrategy(null)
                  setStep('mode')
                }}
                className="px-6 py-3 bg-slate-700 text-white rounded-lg hover:bg-slate-600 flex items-center gap-2"
              >
                <RefreshCw className="w-4 h-4" />
                Create New Strategy
              </button>
            </div>
          </div>
        )}

        {/* Mode Selection */}
        {step === 'mode' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-semibold text-white mb-2">
                Welcome to Content Strategy
              </h2>
              <p className="text-slate-400">
                Let's create your personalized content plan. Choose your preferred setup experience.
              </p>
            </div>

            {/* Mode Selection */}
            <div className="grid grid-cols-3 gap-4">
              <button
                onClick={() => handleModeSelect('quick')}
                disabled={!workspaceId}
                className="p-6 bg-slate-900 rounded-lg border border-slate-600 hover:border-blue-500 transition-colors text-left disabled:opacity-50"
              >
                <Zap className={clsx('w-8 h-8 mb-3', theme.iconPrimary)} />
                <h3 className="text-white font-semibold mb-1">Quick Setup</h3>
                <p className="text-slate-400 text-sm">5 questions, ~3 minutes</p>
              </button>

              <button
                onClick={() => handleModeSelect('chat')}
                disabled={!workspaceId}
                className={clsx('p-6 bg-slate-900 rounded-lg border border-slate-600 transition-colors text-left disabled:opacity-50', theme.borderHover)}
              >
                <Sparkles className={clsx('w-8 h-8 mb-3', theme.iconPrimary)} />
                <h3 className="text-white font-semibold mb-1">AI Chat</h3>
                <p className="text-slate-400 text-sm">Talk with AI, ~5-10 minutes</p>
              </button>

              <button
                onClick={() => handleModeSelect('deep')}
                disabled={!workspaceId}
                className="p-6 bg-slate-900 rounded-lg border border-slate-600 hover:border-blue-500 transition-colors text-left disabled:opacity-50"
              >
                <MessageSquare className="w-8 h-8 text-blue-400 mb-3" />
                <h3 className="text-white font-semibold mb-1">Deep Discovery</h3>
                <p className="text-slate-400 text-sm">Guided conversation, ~15 minutes</p>
              </button>
            </div>
          </div>
        )}

        {/* Quick Mode Setup */}
        {step === 'setup' && mode === 'quick' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-white">
                Question {currentQuestion + 1} of {QUICK_QUESTIONS.length}
              </h2>
              <div className="text-slate-400 text-sm">
                {Math.round(((currentQuestion + 1) / QUICK_QUESTIONS.length) * 100)}% complete
              </div>
            </div>

            <div className="space-y-4">
              <p className="text-white text-lg">{QUICK_QUESTIONS[currentQuestion].question}</p>

              <input
                type="text"
                value={answers[QUICK_QUESTIONS[currentQuestion].id] || ''}
                onChange={(e) => handleQuickAnswer(e.target.value)}
                placeholder={QUICK_QUESTIONS[currentQuestion].placeholder}
                className="w-full px-4 py-3 bg-slate-900 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
              />
            </div>

            <div className="flex justify-between">
              <button
                onClick={() =>
                  currentQuestion > 0
                    ? setCurrentQuestion(currentQuestion - 1)
                    : setStep('mode')
                }
                className="px-6 py-2 bg-slate-700 text-white rounded-lg hover:bg-slate-600 flex items-center gap-2"
              >
                <ChevronLeft className="w-4 h-4" /> Back
              </button>
              <button
                onClick={handleQuickNext}
                disabled={!answers[QUICK_QUESTIONS[currentQuestion].id] || quickSubmitMutation.isPending}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-500 disabled:opacity-50 flex items-center gap-2"
              >
                {quickSubmitMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Generating...
                  </>
                ) : currentQuestion < QUICK_QUESTIONS.length - 1 ? (
                  <>
                    Next <ChevronRight className="w-4 h-4" />
                  </>
                ) : (
                  <>
                    Generate Plan <ChevronRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* Deep Mode Setup */}
        {step === 'setup' && mode === 'deep' && deepState && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-white">Deep Discovery</h2>

            {/* Conversation */}
            <div className="bg-slate-900 rounded-lg p-4 h-96 overflow-y-auto space-y-4">
              {deepState.messages.map((msg, index) => (
                <div
                  key={index}
                  className={clsx(
                    'p-3 rounded-lg max-w-[80%]',
                    msg.role === 'assistant'
                      ? 'bg-slate-800 text-slate-300'
                      : 'bg-blue-600 text-white ml-auto'
                  )}
                >
                  {msg.content}
                </div>
              ))}
              {deepMessageMutation.isPending && (
                <div className="flex items-center gap-2 text-slate-400">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Thinking...
                </div>
              )}
            </div>

            {/* Input */}
            {!deepState.ready_to_generate ? (
              <div className="space-y-3">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={deepInput}
                    onChange={(e) => setDeepInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleDeepSend()}
                    placeholder="Type your response..."
                    className="flex-1 px-4 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
                  />
                  <button
                    onClick={handleDeepSend}
                    disabled={!deepInput.trim() || deepMessageMutation.isPending}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-500 disabled:opacity-50"
                  >
                    <Send className="w-5 h-5" />
                  </button>
                </div>
                <button
                  onClick={handleForceReady}
                  disabled={deepMessageMutation.isPending}
                  className="text-sm text-blue-400 hover:text-blue-300"
                >
                  I am ready to generate a plan now
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="p-4 bg-green-600/20 border border-green-500 rounded-lg">
                  <p className="text-green-400">
                    Ready to generate your content plan! Select a style preference below.
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-2">
                    Content Style
                  </label>
                  <select
                    value={selectedStyle}
                    onChange={(e) => setSelectedStyle(e.target.value)}
                    className="w-full px-4 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white"
                  >
                    {availableStyles.map((style) => (
                      <option key={style.id} value={style.id}>
                        {style.name} - {style.description}
                      </option>
                    ))}
                  </select>
                </div>
                <button
                  onClick={handleGeneratePlan}
                  disabled={deepGenerateMutation.isPending}
                  className="w-full px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-500 disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {deepGenerateMutation.isPending ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Generating Plan...
                    </>
                  ) : (
                    'Generate My Content Plan'
                  )}
                </button>
              </div>
            )}
          </div>
        )}

        {/* AI Chat Mode */}
        {step === 'chat' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-white">AI Strategy Assistant</h2>
              <button
                onClick={() => setStep('mode')}
                className="px-4 py-2 bg-slate-700 text-white rounded-lg hover:bg-slate-600 flex items-center gap-2 text-sm"
              >
                <ChevronLeft className="w-4 h-4" /> Back
              </button>
            </div>
            <p className="text-slate-400 text-sm">
              Have a conversation with our AI to discover your content strategy. It will ask about your goals, audience, and style.
            </p>
            <div className="h-[500px]">
              <StrategyChatPanel onStrategyReady={handleChatStrategyReady} />
            </div>
          </div>
        )}

        {/* Plan Review */}
        {step === 'plan' && plan && (
          <div className="space-y-6">
            <h2 className="text-lg font-semibold text-white">Your Content Plan</h2>

            {/* Thesis */}
            <div className="p-4 bg-blue-600/20 border border-blue-500 rounded-lg">
              <div className="flex items-center gap-2 text-blue-400 mb-2">
                <Target className="w-5 h-5" />
                <span className="font-medium">Signature Thesis</span>
              </div>
              <p className="text-white">{plan.signature_thesis}</p>
            </div>

            {/* Chapters */}
            <div className="space-y-4">
              <h3 className="text-white font-medium flex items-center gap-2">
                <BookOpen className="w-5 h-5 text-slate-400" />
                {plan.chapters.length} Chapters
              </h3>
              {plan.chapters.map((chapter) => (
                <div
                  key={chapter.chapter_number}
                  className="bg-slate-900 rounded-lg p-4"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-white font-medium">
                      Chapter {chapter.chapter_number}: {chapter.title}
                    </span>
                    <span className="text-slate-400 text-sm">
                      {chapter.posts.length} posts
                    </span>
                  </div>
                  {chapter.theme && (
                    <p className="text-slate-400 text-sm mb-2">
                      Theme: {chapter.theme}
                    </p>
                  )}
                  <div className="flex flex-wrap gap-2">
                    {chapter.posts.slice(0, 3).map((post) => (
                      <span
                        key={post.post_number}
                        className="px-2 py-1 bg-slate-800 rounded text-xs text-slate-300"
                      >
                        {post.topic ? `${post.topic.slice(0, 30)}...` : 'Untitled'}
                      </span>
                    ))}
                    {chapter.posts.length > 3 && (
                      <span className="px-2 py-1 bg-slate-800 rounded text-xs text-slate-400">
                        +{chapter.posts.length - 3} more
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>

            <div className="flex justify-between">
              <button
                onClick={() => setStep('setup')}
                className="px-6 py-2 bg-slate-700 text-white rounded-lg hover:bg-slate-600 flex items-center gap-2"
              >
                <ChevronLeft className="w-4 h-4" /> Edit
              </button>
              <button
                onClick={() => approveMutation.mutate()}
                disabled={approveMutation.isPending || !workspaceId}
                className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-500 disabled:opacity-50 flex items-center gap-2"
              >
                {approveMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    Approve Plan <Check className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* Complete */}
        {step === 'complete' && (
          <div className="text-center py-8 space-y-4">
            <div className="w-16 h-16 bg-green-600 rounded-full flex items-center justify-center mx-auto">
              <Check className="w-8 h-8 text-white" />
            </div>
            <h2 className="text-lg font-semibold text-white">
              Content Strategy Created!
            </h2>
            <p className="text-slate-400">
              Your personalized content plan has been saved. You're ready to start
              creating content.
            </p>
            <div className="flex justify-center gap-4 pt-4">
              <a
                href="/voice"
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-500"
              >
                Set Up Voice Profile
              </a>
              <a
                href="/story"
                className="px-6 py-2 bg-slate-700 text-white rounded-lg hover:bg-slate-600"
              >
                Start Writing
              </a>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
