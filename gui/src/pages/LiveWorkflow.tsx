import { useState, useCallback, useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useWorkflowStore } from '../stores/workflowStore'
import { Play, Square, SkipForward, Pause, PlayCircle, AlertCircle, CheckCircle2, Zap, Circle } from 'lucide-react'
import StateMachineCanvas from '../components/workflow/StateMachineCanvas'
import ApprovalDialog from '../components/workflow/ApprovalDialog'
import WorkflowConfigSelector from '../components/WorkflowConfigSelector'
import { useWebSocket } from '../hooks/useWebSocket'
import { startWorkflow, abortWorkflow, stepWorkflow, pauseWorkflow, resumeWorkflow } from '../api/workflow'
import { apiGet } from '../api/client'
import { clsx } from 'clsx'

export default function LiveWorkflow() {
  const {
    running,
    paused,
    currentRunId,
    currentState,
    currentStory,
    tokens,
    cost,
    awaitingApproval,
    approvalContent,
    setAwaitingApproval,
    events,
    error,
  } = useWorkflowStore()
  const eventLogRef = useRef<HTMLDivElement>(null)
  const [story, setStory] = useState('post_03')
  const [selectedConfig, setSelectedConfig] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [localError, setLocalError] = useState<string | null>(null)

  // Fetch workflow config for the state machine canvas
  const { data: configData } = useQuery({
    queryKey: ['workflow-config'],
    queryFn: () => apiGet<{ config: string }>('/config'),
    staleTime: 60000, // Cache for 1 minute
  })

  // Auto-scroll event log
  useEffect(() => {
    if (eventLogRef.current) {
      eventLogRef.current.scrollTop = eventLogRef.current.scrollHeight
    }
  }, [events])

  // Connect WebSocket for live updates
  useWebSocket()

  const handleStart = useCallback(async () => {
    setLoading(true)
    setLocalError(null)
    try {
      await startWorkflow(story, undefined, selectedConfig || undefined)
    } catch (e) {
      setLocalError(e instanceof Error ? e.message : 'Failed to start workflow')
    } finally {
      setLoading(false)
    }
  }, [story, selectedConfig])

  const handleAbort = useCallback(async () => {
    setLoading(true)
    setLocalError(null)
    try {
      await abortWorkflow()
    } catch (e) {
      setLocalError(e instanceof Error ? e.message : 'Failed to abort workflow')
    } finally {
      setLoading(false)
    }
  }, [])

  const handleStep = useCallback(async () => {
    setLoading(true)
    setLocalError(null)
    try {
      // For step mode, we need to know which step to run
      // Default to 'draft' if no story is running
      const step = currentState || 'draft'
      await stepWorkflow(currentStory || story, step, currentRunId || undefined)
    } catch (e) {
      setLocalError(e instanceof Error ? e.message : 'Failed to step workflow')
    } finally {
      setLoading(false)
    }
  }, [story, currentStory, currentState, currentRunId])

  const handlePause = useCallback(async () => {
    setLoading(true)
    setLocalError(null)
    try {
      await pauseWorkflow()
    } catch (e) {
      setLocalError(e instanceof Error ? e.message : 'Failed to pause workflow')
    } finally {
      setLoading(false)
    }
  }, [])

  const handleResume = useCallback(async () => {
    setLoading(true)
    setLocalError(null)
    try {
      await resumeWorkflow()
    } catch (e) {
      setLocalError(e instanceof Error ? e.message : 'Failed to resume workflow')
    } finally {
      setLoading(false)
    }
  }, [])

  return (
    <div className="h-full flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Live Workflow</h1>
        <div className="flex items-center gap-4">
          {!running && (
            <>
              <input
                type="text"
                value={story}
                onChange={(e) => setStory(e.target.value)}
                placeholder="Story ID (e.g., post_03)"
                className="px-3 py-2 bg-slate-700 text-white rounded-lg border border-slate-600 focus:border-blue-500 focus:outline-none"
              />
              <WorkflowConfigSelector
                value={selectedConfig}
                onChange={setSelectedConfig}
                className="w-48"
              />
            </>
          )}
          {running ? (
            <>
              {paused ? (
                <button
                  onClick={handleResume}
                  disabled={loading}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-500 flex items-center gap-2 disabled:opacity-50"
                >
                  <PlayCircle className="w-4 h-4" /> Resume
                </button>
              ) : (
                <button
                  onClick={handlePause}
                  disabled={loading}
                  className="px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-500 flex items-center gap-2 disabled:opacity-50"
                >
                  <Pause className="w-4 h-4" /> Pause
                </button>
              )}
              <button
                onClick={handleAbort}
                disabled={loading}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-500 flex items-center gap-2 disabled:opacity-50"
              >
                <Square className="w-4 h-4" /> Abort
              </button>
            </>
          ) : (
            <button
              onClick={handleStart}
              disabled={loading || !story}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-500 flex items-center gap-2 disabled:opacity-50"
            >
              <Play className="w-4 h-4" /> Start
            </button>
          )}
          <button
            onClick={handleStep}
            disabled={loading || (running && !paused)}
            className="px-4 py-2 bg-slate-700 text-white rounded-lg hover:bg-slate-600 flex items-center gap-2 disabled:opacity-50"
          >
            <SkipForward className="w-4 h-4" /> Step
          </button>
        </div>
      </div>

      {(localError || error) && (
        <div className="bg-red-900/50 border border-red-700 text-red-200 px-4 py-2 rounded-lg">
          {localError || error}
        </div>
      )}

      {awaitingApproval && (
        <ApprovalDialog
          content={approvalContent}
          onClose={() => setAwaitingApproval(false, null)}
        />
      )}

      <div className="flex-1 grid grid-cols-3 gap-4">
        {/* State Machine Canvas */}
        <div className="col-span-2 bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
          <StateMachineCanvas config={configData?.config} />
        </div>

        {/* Metrics Panel */}
        <div className="space-y-4">
          <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
            <h3 className="text-sm font-medium text-slate-400 mb-3">Run Status</h3>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-slate-400">Status</span>
                <span className={clsx(
                  'font-medium',
                  paused ? 'text-yellow-400' : running ? 'text-green-400' : 'text-slate-400'
                )}>
                  {paused ? 'Paused' : running ? 'Running' : 'Idle'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Run ID</span>
                <span className="text-white font-mono text-sm">
                  {currentRunId || '-'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Current State</span>
                <span className="text-white">{currentState || '-'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Tokens</span>
                <span className="text-white">{tokens.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Cost</span>
                <span className="text-white">${cost.toFixed(4)}</span>
              </div>
            </div>
          </div>

          <div className="bg-slate-800 rounded-lg border border-slate-700 p-4 flex-1">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-medium text-slate-400">Live Log</h3>
              <span className="text-xs text-slate-500">{events.length} events</span>
            </div>
            <div
              ref={eventLogRef}
              className="h-64 overflow-auto text-xs space-y-2"
            >
              {events.length === 0 ? (
                <div className="text-slate-500">Waiting for workflow...</div>
              ) : (
                events.map((event) => (
                  <div key={event.id} className="flex gap-2">
                    <div className="flex-shrink-0 mt-0.5">
                      {event.type.includes('error') ? (
                        <AlertCircle className="w-3 h-3 text-red-400" />
                      ) : event.type.includes('complete') ? (
                        <CheckCircle2 className="w-3 h-3 text-green-400" />
                      ) : event.type.includes('start') || event.type.includes('enter') ? (
                        <Zap className="w-3 h-3 text-blue-400" />
                      ) : (
                        <Circle className="w-2 h-2 text-slate-500 mt-0.5" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <span className={clsx(
                        event.type.includes('error') && 'text-red-300',
                        event.type.includes('complete') && 'text-green-300',
                        !event.type.includes('error') && !event.type.includes('complete') && 'text-slate-300',
                      )}>
                        {event.message}
                      </span>
                      <span className="text-slate-600 ml-2">
                        {new Date(event.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
