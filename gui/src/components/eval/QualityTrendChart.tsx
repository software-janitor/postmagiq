/**
 * Quality Trend Chart
 *
 * Displays line chart of quality scores over time.
 */

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import { QualityTrend } from '../../api/eval'

interface Props {
  data: QualityTrend
}

export default function QualityTrendChart({ data }: Props) {
  // Calculate average quality
  const qualityValues = data.weeks
    .filter((w) => w.avg_quality !== null)
    .map((w) => w.avg_quality as number)
  const avgQuality =
    qualityValues.length > 0
      ? qualityValues.reduce((sum, q) => sum + q, 0) / qualityValues.length
      : 0

  // Total runs
  const totalRuns = data.weeks.reduce((sum, w) => sum + w.runs, 0)

  if (data.weeks.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-slate-400">
        No trend data available.
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Line Chart */}
      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data.weeks}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis
              dataKey="week"
              stroke="#94a3b8"
              tickFormatter={(val) => {
                // Show just week number from "2026-02" format
                const parts = val?.split('-')
                return parts?.[1] ? `W${parts[1]}` : val
              }}
            />
            <YAxis domain={[0, 10]} stroke="#94a3b8" />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1e293b',
                border: '1px solid #334155',
                borderRadius: '0.375rem',
              }}
              labelFormatter={(label) => `Week ${label}`}
              formatter={(value, name) => {
                if (name === 'avg_quality' && typeof value === 'number') {
                  return value.toFixed(1)
                }
                return value
              }}
            />
            {avgQuality > 0 && (
              <ReferenceLine
                y={avgQuality}
                stroke="#666"
                strokeDasharray="3 3"
                label={{
                  value: `Avg: ${avgQuality.toFixed(1)}`,
                  fill: '#94a3b8',
                  fontSize: 12,
                }}
              />
            )}
            <Line
              type="monotone"
              dataKey="avg_quality"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={{ fill: '#3b82f6', r: 4 }}
              name="Avg Quality"
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Summary Stats */}
      <div className="flex justify-between text-sm border-t border-slate-700 pt-4">
        <div>
          <span className="text-slate-400">Average: </span>
          <span className="text-white font-medium">
            {avgQuality > 0 ? avgQuality.toFixed(1) : '-'}
          </span>
        </div>
        <div>
          <span className="text-slate-400">Total runs: </span>
          <span className="text-white font-medium">{totalRuns}</span>
        </div>
        <div>
          <span className="text-slate-400">Weeks: </span>
          <span className="text-white font-medium">{data.weeks.length}</span>
        </div>
      </div>
    </div>
  )
}
