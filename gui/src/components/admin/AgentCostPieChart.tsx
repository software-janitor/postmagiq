/**
 * Agent Cost Pie Chart
 *
 * Pie chart showing cost breakdown by agent.
 */

import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from 'recharts'
import { AgentCostBreakdown } from '../../api/admin'

interface Props {
  agents: AgentCostBreakdown[]
  totalCost: number
}

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444', '#06b6d4', '#ec4899']

export default function AgentCostPieChart({ agents, totalCost }: Props) {
  const chartData = agents.map((agent, index) => ({
    name: agent.agent,
    value: agent.total_cost_usd,
    tokens: agent.total_tokens,
    invocations: agent.invocation_count,
    color: COLORS[index % COLORS.length],
    percentage: totalCost > 0 ? (agent.total_cost_usd / totalCost) * 100 : 0,
  }))

  if (agents.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-slate-400">
        No agent data available.
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Pie Chart */}
      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={40}
              outerRadius={70}
              dataKey="value"
              label={({ name, percentage }) =>
                `${name}: ${percentage?.toFixed(0) || 0}%`
              }
              labelLine={false}
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: number) => `$${value.toFixed(2)}`}
              contentStyle={{
                backgroundColor: '#1e293b',
                border: '1px solid #334155',
                borderRadius: '0.375rem',
              }}
            />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Details Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-700">
              <th className="text-left py-2 text-slate-400">Agent</th>
              <th className="text-right py-2 text-slate-400">Calls</th>
              <th className="text-right py-2 text-slate-400">Tokens</th>
              <th className="text-right py-2 text-slate-400">Cost</th>
              <th className="text-right py-2 text-slate-400">%</th>
            </tr>
          </thead>
          <tbody>
            {chartData.map((agent) => (
              <tr key={agent.name} className="border-b border-slate-700/50">
                <td className="py-2 text-white flex items-center gap-2">
                  <span
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: agent.color }}
                  />
                  {agent.name}
                </td>
                <td className="py-2 text-right text-slate-300">
                  {agent.invocations.toLocaleString()}
                </td>
                <td className="py-2 text-right text-slate-300">
                  {agent.tokens.toLocaleString()}
                </td>
                <td className="py-2 text-right text-emerald-400 font-mono">
                  ${agent.value.toFixed(2)}
                </td>
                <td className="py-2 text-right text-slate-400">
                  {agent.percentage.toFixed(1)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
