/**
 * API client for onboarding flow
 *
 * v1 workspace-scoped routes for multi-tenant strategy builder.
 * Legacy user-scoped routes are deprecated and will be removed.
 */

import { apiDelete, apiGet, apiPost } from './client'
import { getCurrentWorkspaceId } from '../stores/workspaceStore'

// =============================================================================
// Types
// =============================================================================

export interface OnboardingQuestion {
  id: string
  question: string
  placeholder?: string
  type: 'text' | 'select'
  options?: Array<{
    id: string
    name: string
    description: string
  }>
}

export interface StartResponse {
  user_id: string
  questions: OnboardingQuestion[]
}

export interface GeneratedPost {
  post_number: number
  topic: string
  shape: string
  cadence: string
}

export interface GeneratedChapter {
  chapter_number: number
  title: string
  theme: string
  theme_description: string
  posts: GeneratedPost[]
}

export interface GeneratedPlan {
  signature_thesis: string
  chapters: GeneratedChapter[]
}

export interface QuickModeResponse {
  plan: GeneratedPlan
}

export interface DeepModeMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface DeepModeState {
  messages: DeepModeMessage[]
  turn_count: number
  ready_to_generate: boolean
}

export interface DeepModeResponse {
  assistant_message: string
  state: DeepModeState
  ready_to_generate: boolean
}

export interface ApproveResponse {
  goal_id: string
  chapter_count: number
  post_count: number
}

// =============================================================================
// Start Onboarding
// =============================================================================

export async function startOnboarding(
  name: string,
  email?: string
): Promise<StartResponse> {
  return apiPost<StartResponse>('/onboarding/start', { name, email })
}

export async function fetchQuickQuestions(): Promise<{ questions: OnboardingQuestion[] }> {
  return apiGet<{ questions: OnboardingQuestion[] }>('/onboarding/questions')
}

// =============================================================================
// Quick Mode
// =============================================================================

export interface QuickModeAnswers {
  user_id: string
  professional_role: string
  known_for: string
  target_audience: string
  content_style: string
  posts_per_week: number
}

export async function submitQuickMode(
  answers: QuickModeAnswers
): Promise<QuickModeResponse> {
  return apiPost<QuickModeResponse>('/onboarding/quick', answers)
}

// =============================================================================
// Deep Mode
// =============================================================================

export async function startDeepDiscovery(): Promise<DeepModeResponse> {
  return apiPost<DeepModeResponse>('/onboarding/deep/start')
}

export async function sendDeepMessage(
  userId: string,
  message: string,
  state: DeepModeState,
  forceReady?: boolean
): Promise<DeepModeResponse> {
  return apiPost<DeepModeResponse>('/onboarding/deep/message', {
    user_id: userId,
    message,
    state,
    force_ready: Boolean(forceReady),
  })
}

export async function generateFromDeep(
  userId: string,
  contentStyle: string,
  state: DeepModeState
): Promise<QuickModeResponse> {
  return apiPost<QuickModeResponse>('/onboarding/deep/generate', {
    user_id: userId,
    content_style: contentStyle,
    state,
  })
}

// =============================================================================
// Plan Approval
// =============================================================================

export interface ApprovePlanRequest {
  user_id: string
  plan: GeneratedPlan
  positioning: string
  target_audience: string
  content_style: string
  onboarding_mode: 'quick' | 'deep' | 'chat'
  transcript?: string
  workspace_id?: string | null
}

export async function approvePlan(
  request: ApprovePlanRequest
): Promise<ApproveResponse> {
  return apiPost<ApproveResponse>('/onboarding/approve', request)
}

// =============================================================================
// Existing Strategy
// =============================================================================

export interface ExistingChapter {
  id: string
  chapter_number: number
  title: string
  description: string | null
  theme: string | null
  theme_description: string | null
  weeks_start: number | null
  weeks_end: number | null
  post_count: number
  completed_count: number
}

export interface ExistingGoal {
  id: string
  workspace_id: string
  strategy_type: 'series' | 'daily' | 'campaign'
  positioning: string | null
  signature_thesis: string | null
  target_audience: string | null
  content_style: string | null
  voice_profile_id: string | null
  image_config_set_id: string | null
}

export interface StrategySummary {
  total_chapters: number
  total_posts: number
  completed_posts: number
  weeks_total: number
}

export interface ExistingStrategy {
  exists: boolean
  goal?: ExistingGoal
  chapters?: ExistingChapter[]
  summary?: StrategySummary
}

