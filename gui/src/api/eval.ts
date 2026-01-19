/**
 * Evaluation API consumers
 */

import { apiGet } from './client'

// ============================================================================
// Types
// ============================================================================

export interface AgentPerformance {
  name: string
  avg_score: number
  avg_hook: number | null
  avg_specifics: number | null
  avg_voice: number | null
  sample_size: number
}

export interface AgentComparison {
  period_days: number
  agents: AgentPerformance[]
}

export interface CostAgent {
  name: string
  invocations: number
  total_tokens: number
  total_cost: number
  avg_cost: number
  percentage: number
}

export interface CostBreakdown {
  total_cost_usd: number
  agents: CostAgent[]
}

export interface TrendWeek {
  week: string
  runs: number
  avg_quality: number | null
  total_cost: number
}

export interface QualityTrend {
  weeks: TrendWeek[]
}

export interface TrendDay {
  day: string
  runs: number
  avg_score: number | null
  total_cost: number
}

export interface DailyTrend {
  period_days: number
  days: TrendDay[]
}

export interface PostIteration {
  iteration: number
  run_id: string
  final_score: number | null
  total_cost: number
  improvements: string | null
}

export interface PostIterations {
  story: string
  iterations: PostIteration[]
}

export interface BestAgentResult {
  name: string
  avg_score: number
  sample_size: number
}

export interface BestAgentForTask {
  state: string
  agents: BestAgentResult[]
}

export interface SummaryStats {
  total_runs: number
  completed_runs: number
  success_rate: number
  total_cost_usd: number
  total_tokens: number
  avg_final_score: number | null
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * Fetch agent performance comparison over last N days.
 */
export function fetchAgentComparison(days = 30): Promise<AgentComparison> {
  return apiGet(`/eval/agents?days=${days}`)
}

/**
 * Fetch cost breakdown by agent.
 */
export function fetchCostBreakdown(): Promise<CostBreakdown> {
  return apiGet('/eval/costs')
}

/**
 * Fetch weekly quality trend.
 */
export function fetchQualityTrend(weeks = 8): Promise<QualityTrend> {
  return apiGet(`/eval/trend?weeks=${weeks}`)
}

/**
 * Fetch daily quality trend.
 */
export function fetchDailyTrend(days = 30): Promise<DailyTrend> {
  return apiGet(`/eval/daily?days=${days}`)
}

/**
 * Fetch iteration history for a specific post.
 */
export function fetchPostIterations(story: string): Promise<PostIterations> {
  return apiGet(`/eval/post/${encodeURIComponent(story)}`)
}

/**
 * Fetch best performing agent for a given task/state.
 */
export function fetchBestAgentForTask(state: string): Promise<BestAgentForTask> {
  return apiGet(`/eval/best/${encodeURIComponent(state)}`)
}

/**
 * Fetch high-level summary statistics.
 */
export function fetchSummaryStats(): Promise<SummaryStats> {
  return apiGet('/eval/summary')
}
