/**
 * Admin Analytics API client
 * SaaS owner-only endpoints for viewing metrics across all workspaces.
 */

import { apiGet, apiPost } from './client'

// ============================================================================
// Types
// ============================================================================

export interface WorkspaceCostSummary {
  workspace_id: string
  workspace_name: string
  total_cost_usd: number
  total_tokens: number
  run_count: number
  successful_runs: number
  failed_runs: number
  last_run_at: string | null
}

export interface WorkspaceSummariesResponse {
  workspaces: WorkspaceCostSummary[]
  total_cost_usd: number
  total_tokens: number
  total_runs: number
}

export interface DailyCostPoint {
  date: string
  total_cost_usd: number
  total_tokens: number
  run_count: number
}

export interface TimelineResponse {
  data: DailyCostPoint[]
  days_back: number
}

export interface AgentCostBreakdown {
  agent: string
  total_cost_usd: number
  total_tokens: number
  invocation_count: number
}

export interface AgentBreakdownResponse {
  agents: AgentCostBreakdown[]
  total_cost_usd: number
}

export interface RefreshResponse {
  records_updated: number
  message: string
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * Fetch cost summary for all workspaces.
 */
export function fetchWorkspaceSummaries(
  daysBack = 30
): Promise<WorkspaceSummariesResponse> {
  return apiGet(`/v1/admin/analytics/workspaces?days_back=${daysBack}`)
}

/**
 * Fetch detailed analytics for a single workspace.
 */
export function fetchWorkspaceDetail(
  workspaceId: string,
  daysBack = 30
): Promise<WorkspaceCostSummary> {
  return apiGet(
    `/v1/admin/analytics/workspaces/${workspaceId}?days_back=${daysBack}`
  )
}

/**
 * Fetch daily cost timeline.
 */
export function fetchTimeline(
  daysBack = 30,
  workspaceId?: string
): Promise<TimelineResponse> {
  const params = new URLSearchParams({ days_back: String(daysBack) })
  if (workspaceId) {
    params.set('workspace_id', workspaceId)
  }
  return apiGet(`/v1/admin/analytics/timeline?${params}`)
}

/**
 * Fetch cost breakdown by agent.
 */
export function fetchAgentBreakdown(
  daysBack = 30,
  workspaceId?: string
): Promise<AgentBreakdownResponse> {
  const params = new URLSearchParams({ days_back: String(daysBack) })
  if (workspaceId) {
    params.set('workspace_id', workspaceId)
  }
  return apiGet(`/v1/admin/analytics/agents?${params}`)
}

/**
 * Refresh daily cost rollups.
 */
export function refreshDailyCosts(
  daysBack = 30,
  workspaceId?: string
): Promise<RefreshResponse> {
  const params = new URLSearchParams({ days_back: String(daysBack) })
  if (workspaceId) {
    params.set('workspace_id', workspaceId)
  }
  return apiPost(`/v1/admin/analytics/refresh?${params}`)
}
