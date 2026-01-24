/**
 * Evaluation Dashboard Page
 *
 * Full dashboard with agent performance, costs, trends, and iteration history.
 */

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  fetchAgentComparison,
  fetchCostBreakdown,
  fetchQualityTrend,
  fetchSummaryStats,
} from '../api/eval'
import {
  AgentComparisonChart,
  CostBreakdownChart,
  QualityTrendChart,
  PostIterationLookup,
} from '../components/eval'
import { Activity, DollarSign, TrendingUp, Target, Lock } from 'lucide-react'
import { useEffectiveFlags } from '../stores/flagsStore'

export default function Evaluation() {
  const flags = useEffectiveFlags()

  // Gate evaluation dashboard for owners only
  if (!flags.show_internal_workflow) {
    return (
      <div className="p-6 flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <Lock className="w-12 h-12 text-slate-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-white mb-2">Access Restricted</h2>
          <p className="text-slate-400">
            Evaluation dashboard is available for platform owners only.
          </p>
        </div>
      </div>
    )
  }

  const [periodDays, setPeriodDays] = useState(30)

  // Fetch data
  const { data: agentData, isLoading: agentsLoading } = useQuery({
    queryKey: ['agent-comparison', periodDays],
    queryFn: () => fetchAgentComparison(periodDays),
  })

  const { data: costData, isLoading: costsLoading } = useQuery({
    queryKey: ['cost-breakdown'],
    queryFn: fetchCostBreakdown,
  })

  const { data: trendData, isLoading: trendLoading } = useQuery({
    queryKey: ['quality-trend'],
    queryFn: () => fetchQualityTrend(8),
  })

  const { data: summaryData } = useQuery({
    queryKey: ['summary-stats'],
    queryFn: fetchSummaryStats,
  })

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Evaluation Dashboard</h1>
        <select
          value={periodDays}
          onChange={(e) => setPeriodDays(Number(e.target.value))}
          className="bg-slate-800 border border-slate-700 rounded px-3 py-2 text-white focus:outline-none focus:border-blue-500"
        >
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>

      {/* Summary Cards */}
      {summaryData && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <SummaryCard
            icon={<Activity className="w-5 h-5" />}
            label="Total Runs"
            value={summaryData.total_runs.toString()}
            subtext={`${summaryData.success_rate}% success rate`}
            color="blue"
          />
          <SummaryCard
            icon={<DollarSign className="w-5 h-5" />}
            label="Total Cost"
            value={`$${summaryData.total_cost_usd.toFixed(2)}`}
            subtext={`${summaryData.total_tokens.toLocaleString()} tokens`}
            color="green"
          />
          <SummaryCard
            icon={<Target className="w-5 h-5" />}
            label="Completed"
            value={summaryData.completed_runs.toString()}
            subtext={`of ${summaryData.total_runs} runs`}
            color="amber"
          />
          <SummaryCard
            icon={<TrendingUp className="w-5 h-5" />}
            label="Avg Score"
            value={summaryData.avg_final_score?.toFixed(1) ?? '-'}
            subtext="final quality"
            color="purple"
          />
        </div>
      )}

      {/* Agent Performance */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
        <h2 className="text-lg font-semibold text-white mb-4">
          Agent Performance
        </h2>
        {agentsLoading ? (
          <LoadingState />
        ) : agentData ? (
          <AgentComparisonChart data={agentData} />
        ) : (
          <EmptyState message="No agent data available" />
        )}
      </div>

      {/* Cost and Trend side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Cost Breakdown */}
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
          <h2 className="text-lg font-semibold text-white mb-4">
            Cost Breakdown
          </h2>
          {costsLoading ? (
            <LoadingState />
          ) : costData ? (
            <CostBreakdownChart data={costData} />
          ) : (
            <EmptyState message="No cost data available" />
          )}
        </div>

        {/* Quality Trend */}
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
          <h2 className="text-lg font-semibold text-white mb-4">
            Quality Trend
          </h2>
          {trendLoading ? (
            <LoadingState />
          ) : trendData ? (
            <QualityTrendChart data={trendData} />
          ) : (
            <EmptyState message="No trend data available" />
          )}
        </div>
      </div>

      {/* Post Iteration History */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
        <h2 className="text-lg font-semibold text-white mb-4">
          Post Iteration History
        </h2>
        <PostIterationLookup />
      </div>
    </div>
  )
}

// ============================================================================
// Helper Components
// ============================================================================

interface SummaryCardProps {
  icon: React.ReactNode
  label: string
  value: string
  subtext: string
  color: 'blue' | 'green' | 'amber' | 'purple'
}

function SummaryCard({ icon, label, value, subtext, color }: SummaryCardProps) {
  const colorClasses = {
    blue: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    green: 'bg-green-500/10 text-green-400 border-green-500/20',
    amber: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    purple: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
  }

  return (
    <div
      className={`rounded-lg border p-4 ${colorClasses[color]} bg-slate-800/50`}
    >
      <div className="flex items-center gap-2 mb-2">
        {icon}
        <span className="text-slate-400 text-sm">{label}</span>
      </div>
      <div className="text-2xl font-bold text-white">{value}</div>
      <div className="text-slate-400 text-sm">{subtext}</div>
    </div>
  )
}

function LoadingState() {
  return (
    <div className="h-64 flex items-center justify-center text-slate-400">
      Loading...
    </div>
  )
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="h-64 flex items-center justify-center text-slate-400">
      {message}
    </div>
  )
}
