import { create } from 'zustand'

export interface WorkflowEvent {
  id: string
  type: string
  timestamp: string
  state?: string
  message: string
  details?: string
}

export interface WorkflowOutputs {
  reviewResult?: string
  processedStory?: string
  drafts?: Record<string, string>
  audits?: Record<string, string>
  finalAudits?: Record<string, string>
  finalPost?: string
}

export interface ModelMetrics {
  tokens: number
  tokens_input: number
  tokens_output: number
  cost_usd: number
}

export interface StateMetrics {
  tokens: number
  cost_usd: number
}

interface WorkflowState {
  running: boolean
  paused: boolean
  aborted: boolean
  currentRunId: string | null
  currentState: string | null
  currentStory: string | null
  awaitingApproval: boolean
  approvalContent: string | null
  approvalPrompt: string | null
  tokens: number
  cost: number
  modelMetrics: Record<string, ModelMetrics>  // Per-model breakdown
  stateMetrics: Record<string, StateMetrics>  // Per-state/persona breakdown
  events: WorkflowEvent[]
  outputs: WorkflowOutputs
  error: string | null

  // Actions
  setRunning: (running: boolean) => void
  setPaused: (paused: boolean) => void
  setAborted: (aborted: boolean) => void
  setCurrentRun: (runId: string | null, story: string | null) => void
  setCurrentState: (state: string | null) => void
  setAwaitingApproval: (awaiting: boolean, content?: string | null, prompt?: string | null) => void
  updateMetrics: (tokens: number, cost: number) => void
  updateModelMetrics: (state: string, agentMetrics: Record<string, ModelMetrics>) => void
  addEvent: (event: Omit<WorkflowEvent, 'id' | 'timestamp'>) => void
  setOutput: (key: keyof WorkflowOutputs, value: string | Record<string, string>) => void
  setOutputs: (outputs: WorkflowOutputs) => void
  setError: (error: string | null) => void
  reset: () => void
}

let eventCounter = 0
// Track recent event signatures to prevent duplicates (type + message within 1 second)
const recentEvents = new Map<string, number>()
const DEDUP_WINDOW_MS = 1000

function isDuplicateEvent(type: string, message: string): boolean {
  const signature = `${type}:${message}`
  const now = Date.now()
  const lastSeen = recentEvents.get(signature)

  if (lastSeen && (now - lastSeen) < DEDUP_WINDOW_MS) {
    return true
  }

  recentEvents.set(signature, now)

  // Clean up old entries to prevent memory growth
  if (recentEvents.size > 100) {
    for (const [key, time] of recentEvents.entries()) {
      if (now - time > DEDUP_WINDOW_MS) {
        recentEvents.delete(key)
      }
    }
  }

  return false
}

export const useWorkflowStore = create<WorkflowState>((set) => ({
  running: false,
  paused: false,
  aborted: false,
  currentRunId: null,
  currentState: null,
  currentStory: null,
  awaitingApproval: false,
  approvalContent: null,
  approvalPrompt: null,
  tokens: 0,
  cost: 0,
  modelMetrics: {},
  stateMetrics: {},
  events: [],
  outputs: {},
  error: null,

  setRunning: (running) => set({ running, paused: running ? false : false }),

  setPaused: (paused) => set({ paused }),

  setAborted: (aborted) => set({ aborted, running: false }),

  setCurrentRun: (runId, story) => set({
    currentRunId: runId,
    currentStory: story,
    running: runId !== null,
    paused: false,
    aborted: false,
  }),

  setCurrentState: (state) => set({ currentState: state }),

  setAwaitingApproval: (awaiting, content, prompt) => set({
    awaitingApproval: awaiting,
    approvalContent: content ?? null,
    approvalPrompt: prompt ?? null,
  }),

  updateMetrics: (tokens, cost) => set({ tokens, cost }),

  updateModelMetrics: (stateName, agentMetrics) => set((currentState) => {
    // Merge new agent metrics, accumulating totals
    const updatedModels = { ...currentState.modelMetrics }
    const updatedStates = { ...currentState.stateMetrics }
    let totalTokens = currentState.tokens
    let totalCost = currentState.cost
    let stateTokens = 0
    let stateCost = 0

    for (const [agent, metrics] of Object.entries(agentMetrics)) {
      // Update per-model metrics
      if (updatedModels[agent]) {
        updatedModels[agent] = {
          tokens: updatedModels[agent].tokens + metrics.tokens,
          tokens_input: updatedModels[agent].tokens_input + metrics.tokens_input,
          tokens_output: updatedModels[agent].tokens_output + metrics.tokens_output,
          cost_usd: updatedModels[agent].cost_usd + metrics.cost_usd,
        }
      } else {
        updatedModels[agent] = metrics
      }
      totalTokens += metrics.tokens
      totalCost += metrics.cost_usd
      stateTokens += metrics.tokens
      stateCost += metrics.cost_usd
    }

    // Update per-state metrics
    if (stateName) {
      if (updatedStates[stateName]) {
        updatedStates[stateName] = {
          tokens: updatedStates[stateName].tokens + stateTokens,
          cost_usd: updatedStates[stateName].cost_usd + stateCost,
        }
      } else {
        updatedStates[stateName] = { tokens: stateTokens, cost_usd: stateCost }
      }
    }

    return {
      modelMetrics: updatedModels,
      stateMetrics: updatedStates,
      tokens: totalTokens,
      cost: totalCost
    }
  }),

  addEvent: (event) => {
    // Deduplicate events that arrive within the same window
    if (isDuplicateEvent(event.type, event.message)) {
      return
    }
    set((state) => ({
      events: [...state.events, {
        ...event,
        id: `event-${++eventCounter}`,
        timestamp: new Date().toISOString(),
      }].slice(-100), // Keep last 100 events
    }))
  },

  setOutput: (key, value) => set((state) => {
    // For drafts, audits, and finalAudits, merge with existing values instead of replacing
    if ((key === 'drafts' || key === 'audits' || key === 'finalAudits') && typeof value === 'object') {
      const existing = state.outputs[key] as Record<string, string> | undefined
      return {
        outputs: {
          ...state.outputs,
          [key]: { ...existing, ...value },
        },
      }
    }
    return {
      outputs: { ...state.outputs, [key]: value },
    }
  }),

  setOutputs: (outputs) => set({ outputs }),

  setError: (error) => set({ error }),

  reset: () => {
    eventCounter = 0
    recentEvents.clear()
    return set({
      running: false,
      paused: false,
      aborted: false,
      currentRunId: null,
      currentState: null,
      currentStory: null,
      awaitingApproval: false,
      approvalContent: null,
      approvalPrompt: null,
      tokens: 0,
      cost: 0,
      modelMetrics: {},
      stateMetrics: {},
      events: [],
      outputs: {},
      error: null,
    })
  },
}))
