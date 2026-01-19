export interface RunSummary {
  run_id: string
  story: string
  status: 'running' | 'complete' | 'failed' | 'halted'
  started_at: string
  completed_at: string | null
  total_tokens: number
  total_cost_usd: number
  final_state: string | null
  config_hash: string | null
}

export interface StateLogEntry {
  ts: string
  run_id: string
  event: string
  state?: string
  type?: string
  transition?: string
  from_state?: string
  to_state?: string
  duration_s?: number
  outputs?: Record<string, unknown>
  error?: string
}

export interface TokenBreakdown {
  total_input: number
  total_output: number
  total_cost_usd: number
  by_agent: Record<string, { input: number; output: number; total: number; cost_usd?: number }>
  by_state: Record<string, { tokens: number; cost_usd?: number }>
}

export interface ArtifactInfo {
  path: string
  name: string
  type: 'draft' | 'audit' | 'final' | 'input' | 'other'
  size_bytes: number
  modified_at: string
}

export interface WorkflowStatus {
  running: boolean
  run_id: string | null
  current_state: string | null
  story: string | null
  started_at: string | null
  awaiting_approval: boolean
}

export interface ConfigValidationResult {
  valid: boolean
  errors: string[]
  warnings: string[]
}
