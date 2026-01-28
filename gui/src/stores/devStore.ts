import { create } from 'zustand'

// Dev mode enabled via environment variable (passed through docker-compose)
// Defaults to true in docker-compose.yml for development
export const DEV_MODE_ENABLED = import.meta.env.VITE_DEV_MODE === 'true'

export interface LLMMessage {
  id: string
  type: 'request' | 'response'
  timestamp: string
  runId: string
  state: string
  agent: string
  model: string

  // Request-specific
  systemPrompt?: string
  userMessage?: string

  // Response-specific
  content?: string
  tokens?: {
    input: number
    output: number
    total: number
  }
  durationMs?: number
  success?: boolean
  error?: string

  // Context usage (both)
  contextWindow: number
  contextUsagePercent?: number
  contextRemaining?: number
  contextWarning?: string
}

interface DevState {
  // State
  enabled: boolean
  isOpen: boolean
  messages: LLMMessage[]

  // Actions
  setEnabled: (enabled: boolean) => void
  setIsOpen: (isOpen: boolean) => void
  toggleOpen: () => void
  addMessage: (message: Omit<LLMMessage, 'id'>) => void
  clearMessages: () => void
}

let messageCounter = 0

export const useDevStore = create<DevState>()((set, get) => ({
  enabled: DEV_MODE_ENABLED,
  isOpen: false,
  messages: [],

  setEnabled: (enabled) => set({ enabled }),

  setIsOpen: (isOpen) => set({ isOpen }),

  toggleOpen: () => set((state) => ({ isOpen: !state.isOpen })),

  addMessage: (message) => {
    // Only add if dev mode is enabled
    if (!get().enabled) return

    const newMessage: LLMMessage = {
      ...message,
      id: `llm-${++messageCounter}`,
    }

    set((state) => ({
      // Keep last 100 messages to avoid memory issues
      messages: [...state.messages, newMessage].slice(-100),
    }))
  },

  clearMessages: () => set({ messages: [] }),
}))

// Helper hook to check if dev console should be shown
export function useDevModeEnabled(): boolean {
  return useDevStore((state) => state.enabled)
}
