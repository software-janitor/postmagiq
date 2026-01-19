/**
 * API client for onboarding flow
 */

import { apiGet, apiPost } from './client'
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
