import { useState, useRef, useEffect } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Bot, Send, X, Loader2, Sparkles } from 'lucide-react'
import { clsx } from 'clsx'
import { apiPost } from '../api/client'

interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

interface AIAssistantProps {
  context: 'scenes' | 'poses' | 'outfits' | 'props' | 'characters' | 'strategy' | 'voice' | 'personas'
  onSuggestion?: (suggestion: string) => void
  className?: string
}

interface ChatResponse {
  response: string
  success: boolean
  error?: string
}

const QUICK_PROMPTS: Record<string, string[]> = {
  scenes: [
    "Suggest a new SUCCESS scene for celebrating a deployment",
    "Create a FAILURE scene showing debugging frustration",
    "Suggest an UNRESOLVED scene about weighing architectural decisions",
  ],
  poses: [
    "Suggest poses for showing deep concentration",
    "Create poses for team collaboration moments",
    "Suggest a new FAILURE pose showing exhaustion",
  ],
  outfits: [
    "Suggest a professional outfit for a conference talk",
    "Create an outfit for a casual Friday coding session",
    "Suggest an outfit with a bold vest color",
  ],
  props: [
    "Suggest tech props for a hardware debugging scene",
    "Create some note props with technical diagrams",
    "Suggest cozy drink props for late night coding",
  ],
  characters: [
    "How can I make the robot more expressive?",
    "Suggest variations for the engineer's appearance",
    "How should the robot look in different sentiments?",
  ],
  strategy: [
    "How can I make my signature thesis more compelling?",
    "Suggest ways to sharpen my positioning statement",
    "What themes would strengthen my content chapters?",
  ],
  voice: [
    "How can I make my tone description more precise?",
    "Suggest signature phrases that feel authentic",
    "What storytelling patterns should I emphasize?",
  ],
  personas: [
    "Help me create a new Researcher persona that gathers context and facts",
    "Generate instructions for an Editor persona focused on clarity and flow",
    "What makes a good auditor persona? Write one for checking technical accuracy",
    "Suggest a persona for handling LinkedIn post formatting and hashtags",
  ],
}

export default function AIAssistant({ context, onSuggestion, className }: AIAssistantProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const chatMutation = useMutation({
    mutationFn: (message: string) =>
      apiPost<ChatResponse>('/ai-assistant/chat', {
        message,
        context,
        agent_type: 'gemini',
      }),
    onSuccess: (data) => {
      if (data.success) {
        setMessages(prev => [
          ...prev,
          { role: 'assistant', content: data.response, timestamp: new Date() }
        ])
        if (onSuggestion && data.response.includes('{')) {
          // Try to extract JSON from response
          try {
            const jsonMatch = data.response.match(/\{[\s\S]*\}/)
            if (jsonMatch) {
              onSuggestion(jsonMatch[0])
            }
          } catch {
            // Ignore JSON parsing errors
          }
        }
      } else {
        setMessages(prev => [
          ...prev,
          { role: 'assistant', content: `Error: ${data.error || 'Failed to get response'}`, timestamp: new Date() }
        ])
      }
    },
    onError: (error: Error) => {
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: `Error: ${error.message}`, timestamp: new Date() }
      ])
    },
  })

  const sendMessage = (message: string) => {
    if (!message.trim()) return

    setMessages(prev => [
      ...prev,
      { role: 'user', content: message, timestamp: new Date() }
    ])
    setInput('')
    chatMutation.mutate(message)
  }

  const quickPrompts = QUICK_PROMPTS[context] || []

  return (
    <div className={clsx('fixed bottom-4 right-4 z-40', className)}>
      {/* Toggle Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="bg-purple-600 text-white p-4 rounded-full shadow-lg hover:bg-purple-500 transition-colors flex items-center gap-2"
        >
          <Sparkles className="w-5 h-5" />
          <span className="font-medium">AI Help</span>
        </button>
      )}

      {/* Chat Panel */}
      {isOpen && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg shadow-2xl w-96 flex flex-col max-h-[600px]">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-zinc-800">
            <div className="flex items-center gap-2">
              <Bot className="w-5 h-5 text-purple-400" />
              <span className="font-semibold text-white">AI Assistant</span>
              <span className="text-xs bg-purple-600/20 text-purple-400 px-2 py-0.5 rounded">
                {context}
              </span>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="p-1 text-zinc-400 hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-[200px] max-h-[350px]">
            {messages.length === 0 ? (
              <div className="text-center text-zinc-500 py-8">
                <Bot className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p className="text-sm">I can help you create new {context}!</p>
                <p className="text-xs mt-1">Try one of the quick prompts below or ask anything.</p>
              </div>
            ) : (
              messages.map((msg, i) => (
                <div
                  key={i}
                  className={clsx(
                    'flex',
                    msg.role === 'user' ? 'justify-end' : 'justify-start'
                  )}
                >
                  <div
                    className={clsx(
                      'max-w-[85%] rounded-lg px-3 py-2 text-sm',
                      msg.role === 'user'
                        ? 'bg-purple-600 text-white'
                        : 'bg-zinc-800 text-zinc-200'
                    )}
                  >
                    <pre className="whitespace-pre-wrap font-sans">{msg.content}</pre>
                  </div>
                </div>
              ))
            )}
            {chatMutation.isPending && (
              <div className="flex justify-start">
                <div className="bg-zinc-800 rounded-lg px-3 py-2 flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin text-purple-400" />
                  <span className="text-sm text-zinc-400">Thinking...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Prompts */}
          {messages.length === 0 && (
            <div className="px-4 pb-2 space-y-1">
              {quickPrompts.map((prompt, i) => (
                <button
                  key={i}
                  onClick={() => sendMessage(prompt)}
                  disabled={chatMutation.isPending}
                  className="w-full text-left px-3 py-2 bg-zinc-800 hover:bg-zinc-700 rounded text-sm text-zinc-300 truncate"
                >
                  {prompt}
                </button>
              ))}
            </div>
          )}

          {/* Input */}
          <div className="p-4 border-t border-zinc-800">
            <div className="flex gap-2">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage(input)}
                placeholder={`Ask about ${context}...`}
                disabled={chatMutation.isPending}
                className="flex-1 px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 text-sm focus:outline-none focus:border-purple-500"
              />
              <button
                onClick={() => sendMessage(input)}
                disabled={!input.trim() || chatMutation.isPending}
                className="px-3 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
