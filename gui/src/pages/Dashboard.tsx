import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Play, History, PenTool, AlertCircle } from 'lucide-react'
import { clsx } from 'clsx'
import { fetchRuns } from '../api/runs'
import { useThemeClasses } from '../hooks/useThemeClasses'
import ThemeIcon from '../components/ThemeIcon'
import { useEffectiveFlags } from '../stores/flagsStore'

export default function Dashboard() {
  const theme = useThemeClasses()
  const flags = useEffectiveFlags()
  const showInternals = flags.show_internal_workflow
  const showLiveWorkflow = flags.show_live_workflow

  const { data: runs, isLoading, error } = useQuery({
    queryKey: ['runs'],
    queryFn: fetchRuns,
  })

  const recentRuns = runs?.slice(0, 5) || []

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <ThemeIcon className={clsx('w-8 h-8', theme.textPrimary)} />
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
      </div>

      {/* Quick Actions */}
      <div className={clsx('grid grid-cols-1 gap-4', showLiveWorkflow ? 'md:grid-cols-3' : 'md:grid-cols-2')}>
        <Link
          to="/story"
          className={clsx('p-6 bg-zinc-900 rounded-lg border border-zinc-800 transition-colors group', theme.borderHover)}
        >
          <PenTool className={clsx('w-8 h-8 mb-3', theme.textPrimary)} />
          <h3 className={clsx('text-lg font-semibold text-white', `group-hover:${theme.textPrimary.replace('text-', '')}`)}>
            Brew New Content
          </h3>
          <p className="text-sm text-zinc-400 mt-1">
            Distill your next story
          </p>
        </Link>

        {showLiveWorkflow && (
          <Link
            to="/workflow"
            className={clsx('p-6 bg-zinc-900 rounded-lg border border-zinc-800 transition-colors group', theme.borderHover)}
          >
            <Play className={clsx('w-8 h-8 mb-3', theme.textSecondary)} />
            <h3 className={clsx('text-lg font-semibold text-white', `group-hover:${theme.textSecondary.replace('text-', '')}`)}>
              Live Transmutation
            </h3>
            <p className="text-sm text-zinc-400 mt-1">
              Watch the alchemy unfold
            </p>
          </Link>
        )}

        <Link
          to="/runs"
          className="p-6 bg-zinc-900 rounded-lg border border-zinc-800 hover:border-zinc-500 transition-colors group"
        >
          <History className="w-8 h-8 text-zinc-400 mb-3" />
          <h3 className="text-lg font-semibold text-white group-hover:text-zinc-300">
            Brew History
          </h3>
          <p className="text-sm text-zinc-400 mt-1">
            Review past transmutations
          </p>
        </Link>
      </div>

      {/* Recent Runs */}
      <div className="bg-zinc-900 rounded-lg border border-zinc-800">
        <div className="p-4 border-b border-zinc-800">
          <h2 className="text-lg font-semibold text-white">Recent Brews</h2>
        </div>

        {isLoading ? (
          <div className="p-8 text-center text-zinc-400">Loading...</div>
        ) : error ? (
          <div className="p-8 text-center text-red-400 flex items-center justify-center gap-2">
            <AlertCircle className="w-5 h-5" />
            Failed to load brews
          </div>
        ) : recentRuns.length === 0 ? (
          <div className="p-8 text-center text-zinc-400">
            No brews yet. Distill your first content!
          </div>
        ) : (
          <div className="divide-y divide-zinc-800">
            {recentRuns.map((run) => {
              const content = (
                <div className="flex items-center justify-between">
                  <div>
                    <span className="font-medium text-white">{run.story}</span>
                    {showInternals && (
                      <span className="text-zinc-400 text-sm ml-2">
                        {run.run_id}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-4 text-sm">
                    <span className={clsx('px-2 py-1 rounded',
                      run.status === 'complete' && clsx(theme.bgMuted, theme.textPrimary),
                      run.status === 'failed' && 'bg-red-500/20 text-red-400',
                      run.status === 'running' && 'bg-blue-500/20 text-blue-400',
                      !['complete', 'failed', 'running'].includes(run.status) && 'bg-zinc-500/20 text-zinc-400'
                    )}>
                      {run.status}
                    </span>
                    {showInternals && (
                      <span className="text-zinc-400">
                        ${run.total_cost_usd?.toFixed(3) || '0.000'}
                      </span>
                    )}
                  </div>
                </div>
              )

              // For regular users, don't link to run details
              return showInternals ? (
                <Link
                  key={run.run_id}
                  to={`/runs/${run.run_id}`}
                  className="block p-4 hover:bg-zinc-800/50 transition-colors cursor-pointer"
                >
                  {content}
                </Link>
              ) : (
                <div key={run.run_id} className="block p-4">
                  {content}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
