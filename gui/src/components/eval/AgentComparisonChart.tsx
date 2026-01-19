/**
 * Agent Performance Comparison Chart
 *
 * Displays bar chart for overall scores and radar chart for detailed metrics.
 */

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Legend,
} from 'recharts'
import { AgentComparison } from '../../api/eval'

interface Props {
  data: AgentComparison
}

const AGENT_COLORS: Record<string, string> = {
  claude: '#3b82f6',
  gemini: '#10b981',
  codex: '#f59e0b',
  ollama: '#8b5cf6',
}

export default function AgentComparisonChart({ data }: Props) {
  // Transform for radar chart
  const radarData = [
    {
      metric: 'Overall',
      ...Object.fromEntries(data.agents.map((a) => [a.name, a.avg_score])),
    },
    {
      metric: 'Hook',
      ...Object.fromEntries(data.agents.map((a) => [a.name, a.avg_hook || 0])),
    },
    {
      metric: 'Specifics',
      ...Object.fromEntries(
        data.agents.map((a) => [a.name, a.avg_specifics || 0])
      ),
    },
    {
      metric: 'Voice',
      ...Object.fromEntries(data.agents.map((a) => [a.name, a.avg_voice || 0])),
    },
  ]

  if (data.agents.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-slate-400">
        No agent data available for the selected period.
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Bar Chart for Overall Scores */}
      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data.agents}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="name" stroke="#94a3b8" />
            <YAxis domain={[0, 10]} stroke="#94a3b8" />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1e293b',
                border: '1px solid #334155',
                borderRadius: '0.375rem',
              }}
              labelStyle={{ color: '#f8fafc' }}
            />
            <Bar dataKey="avg_score" fill="#3b82f6" name="Avg Score" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Radar Chart for Detailed Breakdown */}
      {data.agents.length >= 2 && (
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart data={radarData}>
              <PolarGrid stroke="#334155" />
              <PolarAngleAxis dataKey="metric" stroke="#94a3b8" />
              <PolarRadiusAxis
                angle={30}
                domain={[0, 10]}
                stroke="#94a3b8"
                tickCount={6}
              />
              {data.agents.map((agent) => (
                <Radar
                  key={agent.name}
                  name={agent.name}
                  dataKey={agent.name}
                  stroke={AGENT_COLORS[agent.name] || '#666'}
                  fill={AGENT_COLORS[agent.name] || '#666'}
                  fillOpacity={0.2}
                />
              ))}
              <Legend />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1e293b',
                  border: '1px solid #334155',
                  borderRadius: '0.375rem',
                }}
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Summary Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-700">
              <th className="text-left py-2 text-slate-400">Agent</th>
              <th className="text-right py-2 text-slate-400">Overall</th>
              <th className="text-right py-2 text-slate-400">Hook</th>
              <th className="text-right py-2 text-slate-400">Specifics</th>
              <th className="text-right py-2 text-slate-400">Voice</th>
              <th className="text-right py-2 text-slate-400">Samples</th>
            </tr>
          </thead>
          <tbody>
            {data.agents.map((agent) => (
              <tr key={agent.name} className="border-b border-slate-700/50">
                <td className="py-2 text-white font-medium">{agent.name}</td>
                <td className="py-2 text-right text-white">
                  {agent.avg_score.toFixed(1)}
                </td>
                <td className="py-2 text-right text-slate-300">
                  {agent.avg_hook?.toFixed(1) ?? '-'}
                </td>
                <td className="py-2 text-right text-slate-300">
                  {agent.avg_specifics?.toFixed(1) ?? '-'}
                </td>
                <td className="py-2 text-right text-slate-300">
                  {agent.avg_voice?.toFixed(1) ?? '-'}
                </td>
                <td className="py-2 text-right text-slate-400">
                  {agent.sample_size}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
