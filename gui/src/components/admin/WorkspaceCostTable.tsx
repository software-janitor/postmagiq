/**
 * Workspace Cost Table
 *
 * Sortable table showing cost metrics for all workspaces.
 */

import { useState } from 'react'
import { ChevronUp, ChevronDown } from 'lucide-react'
import { WorkspaceCostSummary } from '../../api/admin'

interface Props {
  workspaces: WorkspaceCostSummary[]
  onWorkspaceClick?: (workspaceId: string) => void
}

type SortKey = 'workspace_name' | 'total_cost_usd' | 'total_tokens' | 'run_count' | 'last_run_at'
type SortDir = 'asc' | 'desc'

export default function WorkspaceCostTable({ workspaces, onWorkspaceClick }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>('total_cost_usd')
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
  }

  const sorted = [...workspaces].sort((a, b) => {
    let aVal: string | number | null = a[sortKey]
    let bVal: string | number | null = b[sortKey]

    // Handle nulls
    if (aVal === null) aVal = ''
    if (bVal === null) bVal = ''

    if (typeof aVal === 'string' && typeof bVal === 'string') {
      return sortDir === 'asc'
        ? aVal.localeCompare(bVal)
        : bVal.localeCompare(aVal)
    }

    const aNum = Number(aVal)
    const bNum = Number(bVal)
    return sortDir === 'asc' ? aNum - bNum : bNum - aNum
  })

  const SortIcon = ({ active, dir }: { active: boolean; dir: SortDir }) => {
    if (!active) return <ChevronDown className="w-4 h-4 opacity-30" />
    return dir === 'asc' ? (
      <ChevronUp className="w-4 h-4" />
    ) : (
      <ChevronDown className="w-4 h-4" />
    )
  }

  const HeaderCell = ({
    label,
    sortable,
    align = 'left',
  }: {
    label: string
    sortable: SortKey
    align?: 'left' | 'right'
  }) => (
    <th
      className={`py-3 px-4 text-${align} text-slate-400 font-medium cursor-pointer hover:text-white transition-colors`}
      onClick={() => handleSort(sortable)}
    >
      <div className={`flex items-center gap-1 ${align === 'right' ? 'justify-end' : ''}`}>
        {label}
        <SortIcon active={sortKey === sortable} dir={sortDir} />
      </div>
    </th>
  )

  if (workspaces.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-slate-400">
        No workspace data available.
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-700">
            <HeaderCell label="Workspace" sortable="workspace_name" />
            <HeaderCell label="Cost" sortable="total_cost_usd" align="right" />
            <HeaderCell label="Tokens" sortable="total_tokens" align="right" />
            <HeaderCell label="Runs" sortable="run_count" align="right" />
            <th className="py-3 px-4 text-right text-slate-400 font-medium">
              Success Rate
            </th>
            <HeaderCell label="Last Run" sortable="last_run_at" align="right" />
          </tr>
        </thead>
        <tbody>
          {sorted.map((ws) => {
            const successRate =
              ws.run_count > 0
                ? ((ws.successful_runs / ws.run_count) * 100).toFixed(1)
                : '-'

            return (
              <tr
                key={ws.workspace_id}
                className="border-b border-slate-700/50 hover:bg-slate-800/50 cursor-pointer transition-colors"
                onClick={() => onWorkspaceClick?.(ws.workspace_id)}
              >
                <td className="py-3 px-4 text-white font-medium">
                  {ws.workspace_name}
                </td>
                <td className="py-3 px-4 text-right text-emerald-400 font-mono">
                  ${ws.total_cost_usd.toFixed(2)}
                </td>
                <td className="py-3 px-4 text-right text-slate-300 font-mono">
                  {ws.total_tokens.toLocaleString()}
                </td>
                <td className="py-3 px-4 text-right text-slate-300">
                  {ws.run_count.toLocaleString()}
                </td>
                <td className="py-3 px-4 text-right">
                  <span
                    className={
                      successRate === '-'
                        ? 'text-slate-500'
                        : Number(successRate) >= 80
                        ? 'text-emerald-400'
                        : Number(successRate) >= 50
                        ? 'text-amber-400'
                        : 'text-red-400'
                    }
                  >
                    {successRate}%
                  </span>
                </td>
                <td className="py-3 px-4 text-right text-slate-400 text-xs">
                  {ws.last_run_at
                    ? new Date(ws.last_run_at).toLocaleDateString()
                    : '-'}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