export async function fetchExistingStrategy(): Promise<ExistingStrategy> {
  const workspaceId = getCurrentWorkspaceId()
  if (!workspaceId) {
    return { exists: false }
  }

  try {
    // Fetch goals and chapters from workspace-scoped endpoints
    const [goals, chapters] = await Promise.all([
      apiGet<ExistingGoal[]>(`/v1/w/${workspaceId}/goals`),
      apiGet<ExistingChapter[]>(`/v1/w/${workspaceId}/chapters`),
    ])

    if (!goals.length) {
      return { exists: false }
    }

    // Use the first goal as the primary strategy
    const goal = goals[0]

    // Calculate summary
    const totalPosts = chapters.reduce((sum, ch) => sum + ch.post_count, 0)
    const completedPosts = chapters.reduce((sum, ch) => sum + ch.completed_count, 0)
    const weeksTotal = chapters.reduce((max, ch) => Math.max(max, ch.weeks_end || 0), 0)

    return {
      exists: true,
      goal,
      chapters,
      summary: {
        total_chapters: chapters.length,
        total_posts: totalPosts,
        completed_posts: completedPosts,
        weeks_total: weeksTotal,
      },
    }
  } catch {
    return { exists: false }
  }
}

// =============================================================================
// v1 Workspace-Scoped API (preferred)
// =============================================================================

export interface V1ContentStyle {
  id: string
  name: string
  description: string
}

export interface V1QuickModeRequest {
  professional_role: string
  known_for: string
  target_audience: string
  content_style: string
  posts_per_week: number
}

export interface V1DeepModeMessageRequest {
  message: string
  state?: DeepModeState | null
  force_ready?: boolean
}

export interface V1DeepModeResponse {
  message: string
  state: DeepModeState
  is_ready: boolean
}

export interface V1GeneratePlanRequest {
  content_style: string
  state: DeepModeState
}

export interface V1ApprovePlanRequest {
  plan: GeneratedPlan
  positioning: string
  target_audience: string
  content_style: string
  onboarding_mode: 'quick' | 'deep' | 'chat'
  transcript?: string | null
}

export interface V1ApproveResponse {
  goal_id: string
  chapters: string[]
}

export interface V1StrategyResponse {
  goal: ExistingGoal | null
  chapters: ExistingChapter[]
}

/**
 * Get available content styles (workspace-scoped).
 */
export async function fetchContentStylesV1(
  workspaceId: string
): Promise<{ styles: V1ContentStyle[] }> {
  return apiGet<{ styles: V1ContentStyle[] }>(
    `/v1/w/${workspaceId}/onboarding/content-styles`
  )
}

/**
 * Submit quick mode onboarding (workspace-scoped).
 */
export async function submitQuickModeV1(
  workspaceId: string,
  request: V1QuickModeRequest
): Promise<QuickModeResponse> {
  return apiPost<QuickModeResponse>(
    `/v1/w/${workspaceId}/onboarding/quick`,
    request
  )
}

/**
 * Send deep mode message (workspace-scoped).
 */
export async function sendDeepMessageV1(
  workspaceId: string,
  request: V1DeepModeMessageRequest
): Promise<V1DeepModeResponse> {
  return apiPost<V1DeepModeResponse>(
    `/v1/w/${workspaceId}/onboarding/deep/message`,
    request
  )
}

/**
 * Generate plan from deep mode (workspace-scoped).
 */
export async function generateFromDeepV1(
  workspaceId: string,
  request: V1GeneratePlanRequest
): Promise<QuickModeResponse> {
  return apiPost<QuickModeResponse>(
    `/v1/w/${workspaceId}/onboarding/deep/generate-plan`,
    request
  )
}

/**
 * Approve and save generated plan (workspace-scoped).
 */
export async function approvePlanV1(
  workspaceId: string,
  request: V1ApprovePlanRequest
): Promise<V1ApproveResponse> {
  return apiPost<V1ApproveResponse>(
    `/v1/w/${workspaceId}/onboarding/approve`,
    request
  )
}

/**
 * Get current strategy for workspace.
 */
export async function fetchStrategyV1(
  workspaceId: string
): Promise<V1StrategyResponse> {
  return apiGet<V1StrategyResponse>(
    `/v1/w/${workspaceId}/onboarding/strategy`
  )
}

/**
 * Delete current strategy for workspace.
 */
export async function deleteStrategyV1(workspaceId: string): Promise<void> {
  return apiDelete(`/v1/w/${workspaceId}/onboarding/strategy`)
}
