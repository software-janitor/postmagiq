import { useState, useRef, useEffect } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Send, Loader2, Sparkles, Check, RefreshCw } from 'lucide-react'
import { clsx } from 'clsx'
import { apiPost } from '../api/client'
import { GeneratedPlan } from '../api/onboarding'

interface StrategyMessage {
  role: 'user' | 'assistant'
  content: string
}

interface ChatState {
  messages: StrategyMessage[]
  extracted_info: Record<string, unknown>
  ready_to_create: boolean
  turn_count: number
}

interface ChatResponse {
  assistant_message: string
  state: ChatState
  ready_to_create: boolean
  success: boolean
  error?: string
}

interface StrategyPlanResponse {
  plan: GeneratedPlan
  success: boolean
  error?: string
}

export interface ExtractedStrategy {
  strategy_type?: string
  positioning?: string
  signature_thesis?: string
  target_audience?: string
  content_style?: string
  post_frequency?: string
  platforms?: string[]
  chapter_themes?: string[]
  intellectual_enemies?: string[]
  target_roles?: string[]
  posts_per_week?: number
  voice_constraints?: string
  series_length_weeks?: number
  post_length?: string
}

interface Props {
  onStrategyReady: (payload: { strategy: ExtractedStrategy; plan?: GeneratedPlan }) => void
}

export default function StrategyChatPanel({ onStrategyReady }: Props) {
  const [messages, setMessages] = useState<StrategyMessage[]>([])
  const [input, setInput] = useState('')
  const [chatState, setChatState] = useState<ChatState | null>(null)
  const [isReady, setIsReady] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Start conversation mutation
  const startMutation = useMutation({
    mutationFn: () => apiPost<ChatResponse>('/ai-assistant/strategy/start'),
    onSuccess: (data) => {
      if (data.success) {
        setMessages([{ role: 'assistant', content: data.assistant_message }])
        setChatState(data.state)
        setIsReady(data.ready_to_create)
      }
    },
  })

  // Send message mutation
  const sendMutation = useMutation({
    mutationFn: (message: string) =>
      apiPost<ChatResponse>('/ai-assistant/strategy/message', {
        message,
        state: chatState,
      }),
    onSuccess: (data) => {
      if (data.success) {
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', content: data.assistant_message },
        ])
        setChatState(data.state)
        setIsReady(data.ready_to_create)
      }
    },
  })

  const planMutation = useMutation({
    mutationFn: (strategy: ExtractedStrategy) =>
      apiPost<StrategyPlanResponse>('/ai-assistant/strategy/plan', { strategy }),
    onSuccess: (data, strategy) => {
      if (data.success) {
        onStrategyReady({ strategy, plan: data.plan })
      } else {
        onStrategyReady({ strategy })
      }
    },
    onError: (_error, strategy) => {
      onStrategyReady({ strategy })
    },
  })

  // Extract strategy mutation
  const extractMutation = useMutation({
    mutationFn: () =>
      apiPost<{ strategy: ExtractedStrategy; success: boolean }>(
        '/ai-assistant/strategy/extract',
        { state: chatState }
      ),
    onSuccess: (data) => {
      if (data.success && data.strategy) {
        planMutation.mutate(data.strategy)
      }
    },
  })

  // Start conversation on mount
  useEffect(() => {
    if (messages.length === 0 && !startMutation.isPending) {
      startMutation.mutate()
    }
  }, [])

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = () => {
    if (!input.trim() || sendMutation.isPending) return

    const userMessage = input.trim()
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }])
    sendMutation.mutate(userMessage)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleUseStrategy = () => {
    extractMutation.mutate()
  }

  const handleRestart = () => {
    setMessages([])
    setChatState(null)
    setIsReady(false)
    startMutation.mutate()
  }

  return (
    <div className="flex flex-col h-full bg-zinc-900 rounded-lg border border-zinc-800 overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-zinc-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-amber-400" />
          <h3 className="font-semibold text-white">AI Strategy Assistant</h3>
        </div>
        <button
          onClick={handleRestart}
          className="p-2 text-zinc-400 hover:text-white hover:bg-zinc-800 rounded-lg"
          title="Start Over"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={clsx(
              'max-w-[85%] rounded-lg p-3',
              msg.role === 'user'
                ? 'ml-auto bg-amber-600 text-white'
                : 'bg-zinc-800 text-zinc-100'
            )}
          >
            <p className="whitespace-pre-wrap text-sm">{msg.content}</p>
          </div>
        ))}

        {(startMutation.isPending || sendMutation.isPending) && (
          <div className="flex items-center gap-2 text-zinc-400">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span className="text-sm">Thinking...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Ready to create banner */}
      {isReady && (
        <div className="px-4 py-3 bg-green-900/30 border-t border-green-800/50">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-green-400">
              <Check className="w-4 h-4" />
              <span className="text-sm">Strategy ready to create</span>
            </div>
            <button
              onClick={handleUseStrategy}
              disabled={extractMutation.isPending || planMutation.isPending}
              className="px-4 py-1.5 bg-green-600 text-white text-sm rounded-lg hover:bg-green-500 disabled:opacity-50 flex items-center gap-2"
            >
              {extractMutation.isPending || planMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Generating...
                </>
              ) : (
                'Use This Strategy'
              )}
            </button>
          </div>
        </div>
      )}

      {/* Input */}
      <div className="p-4 border-t border-zinc-800">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your message..."
            className="flex-1 px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white text-sm resize-none focus:outline-none focus:border-amber-600"
            rows={2}
            disabled={sendMutation.isPending}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || sendMutation.isPending}
            className="px-4 bg-amber-600 text-white rounded-lg hover:bg-amber-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
        <p className="text-xs text-zinc-500 mt-2">
          Press Enter to send, Shift+Enter for new line
        </p>
        {!isReady && messages.length > 1 && (
          <button
            onClick={handleUseStrategy}
            disabled={extractMutation.isPending || planMutation.isPending}
            className="mt-3 text-xs text-amber-400 hover:text-amber-300 disabled:opacity-50"
          >
            Use the current conversation to generate a plan
          </button>
        )}
      </div>
    </div>
  )
}
