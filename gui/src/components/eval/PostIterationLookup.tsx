/**
 * Post Iteration Lookup
 *
 * Search for post iterations and display history chart.
 */

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { Search, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { fetchPostIterations } from '../../api/eval'

export default function PostIterationLookup() {
  const [story, setStory] = useState('')
  const [searchQuery, setSearchQuery] = useState('')

  const { data, isLoading, error } = useQuery({
    queryKey: ['post-iterations', searchQuery],
    queryFn: () => fetchPostIterations(searchQuery),
    enabled: !!searchQuery,
    retry: false,
  })

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (story.trim()) {
      setSearchQuery(story.trim())
    }
  }

  const getTrendIcon = () => {
    if (!data || data.iterations.length < 2) {
      return <Minus className="w-4 h-4 text-slate-400" />
    }
    const first = data.iterations[0].final_score
    const last = data.iterations[data.iterations.length - 1].final_score
    if (first === null || last === null) {
      return <Minus className="w-4 h-4 text-slate-400" />
    }
    if (last > first) {
      return <TrendingUp className="w-4 h-4 text-green-400" />
    }
    if (last < first) {
      return <TrendingDown className="w-4 h-4 text-red-400" />
    }
    return <Minus className="w-4 h-4 text-slate-400" />
  }

  return (
    <div className="space-y-4">
      {/* Search Form */}
      <form onSubmit={handleSearch} className="flex gap-2">
        <input
          type="text"
          value={story}
          onChange={(e) => setStory(e.target.value)}
          placeholder="Enter story name (e.g., post_03)"
          className="flex-1 bg-slate-700 border border-slate-600 rounded px-3 py-2 text-white placeholder-slate-400 focus:outline-none focus:border-blue-500"
        />
        <button
          type="submit"
          disabled={!story.trim()}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 disabled:cursor-not-allowed rounded text-white flex items-center gap-2"
        >
          <Search className="w-4 h-4" />
          Search
        </button>
      </form>

      {/* Loading State */}
      {isLoading && (
        <div className="text-slate-400 text-center py-8">
          Loading iterations...
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="text-red-400 text-center py-8">
          No iterations found for "{searchQuery}"
        </div>
      )}

      {/* Results */}
      {data && data.iterations.length > 0 && (
        <div className="space-y-4">
          {/* Header */}
          <div className="flex items-center gap-4">
            <span className="text-white font-medium text-lg">{data.story}</span>
            <span className="text-slate-400">
              {data.iterations.length} iteration
              {data.iterations.length !== 1 ? 's' : ''}
            </span>
            {getTrendIcon()}
          </div>

          {/* Score Chart */}
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data.iterations}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="iteration" stroke="#94a3b8" />
                <YAxis domain={[0, 10]} stroke="#94a3b8" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1e293b',
                    border: '1px solid #334155',
                    borderRadius: '0.375rem',
                  }}
                  formatter={(value) =>
                    typeof value === 'number' ? value.toFixed(1) : 'N/A'
                  }
                />
                <Line
                  type="monotone"
                  dataKey="final_score"
                  stroke="#10b981"
                  strokeWidth={2}
                  dot={{ fill: '#10b981', r: 4 }}
                  name="Final Score"
                  connectNulls
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Iterations Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700">
                  <th className="text-left py-2 text-slate-400">Iter</th>
                  <th className="text-left py-2 text-slate-400">Run ID</th>
                  <th className="text-right py-2 text-slate-400">Score</th>
                  <th className="text-right py-2 text-slate-400">Cost</th>
                  <th className="text-left py-2 text-slate-400">Improvements</th>
                </tr>
              </thead>
              <tbody>
                {data.iterations.map((iter) => (
                  <tr
                    key={iter.run_id}
                    className="border-b border-slate-700/50"
                  >
                    <td className="py-2 text-white">{iter.iteration}</td>
                    <td className="py-2 text-slate-300 font-mono text-xs">
                      {iter.run_id.length > 20
                        ? `${iter.run_id.substring(0, 20)}...`
                        : iter.run_id}
                    </td>
                    <td className="py-2 text-right text-white">
                      {iter.final_score?.toFixed(1) ?? '-'}
                    </td>
                    <td className="py-2 text-right text-slate-300">
                      ${iter.total_cost.toFixed(2)}
                    </td>
                    <td className="py-2 text-slate-400 truncate max-w-xs">
                      {iter.improvements || '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!searchQuery && !isLoading && (
        <div className="text-slate-400 text-center py-8">
          Enter a story name to view iteration history.
        </div>
      )}
    </div>
  )
}
