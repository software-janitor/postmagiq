import { useEffect, useCallback } from 'react'
import { useWorkflowStore, ModelMetrics } from '../stores/workflowStore'
import { useDevStore } from '../stores/devStore'
import { getAccessToken } from '../stores/authStore'

// Singleton WebSocket instance - shared across all components
let globalWs: WebSocket | null = null
let reconnectTimeout: number | null = null
let connectionCount = 0  // Track how many components are using the connection

interface WebSocketMessage {
  type: string
  run_id?: string
  story?: string
  current_state?: string
  previous_state?: string
  final_state?: string
  total_tokens?: number
  total_cost_usd?: number
  duration_s?: number
  content?: string
  prompt?: string
  input_path?: string
  decision?: string
  feedback?: string
  error?: string
  timestamp?: string
  agent?: string
  output_preview?: string
  rule?: string
  last_score?: number
  reason?: string
  skip_to?: string
  message?: string
  state?: string
  session_id?: string
  agent_metrics?: Record<string, ModelMetrics>

  // LLM message fields (DEV_MODE)
  model?: string
  system_prompt?: string
  user_message?: string
  tokens?: {
    input: number
    output: number
    total: number
  }
  duration_ms?: number
  context_window?: number
  context_usage_percent?: number
  context_remaining?: number
  context_warning?: string
  success?: boolean
}

// Human-readable descriptions for workflow events
const EVENT_DESCRIPTIONS: Record<string, (msg: WebSocketMessage) => string> = {
  'workflow:started': (msg) => `Starting workflow for ${msg.story}`,
  'workflow:complete': (msg) => `Workflow complete! Final state: ${msg.final_state}`,
  'workflow:error': (msg) => `Error: ${msg.error}`,
  'workflow:aborted': () => 'Workflow aborted by user',
  'workflow:paused': (msg) => `Paused at: ${msg.current_state}`,
  'workflow:resumed': (msg) => `Resumed from: ${msg.current_state}`,
  'state:enter': (msg) => `Entering state: ${msg.current_state}`,
  'state:exit': (msg) => `Exiting state: ${msg.previous_state}`,
  'agent:start': (msg) => `Running ${msg.agent || 'agent'}...`,
  'agent:complete': (msg) => `${msg.agent || 'Agent'} finished`,
  'agent:output': (msg) => msg.output_preview ? `Output: ${msg.output_preview.slice(0, 100)}...` : 'Agent produced output',
  'approval:requested': () => 'Waiting for your approval...',
  'approval:received': () => 'Approval received, continuing...',
  'draft:generated': () => 'Draft generated',
  'audit:complete': (msg) => `Audit complete: ${msg.decision || 'decision pending'}`,
  'synthesis:complete': () => 'Final synthesis complete',
  'circuit_break:detected': (msg) => `Loop detected (${msg.rule}), last score: ${msg.last_score || 'N/A'}`,
  'circuit_break:auto_skip': (msg) => `Auto-proceeding: ${msg.reason}`,
}

