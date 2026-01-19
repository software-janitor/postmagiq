import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchRun, fetchStateLog, fetchTokenBreakdown } from '../api/runs'
import { AlertCircle, Clock, Coins, Hash, ArrowLeft } from 'lucide-react'
import { useEffectiveFlags } from '../stores/flagsStore'

export default function RunDetail() {
  const { runId } = useParams<{ runId: string }>()
  const flags = useEffectiveFlags()
  const showInternals = flags.show_internal_workflow

  const { data: run, isLoading: runLoading } = useQuery({
    queryKey: ['run', runId],
    queryFn: () => fetchRun(runId!),
    enabled: !!runId && showInternals,
  })

  const { data: stateLog } = useQuery({
    queryKey: ['stateLog', runId],
    queryFn: () => fetchStateLog(runId!),
    enabled: !!runId && showInternals,
  })

  const { data: tokens } = useQuery({
    queryKey: ['tokens', runId],
    queryFn: () => fetchTokenBreakdown(runId!),
    enabled: !!runId && showInternals,
  })

  // Regular users should not access this page
  if (!showInternals) {
    return (
      <div className="space-y-6">
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-8 text-center">
          <AlertCircle className="w-12 h-12 text-slate-500 mx-auto mb-4" />
          <h2 className="text-lg font-semibold text-white mb-2">Detailed Run Information</h2>
          <p className="text-slate-400 mb-4">
            Detailed workflow information is not available for your account.
          </p>
          <Link
            to="/runs"
            className="text-blue-400 hover:text-blue-300 flex items-center gap-2 justify-center"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Run History
          </Link>
        </div>
      </div>
    )
  }

  if (runLoading) {
    return <div className="text-slate-400">Loading...</div>
  }

  if (!run) {
    return (
      <div className="text-red-400 flex items-center gap-2">
        <AlertCircle className="w-5 h-5" />
        Run not found
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">{run.story}</h1>
        <span className={`px-3 py-1 rounded-lg ${
          run.status === 'complete' ? 'bg-green-500/20 text-green-400' :
          run.status === 'failed' ? 'bg-red-500/20 text-red-400' :
          'bg-slate-500/20 text-slate-400'
        }`}>
          {run.status}
        </span>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
          <div className="flex items-center gap-2 text-slate-400 text-sm mb-1">
            <Hash className="w-4 h-4" /> Run ID
          </div>
          <div className="text-white font-mono text-sm">{run.run_id}</div>
        </div>
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
          <div className="flex items-center gap-2 text-slate-400 text-sm mb-1">
            <Clock className="w-4 h-4" /> Final State
          </div>
          <div className="text-white">{run.final_state || '-'}</div>
        </div>
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
          <div className="flex items-center gap-2 text-slate-400 text-sm mb-1">
            <Hash className="w-4 h-4" /> Tokens
          </div>
          <div className="text-white">{run.total_tokens.toLocaleString()}</div>
        </div>
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
          <div className="flex items-center gap-2 text-slate-400 text-sm mb-1">
            <Coins className="w-4 h-4" /> Cost
          </div>
          <div className="text-white">${run.total_cost_usd.toFixed(4)}</div>
        </div>
      </div>

      {/* State Log */}
      <div className="bg-slate-800 rounded-lg border border-slate-700">
        <div className="p-4 border-b border-slate-700">
          <h2 className="text-lg font-semibold text-white">State Log</h2>
        </div>
        <div className="p-4 max-h-96 overflow-auto">
          {stateLog?.map((entry, i) => (
            <div key={i} className="flex items-start gap-4 py-2 border-b border-slate-700/50 last:border-0">
              <span className="text-xs text-slate-500 font-mono w-24 flex-shrink-0">
                {new Date(entry.ts).toLocaleTimeString()}
              </span>
              <span className={`text-xs px-2 py-0.5 rounded ${
                entry.event === 'state_enter' ? 'bg-blue-500/20 text-blue-400' :
                entry.event === 'state_complete' ? 'bg-green-500/20 text-green-400' :
                entry.event === 'error' ? 'bg-red-500/20 text-red-400' :
                'bg-slate-500/20 text-slate-400'
              }`}>
                {entry.event}
              </span>
              <span className="text-sm text-white">{entry.state || entry.from_state}</span>
              {entry.transition && (
                <span className="text-sm text-slate-400">→ {entry.transition}</span>
              )}
              {entry.duration_s && (
                <span className="text-xs text-slate-500">{entry.duration_s.toFixed(2)}s</span>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Token & Cost Breakdown by Agent */}
      {tokens && Object.keys(tokens.by_agent).length > 0 && (
        <div className="bg-slate-800 rounded-lg border border-slate-700">
          <div className="p-4 border-b border-slate-700">
            <h2 className="text-lg font-semibold text-white">Usage by Agent</h2>
          </div>
          <div className="p-4">
            <div className="grid grid-cols-3 gap-4">
              {Object.entries(tokens.by_agent)
                .sort((a, b) => (b[1].cost_usd || 0) - (a[1].cost_usd || 0))
                .map(([agent, data]) => (
                <div key={agent} className="bg-slate-900 rounded-lg p-4">
                  <div className="text-sm font-medium text-white mb-2">{agent}</div>
                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between text-slate-400">
                      <span>Input</span>
                      <span>{data.input.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between text-slate-400">
                      <span>Output</span>
                      <span>{data.output.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between text-slate-300 pt-1 border-t border-slate-700">
                      <span>Total Tokens</span>
                      <span>{data.total.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between text-green-400 font-medium">
                      <span>Cost</span>
                      <span>${(data.cost_usd || 0).toFixed(4)}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Cost Breakdown by State */}
      {tokens && Object.keys(tokens.by_state).length > 0 && (
        <div className="bg-slate-800 rounded-lg border border-slate-700">
          <div className="p-4 border-b border-slate-700">
            <h2 className="text-lg font-semibold text-white">Usage by State</h2>
          </div>
          <div className="p-4">
            <div className="grid grid-cols-4 gap-4">
              {Object.entries(tokens.by_state)
                .sort((a, b) => (b[1].cost_usd || 0) - (a[1].cost_usd || 0))
                .map(([state, data]) => (
                <div key={state} className="bg-slate-900 rounded-lg p-3">
                  <div className="text-sm font-medium text-purple-400 mb-1">{state}</div>
                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between text-slate-400">
                      <span>Tokens</span>
                      <span>{(data.tokens || 0).toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between text-green-400 font-medium">
                      <span>Cost</span>
                      <span>${(data.cost_usd || 0).toFixed(4)}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
