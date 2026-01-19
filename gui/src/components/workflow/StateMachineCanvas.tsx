import { useMemo, useEffect } from 'react'
import {
  ReactFlow,
  Node,
  Edge,
  Background,
  Controls,
  useNodesState,
  useEdgesState,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import yaml from 'js-yaml'
import StateNode from './StateNode'

interface StateMachineCanvasProps {
  config?: string  // YAML config string
}

interface WorkflowConfig {
  states: Record<string, {
    type: string
    agent?: string      // Single agent (for single/orchestrator-task)
    agents?: string[]   // Multiple agents (for fan-out)
    transitions: Record<string, string>
  }>
}

const nodeTypes = {
  stateNode: StateNode,
}

// Auto-layout positions
function calculatePositions(states: string[]): Record<string, { x: number; y: number }> {
  const positions: Record<string, { x: number; y: number }> = {}
  const verticalGap = 120
  const horizontalCenter = 300

  // Identify terminal states (usually go at the bottom)
  const terminalStates: string[] = []
  const regularStates: string[] = []

  states.forEach(state => {
    if (state === 'complete' || state === 'halt') {
      terminalStates.push(state)
    } else {
      regularStates.push(state)
    }
  })

  // Position regular states vertically
  regularStates.forEach((state, index) => {
    positions[state] = { x: horizontalCenter, y: index * verticalGap }
  })

  // Position terminal states at the bottom, side by side
  const bottomY = regularStates.length * verticalGap
  terminalStates.forEach((state, index) => {
    const offset = (index - (terminalStates.length - 1) / 2) * 200
    positions[state] = { x: horizontalCenter + offset, y: bottomY }
  })

  return positions
}

function parseConfigToGraph(configYaml: string): { nodes: Node[]; edges: Edge[] } {
  try {
    const config = yaml.load(configYaml) as WorkflowConfig

    if (!config?.states) {
      return { nodes: [], edges: [] }
    }

    const stateNames = Object.keys(config.states)
    const positions = calculatePositions(stateNames)

    // Create nodes
    const nodes: Node[] = stateNames.map(stateName => {
      const state = config.states[stateName]
      // Normalize agent/agents to always be an array for display
      const agents = state.agents || (state.agent ? [state.agent] : undefined)
      return {
        id: stateName,
        position: positions[stateName] || { x: 0, y: 0 },
        type: 'stateNode',
        data: {
          label: stateName,
          type: state.type,
          agents,
          error: stateName === 'halt',
        },
      }
    })

    // Create edges from transitions
    const edges: Edge[] = []
    let edgeId = 0

    Object.entries(config.states).forEach(([stateName, state]) => {
      if (state.transitions) {
        Object.entries(state.transitions).forEach(([condition, targetState]) => {
          edges.push({
            id: `e${edgeId++}`,
            source: stateName,
            target: targetState,
            label: condition,
            style: condition.includes('failure') || condition === 'feedback' || condition === 'retry'
              ? { strokeDasharray: '5,5' }
              : undefined,
          })
        })
      }
    })

    return { nodes, edges }
  } catch (e) {
    console.error('Failed to parse workflow config:', e)
    return { nodes: [], edges: [] }
  }
}

// Fallback default state machine - matches workflow_config.yaml
const defaultNodes: Node[] = [
  { id: 'start', position: { x: 300, y: 0 }, data: { label: 'start', type: 'initial' }, type: 'stateNode' },
  { id: 'story-review', position: { x: 300, y: 100 }, data: { label: 'story-review', type: 'single', agents: ['gemini'] }, type: 'stateNode' },
  { id: 'story-feedback', position: { x: 500, y: 150 }, data: { label: 'story-feedback', type: 'human-approval' }, type: 'stateNode' },
  { id: 'story-process', position: { x: 300, y: 200 }, data: { label: 'story-process', type: 'single', agents: ['claude'] }, type: 'stateNode' },
  { id: 'draft', position: { x: 300, y: 300 }, data: { label: 'draft', type: 'fan-out', agents: ['claude', 'gemini'] }, type: 'stateNode' },
  { id: 'cross-audit', position: { x: 300, y: 400 }, data: { label: 'cross-audit', type: 'fan-out', agents: ['claude', 'gemini'] }, type: 'stateNode' },
  { id: 'synthesize', position: { x: 300, y: 500 }, data: { label: 'synthesize', type: 'orchestrator-task', agents: ['claude'] }, type: 'stateNode' },
  { id: 'final-audit', position: { x: 300, y: 600 }, data: { label: 'final-audit', type: 'fan-out', agents: ['claude', 'gemini'] }, type: 'stateNode' },
  { id: 'human-approval', position: { x: 300, y: 700 }, data: { label: 'human-approval', type: 'human-approval' }, type: 'stateNode' },
  { id: 'complete', position: { x: 200, y: 820 }, data: { label: 'complete', type: 'terminal' }, type: 'stateNode' },
  { id: 'halt', position: { x: 400, y: 820 }, data: { label: 'halt', type: 'terminal', error: true }, type: 'stateNode' },
]

const defaultEdges: Edge[] = [
  { id: 'e1', source: 'start', target: 'story-review' },
  { id: 'e2', source: 'story-review', target: 'story-process', label: 'proceed' },
  { id: 'e3', source: 'story-review', target: 'story-feedback', label: 'retry', style: { strokeDasharray: '5,5' } },
  { id: 'e4', source: 'story-review', target: 'halt', label: 'halt', style: { strokeDasharray: '5,5' } },
  { id: 'e5', source: 'story-feedback', target: 'story-process', label: 'approved' },
  { id: 'e6', source: 'story-feedback', target: 'story-review', label: 'feedback', style: { strokeDasharray: '5,5' } },
  { id: 'e7', source: 'story-feedback', target: 'halt', label: 'abort', style: { strokeDasharray: '5,5' } },
  { id: 'e8', source: 'story-process', target: 'draft', label: 'success' },
  { id: 'e9', source: 'story-process', target: 'story-review', label: 'failure', style: { strokeDasharray: '5,5' } },
  { id: 'e10', source: 'draft', target: 'cross-audit', label: 'all_success' },
  { id: 'e11', source: 'draft', target: 'halt', label: 'all_failure', style: { strokeDasharray: '5,5' } },
  { id: 'e12', source: 'cross-audit', target: 'synthesize', label: 'all_success' },
  { id: 'e13', source: 'cross-audit', target: 'draft', label: 'all_failure', style: { strokeDasharray: '5,5' } },
  { id: 'e14', source: 'synthesize', target: 'final-audit', label: 'success' },
  { id: 'e15', source: 'synthesize', target: 'cross-audit', label: 'failure', style: { strokeDasharray: '5,5' } },
  { id: 'e16', source: 'final-audit', target: 'human-approval', label: 'all_success' },
  { id: 'e17', source: 'final-audit', target: 'synthesize', label: 'all_failure', style: { strokeDasharray: '5,5' } },
  { id: 'e18', source: 'human-approval', target: 'complete', label: 'approved' },
  { id: 'e19', source: 'human-approval', target: 'synthesize', label: 'feedback', style: { strokeDasharray: '5,5' } },
  { id: 'e20', source: 'human-approval', target: 'halt', label: 'abort', style: { strokeDasharray: '5,5' } },
]

export default function StateMachineCanvas({ config }: StateMachineCanvasProps) {
  // Parse config into nodes and edges
  const { parsedNodes, parsedEdges } = useMemo(() => {
    if (config) {
      const { nodes, edges } = parseConfigToGraph(config)
      if (nodes.length > 0) {
        return { parsedNodes: nodes, parsedEdges: edges }
      }
    }
    return { parsedNodes: defaultNodes, parsedEdges: defaultEdges }
  }, [config])

  const [nodes, setNodes, onNodesChange] = useNodesState(parsedNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(parsedEdges)

  // Update nodes/edges when config changes
  useEffect(() => {
    setNodes(parsedNodes)
    setEdges(parsedEdges)
  }, [parsedNodes, parsedEdges, setNodes, setEdges])

  return (
    <div className="h-full w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        className="bg-slate-900"
      >
        <Background color="#475569" gap={20} />
        <Controls className="bg-slate-800 border-slate-700" />
      </ReactFlow>
    </div>
  )
}