export function useWebSocket() {
  const {
    setRunning,
    setPaused,
    setAborted,
    setCurrentRun,
    setCurrentState,
    setAwaitingApproval,
    updateMetrics,
    updateModelMetrics,
    addEvent,
    setOutput,
    setError,
    reset,
  } = useWorkflowStore()

  const connect = useCallback(() => {
    // Already connected - don't create another
    if (globalWs && globalWs.readyState === WebSocket.OPEN) {
      return
    }

    // Already connecting - don't create another
    if (globalWs && globalWs.readyState === WebSocket.CONNECTING) {
      return
    }

    // Get access token for authentication
    const token = getAccessToken()
    if (!token) {
      console.warn('WebSocket: No access token, skipping connection')
      return
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/api/ws?token=${encodeURIComponent(token)}`

    globalWs = new WebSocket(wsUrl)

    globalWs.onopen = () => {
      console.log('WebSocket connected (singleton)')
      addEvent({
        type: 'system',
        message: 'Connected to workflow server',
      })
    }

    globalWs.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data)
        handleMessage(message)
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e)
      }
    }

    globalWs.onclose = () => {
      console.log('WebSocket disconnected, reconnecting...')
      globalWs = null
      // Only reconnect if there are still components using the connection
      if (connectionCount > 0) {
        reconnectTimeout = window.setTimeout(() => {
          connect()
        }, 2000)
      }
    }

    globalWs.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
  }, [addEvent])

  const handleMessage = useCallback((message: WebSocketMessage) => {
    // Generate human-readable message
    const descFn = EVENT_DESCRIPTIONS[message.type]
    const description = descFn ? descFn(message) : `Event: ${message.type}`

    // Add event to log
    addEvent({
      type: message.type,
      state: message.current_state,
      message: description,
      details: message.content || message.output_preview || message.feedback,
    })

    // Handle state updates
    switch (message.type) {
      case 'workflow:started':
        // Reset all metrics from previous run to avoid accumulation
        reset()
        setCurrentRun(message.run_id ?? null, message.story ?? null)
        setRunning(true)
        setError(null)
        break

      case 'workflow:complete':
        setRunning(false)
        setCurrentState(message.final_state ?? null)
        if (message.total_tokens !== undefined && message.total_cost_usd !== undefined) {
          updateMetrics(message.total_tokens, message.total_cost_usd)
        }
        // If workflow ended in halt state, treat it as an error
        if (message.final_state === 'halt') {
          setError(message.error || 'Workflow halted due to errors')
        }
        break

      case 'workflow:error':
        setRunning(false)
        setError(message.error ?? 'Unknown error')
        console.error('Workflow error:', message.error)
        break

      case 'workflow:aborted':
        setAborted(true)
        break

      case 'workflow:paused':
        setPaused(true)
        setCurrentState(message.current_state ?? null)
        break

      case 'workflow:resumed':
        setPaused(false)
        setCurrentState(message.current_state ?? null)
        break

      case 'state:enter':
        setCurrentState(message.current_state ?? null)
        break

      case 'approval:requested':
        setAwaitingApproval(true, message.content, message.prompt)
        break

      case 'approval:received':
        setAwaitingApproval(false, null, null)
        break

      // Handle output events
      case 'output:review':
        if (message.content) setOutput('reviewResult', message.content)
        break

      case 'output:processed':
        if (message.content) setOutput('processedStory', message.content)
        break

      case 'output:draft':
        if (message.content && message.agent) {
          setOutput('drafts', { [message.agent]: message.content })
        }
        break

      case 'output:audit':
        if (message.content && message.agent) {
          setOutput('audits', { [message.agent]: message.content })
        }
        break

      case 'output:final-audit':
        if (message.content && message.agent) {
          setOutput('finalAudits', { [message.agent]: message.content })
        }
        break

      case 'output:final':
        if (message.content) setOutput('finalPost', message.content)
        break

      case 'session:resume':
        addEvent({
          type: 'session',
          message: message.message || `Resuming session ${message.session_id}`,
          details: `State: ${message.state}, Session: ${message.session_id}`,
        })
        break

      case 'session:new':
        addEvent({
          type: 'session',
          message: message.message || 'Starting new session',
          details: `State: ${message.state}`,
        })
        break

      case 'metrics:update':
        // Per-agent metrics from state completion
        if (message.agent_metrics) {
          updateModelMetrics(message.state || '', message.agent_metrics)
        }
        break

      // DEV_MODE: LLM message events
      case 'llm:request':
        useDevStore.getState().addMessage({
          type: 'request',
          timestamp: message.timestamp || new Date().toISOString(),
          runId: message.run_id || '',
          state: message.state || '',
          agent: message.agent || '',
          model: message.model || '',
          systemPrompt: message.system_prompt,
          userMessage: message.user_message,
          contextWindow: message.context_window || 0,
          contextUsagePercent: message.context_usage_percent,
          contextWarning: message.context_warning,
        })
        break

      case 'llm:response':
        useDevStore.getState().addMessage({
          type: 'response',
          timestamp: message.timestamp || new Date().toISOString(),
          runId: message.run_id || '',
          state: message.state || '',
          agent: message.agent || '',
          model: message.model || '',
          content: message.content,
          tokens: message.tokens,
          durationMs: message.duration_ms,
          contextWindow: message.context_window || 0,
          contextUsagePercent: message.context_usage_percent,
          contextRemaining: message.context_remaining,
          contextWarning: message.context_warning,
          success: message.success,
          error: message.error,
        })
        break
    }
  }, [setRunning, setPaused, setAborted, setCurrentRun, setCurrentState, setAwaitingApproval, updateMetrics, updateModelMetrics, addEvent, setOutput, setError, reset])

  useEffect(() => {
    connectionCount++
    connect()

    return () => {
      connectionCount--
      // Only close if no components are using the connection
      if (connectionCount === 0) {
        if (reconnectTimeout) {
          clearTimeout(reconnectTimeout)
          reconnectTimeout = null
        }
        if (globalWs) {
          globalWs.close()
          globalWs = null
        }
      }
    }
  }, [connect])

  return globalWs
}
