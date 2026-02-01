/**
 * Cost Timeline Chart
 *
 * Line chart showing daily cost trend using Recharts.
 */

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart,
} from 'recharts'
import { DailyCostPoint } from '../../api/admin'

interface Props {
  data: DailyCostPoint[]
}

export default function CostTimelineChart({ data }: Props) {
  // Calculate totals
  const totalCost = data.reduce((sum, d) => sum + d.total_cost_usd, 0)
  const totalRuns = data.reduce((sum, d) => sum + d.run_count, 0)
  const avgDailyCost = data.length > 0 ? totalCost / data.length : 0

  if (data.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-slate-400">
        No timeline data available.
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Chart */}
      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <defs>
              <linearGradient id="costGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis
              dataKey="date"
              stroke="#94a3b8"
              tickFormatter={(val) => {
                const date = new Date(val)
                return `${date.getMonth() + 1}/${date.getDate()}`
              }}
              tick={{ fontSize: 11 }}
            />
            <YAxis
              stroke="#94a3b8"
              tickFormatter={(val) => `$${val.toFixed(0)}`}
              tick={{ fontSize: 11 }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1e293b',
                border: '1px solid #334155',
                borderRadius: '0.375rem',
              }}
              labelFormatter={(label) => new Date(label).toLocaleDateString()}
              formatter={(value: number, name: string) => {
                if (name === 'total_cost_usd') return [`$${value.toFixed(2)}`, 'Cost']
                if (name === 'run_count') return [value, 'Runs']
                return [value, name]
              }}
            />
            <Area
              type="monotone"
              dataKey="total_cost_usd"
              stroke="#10b981"
              strokeWidth={2}
              fill="url(#costGradient)"
              name="total_cost_usd"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-3 gap-4 text-sm border-t border-slate-700 pt-4">
        <div className="text-center">
          <div className="text-slate-400">Total Cost</div>
          <div className="text-xl font-bold text-emerald-400">
            ${totalCost.toFixed(2)}
          </div>
        </div>
        <div className="text-center">
          <div className="text-slate-400">Avg Daily</div>
          <div className="text-xl font-bold text-white">
            ${avgDailyCost.toFixed(2)}
          </div>
        </div>
        <div className="text-center">
          <div className="text-slate-400">Total Runs</div>
          <div className="text-xl font-bold text-white">
            {totalRuns.toLocaleString()}
          </div>
        </div>
      </div>
    </div>
  )
}
