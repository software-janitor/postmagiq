import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { fetchRuns } from '../api/runs'
import { AlertCircle, ChevronRight } from 'lucide-react'
import { useEffectiveFlags } from '../stores/flagsStore'

export default function RunHistory() {
  const flags = useEffectiveFlags()
  const showInternals = flags.show_internal_workflow

  const { data: runs, isLoading, error } = useQuery({
    queryKey: ['runs'],
    queryFn: fetchRuns,
  })

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">Run History</h1>

      <div className="bg-slate-800 rounded-lg border border-slate-700">
        {isLoading ? (
          <div className="p-8 text-center text-slate-400">Loading runs...</div>
        ) : error ? (
          <div className="p-8 text-center text-red-400 flex items-center justify-center gap-2">
            <AlertCircle className="w-5 h-5" />
            Failed to load runs
          </div>
        ) : !runs?.length ? (
          <div className="p-8 text-center text-slate-400">
            No runs found. Start a workflow to see history.
          </div>
        ) : (
          <table className="w-full">
            <thead className="border-b border-slate-700">
              <tr className="text-left text-sm text-slate-400">
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">Story</th>
                <th className="px-4 py-3">Status</th>
                {showInternals && <th className="px-4 py-3">Final State</th>}
                {showInternals && <th className="px-4 py-3">Tokens</th>}
                {showInternals && <th className="px-4 py-3">Cost</th>}
                <th className="px-4 py-3">Credits</th>
                <th className="px-4 py-3">Duration</th>
                {showInternals && <th className="px-4 py-3"></th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {runs.map((run) => (
                <tr key={run.run_id} className="hover:bg-slate-700/50">
                  <td className="px-4 py-3 text-sm text-slate-300">
                    {run.started_at ? new Date(run.started_at).toLocaleDateString() : '-'}
                  </td>
                  <td className="px-4 py-3 text-white">{run.story}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-sm ${
                      run.status === 'complete' ? 'bg-green-500/20 text-green-400' :
                      run.status === 'failed' ? 'bg-red-500/20 text-red-400' :
                      run.status === 'running' ? 'bg-blue-500/20 text-blue-400' :
                      'bg-slate-500/20 text-slate-400'
                    }`}>
                      {run.status}
                    </span>
                  </td>
                  {showInternals && <td className="px-4 py-3 text-slate-300">{run.final_state || '-'}</td>}
                  {showInternals && <td className="px-4 py-3 text-slate-300">{run.total_tokens.toLocaleString()}</td>}
                  {showInternals && <td className="px-4 py-3 text-slate-300">${run.total_cost_usd.toFixed(4)}</td>}
                  <td className="px-4 py-3 text-slate-300">
                    {run.credits != null ? run.credits.toLocaleString() : '-'}
                  </td>
                  <td className="px-4 py-3 text-slate-300">
                    {run.started_at && run.completed_at
                      ? `${Math.round((new Date(run.completed_at).getTime() - new Date(run.started_at).getTime()) / 1000 / 60)}m`
                      : run.started_at
                      ? 'In progress'
                      : '-'}
                  </td>
                  {showInternals && (
                    <td className="px-4 py-3">
                      <Link
                        to={`/runs/${run.run_id}`}
                        className="text-blue-400 hover:text-blue-300 flex items-center gap-1"
                      >
                        View <ChevronRight className="w-4 h-4" />
                      </Link>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
