/**
 * Admin Analytics Dashboard
 *
 * SaaS owner-only dashboard for viewing metrics across all workspaces.
 */

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { BarChart3, RefreshCw, Loader2, AlertCircle } from 'lucide-react'
import { clsx } from 'clsx'
import {
  fetchWorkspaceSummaries,
  fetchTimeline,
  fetchAgentBreakdown,
  refreshDailyCosts,
} from '../../api/admin'
import { WorkspaceCostTable, CostTimelineChart, AgentCostPieChart } from '../../components/admin'
import { useThemeClasses } from '../../hooks/useThemeClasses'

export default function Analytics() {
  const theme = useThemeClasses()
  const queryClient = useQueryClient()
  const [daysBack, setDaysBack] = useState(30)
  const [selectedWorkspace, setSelectedWorkspace] = useState<string | undefined>(undefined)

  // Fetch workspace summaries
  const {
    data: summaries,
    isLoading: loadingSummaries,
    error: summariesError,
  } = useQuery({
    queryKey: ['admin-summaries', daysBack],
    queryFn: () => fetchWorkspaceSummaries(daysBack),
  })

  // Fetch timeline
  const {
    data: timeline,
    isLoading: loadingTimeline,
  } = useQuery({
    queryKey: ['admin-timeline', daysBack, selectedWorkspace],
    queryFn: () => fetchTimeline(daysBack, selectedWorkspace),
  })

  // Fetch agent breakdown
  const {
    data: agentBreakdown,
    isLoading: loadingAgents,
  } = useQuery({
    queryKey: ['admin-agents', daysBack, selectedWorkspace],
    queryFn: () => fetchAgentBreakdown(daysBack, selectedWorkspace),
  })

  // Refresh mutation
  const refreshMutation = useMutation({
    mutationFn: () => refreshDailyCosts(daysBack, selectedWorkspace),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-summaries'] })
      queryClient.invalidateQueries({ queryKey: ['admin-timeline'] })
      queryClient.invalidateQueries({ queryKey: ['admin-agents'] })
    },
  })

  const handleWorkspaceClick = (workspaceId: string) => {
    setSelectedWorkspace(selectedWorkspace === workspaceId ? undefined : workspaceId)
  }

  const handleRefresh = () => {
    refreshMutation.mutate()
  }

  if (summariesError) {
    return (
      <div className="flex items-center justify-center h-64 text-red-400">
        <AlertCircle className="w-6 h-6 mr-2" />
        Failed to load analytics. Make sure you have owner permissions.
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <BarChart3 className={clsx('w-8 h-8', theme.textPrimary)} />
          <h1 className="text-2xl font-bold text-white">Admin Analytics</h1>
        </div>
        <div className="flex items-center gap-4">
          {/* Date Range Selector */}
          <select
            value={daysBack}
            onChange={(e) => setDaysBack(Number(e.target.value))}
            className="bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
            <option value={365}>Last year</option>
          </select>

          {/* Refresh Button */}
          <button
            onClick={handleRefresh}
            disabled={refreshMutation.isPending}
            className={clsx(
              'flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition-colors',
              'bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-50'
            )}
          >
            {refreshMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4" />
            )}
            Refresh Data
          </button>
        </div>
      </div>

      {/* Workspace Filter Indicator */}
      {selectedWorkspace && summaries && (
        <div className="flex items-center gap-2 text-sm">
          <span className="text-slate-400">Filtered by:</span>
          <span className="px-3 py-1 bg-blue-600/20 text-blue-400 rounded-full">
            {summaries.workspaces.find((w) => w.workspace_id === selectedWorkspace)?.workspace_name}
          </span>
          <button
            onClick={() => setSelectedWorkspace(undefined)}
            className="text-slate-400 hover:text-white text-xs underline"
          >
            Clear filter
          </button>
        </div>
      )}

      {/* Summary Cards */}
      {loadingSummaries ? (
        <div className="flex items-center justify-center h-32">
          <Loader2 className="w-8 h-8 animate-spin text-slate-400" />
        </div>
      ) : summaries ? (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-4">
            <div className="text-slate-400 text-sm">Total Cost</div>
            <div className="text-2xl font-bold text-emerald-400 mt-1">
              ${summaries.total_cost_usd.toFixed(2)}
            </div>
          </div>
          <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-4">
            <div className="text-slate-400 text-sm">Total Tokens</div>
            <div className="text-2xl font-bold text-white mt-1">
              {summaries.total_tokens.toLocaleString()}
            </div>
          </div>
          <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-4">
            <div className="text-slate-400 text-sm">Total Runs</div>
            <div className="text-2xl font-bold text-white mt-1">
              {summaries.total_runs.toLocaleString()}
            </div>
          </div>
          <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-4">
            <div className="text-slate-400 text-sm">Workspaces</div>
            <div className="text-2xl font-bold text-white mt-1">
              {summaries.workspaces.length}
            </div>
          </div>
        </div>
      ) : null}

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Timeline Chart */}
        <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Cost Timeline</h2>
          {loadingTimeline ? (
            <div className="flex items-center justify-center h-48">
              <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
            </div>
          ) : timeline ? (
            <CostTimelineChart data={timeline.data} />
          ) : null}
        </div>

        {/* Agent Breakdown */}
        <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Cost by Agent</h2>
          {loadingAgents ? (
            <div className="flex items-center justify-center h-48">
              <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
            </div>
          ) : agentBreakdown ? (
            <AgentCostPieChart
              agents={agentBreakdown.agents}
              totalCost={agentBreakdown.total_cost_usd}
            />
          ) : null}
        </div>
      </div>

      {/* Workspace Table */}
      <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Workspace Costs</h2>
        {loadingSummaries ? (
          <div className="flex items-center justify-center h-48">
            <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
          </div>
        ) : summaries ? (
          <WorkspaceCostTable
            workspaces={summaries.workspaces}
            onWorkspaceClick={handleWorkspaceClick}
          />
        ) : null}
      </div>

      {/* Refresh Status */}
      {refreshMutation.isSuccess && (
        <div className="fixed bottom-4 right-4 bg-green-600 text-white px-4 py-2 rounded-lg shadow-lg">
          Data refreshed: {refreshMutation.data?.records_updated} records updated
        </div>
      )}
    </div>
  )
}
