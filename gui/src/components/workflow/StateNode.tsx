import { memo } from 'react'
import { Handle, Position, NodeProps } from '@xyflow/react'
import { clsx } from 'clsx'

interface StateNodeData {
  label: string
  type: 'initial' | 'fan-out' | 'single' | 'orchestrator-task' | 'human-approval' | 'terminal'
  agents?: string[]
  isActive?: boolean
  isComplete?: boolean
  error?: boolean
}

const STATE_COLORS: Record<string, string> = {
  'initial': 'border-indigo-500 bg-indigo-500/10',
  'fan-out': 'border-violet-500 bg-violet-500/10',
  'single': 'border-blue-500 bg-blue-500/10',
  'orchestrator-task': 'border-amber-500 bg-amber-500/10',
  'human-approval': 'border-emerald-500 bg-emerald-500/10',
  'terminal': 'border-red-500 bg-red-500/10',
}

function StateNode({ data, selected }: NodeProps) {
  const nodeData = data as unknown as StateNodeData
  const colorClass = STATE_COLORS[nodeData.type] || STATE_COLORS['initial']

  return (
    <div
      className={clsx(
        'px-4 py-3 rounded-lg border-2 min-w-[140px] transition-all',
        colorClass,
        selected && 'ring-2 ring-blue-400 ring-offset-2 ring-offset-slate-900',
        nodeData.isActive && 'animate-pulse shadow-lg',
        nodeData.isComplete && 'opacity-60',
        nodeData.error && 'border-red-500'
      )}
    >
      {nodeData.type !== 'initial' && (
        <Handle
          type="target"
          position={Position.Top}
          className="!bg-slate-400 !w-3 !h-3 !border-2 !border-slate-900"
        />
      )}

      <div className="text-center">
        <div className="text-sm font-semibold text-white">{nodeData.label}</div>
        <div className="text-xs text-slate-400 mt-1">{nodeData.type}</div>
        {nodeData.agents && (
          <div className="text-xs text-slate-500 mt-1">
            {nodeData.agents.join(', ')}
          </div>
        )}
      </div>

      {nodeData.type !== 'terminal' && (
        <Handle
          type="source"
          position={Position.Bottom}
          className="!bg-slate-400 !w-3 !h-3 !border-2 !border-slate-900"
        />
      )}
    </div>
  )
}

export default memo(StateNode)
