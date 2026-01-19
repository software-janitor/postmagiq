/**
 * Cost Breakdown Chart
 *
 * Displays pie chart and table of costs by agent.
 */

import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from 'recharts'
import { CostBreakdown } from '../../api/eval'

interface Props {
  data: CostBreakdown
}

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444']

export default function CostBreakdownChart({ data }: Props) {
  const chartData = data.agents.map((agent, index) => ({
    name: agent.name,
    value: agent.total_cost,
    color: COLORS[index % COLORS.length],
  }))

  if (data.agents.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-slate-400">
        No cost data available.
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Total Cost */}
      <div className="text-center">
        <span className="text-3xl font-bold text-white">
          ${data.total_cost_usd.toFixed(2)}
        </span>
        <span className="text-slate-400 ml-2">total spent</span>
      </div>

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
            {data.agents.map((agent) => (
              <tr key={agent.name} className="border-b border-slate-700/50">
                <td className="py-2 text-white">{agent.name}</td>
                <td className="py-2 text-right text-slate-300">
                  {agent.invocations.toLocaleString()}
                </td>
                <td className="py-2 text-right text-slate-300">
                  {agent.total_tokens.toLocaleString()}
                </td>
                <td className="py-2 text-right text-white">
                  ${agent.total_cost.toFixed(2)}
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
