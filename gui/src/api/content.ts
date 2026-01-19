/**
 * API client for content strategy database
 */

import { apiGet, apiPost, apiPut } from './client'

// =============================================================================
// Types
// =============================================================================

export interface UserResponse {
  id: number
  name: string
  email: string | null
  has_goal: boolean
  has_voice_profile: boolean
  post_count: number
}

export interface GoalResponse {
  id: number
  positioning: string | null
  signature_thesis: string | null
  target_audience: string | null
  content_style: string | null
  onboarding_mode: string | null
}

export interface ChapterResponse {
  id: number
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

export interface PostResponse {
  id: number
  post_number: number
  chapter_id: number
  chapter_number: number
  chapter_title: string
  topic: string | null
  shape: string | null
  cadence: string | null
  entry_point: string | null
  status: string
  guidance: string | null
  published_url: string | null
}

export interface VoiceProfileResponse {
  id: number
  tone: string | null
  sentence_patterns: string | null
  vocabulary_level: string | null
  signature_phrases: string | null
  storytelling_style: string | null
  emotional_register: string | null
}

export interface ContentStyle {
  id: string
  name: string
  description: string
  chapter_framing: string
}

export interface PostShape {
  id: string
  name: string
  description: string
}

export interface VoicePrompt {
  id: string
  prompt: string
  reveals: string
}

// =============================================================================
// User API
// =============================================================================

export async function createUser(name: string, email?: string): Promise<{ id: number }> {
  return apiPost<{ id: number }>('/content/users', { name, email })
}

export async function fetchUser(userId: number): Promise<UserResponse> {
  return apiGet<UserResponse>(`/content/users/${userId}`)
}

export async function fetchUserByEmail(email: string): Promise<UserResponse> {
  return apiGet<UserResponse>(`/content/users/email/${email}`)
}

// =============================================================================
// Goal API
// =============================================================================

export async function fetchGoal(userId: number): Promise<GoalResponse> {
  return apiGet<GoalResponse>(`/content/users/${userId}/goal`)
}

export async function updateGoal(
  goalId: number,
  updates: Partial<GoalResponse>
): Promise<{ status: string }> {
  return apiPut<{ status: string }>(`/content/goals/${goalId}`, updates)
}

// =============================================================================
// Chapter API
// =============================================================================

export async function fetchChapters(userId: number): Promise<ChapterResponse[]> {
  return apiGet<ChapterResponse[]>(`/content/users/${userId}/chapters`)
}

export async function fetchChapter(chapterId: number): Promise<ChapterResponse> {
  return apiGet<ChapterResponse>(`/content/chapters/${chapterId}`)
}

// =============================================================================
// Post API
// =============================================================================

export async function fetchPosts(
  userId: number,
  options?: { chapterId?: number; status?: string }
): Promise<PostResponse[]> {
  let url = `/content/users/${userId}/posts`
  const params = new URLSearchParams()
  if (options?.chapterId) params.append('chapter_id', String(options.chapterId))
  if (options?.status) params.append('status', options.status)
  if (params.toString()) url += `?${params.toString()}`
  return apiGet<PostResponse[]>(url)
}

export async function fetchAvailableDbPosts(userId: number): Promise<PostResponse[]> {
  return apiGet<PostResponse[]>(`/content/users/${userId}/posts/available`)
}

export async function fetchNextDbPost(userId: number): Promise<PostResponse> {
  return apiGet<PostResponse>(`/content/users/${userId}/posts/next`)
}

export async function fetchDbPost(postId: number): Promise<PostResponse> {
  return apiGet<PostResponse>(`/content/posts/${postId}`)
}

export async function updatePost(
  postId: number,
  updates: Partial<PostResponse>
): Promise<{ status: string }> {
  return apiPut<{ status: string }>(`/content/posts/${postId}`, updates)
}

// =============================================================================
// Voice Profile API
// =============================================================================

export async function fetchVoiceProfile(userId: number): Promise<VoiceProfileResponse> {
  return apiGet<VoiceProfileResponse>(`/content/users/${userId}/voice-profile`)
}

// =============================================================================
// Constants API
// =============================================================================

export async function fetchVoicePrompts(): Promise<{ prompts: VoicePrompt[] }> {
  return apiGet<{ prompts: VoicePrompt[] }>('/content/prompts')
}

export async function fetchContentStyles(): Promise<{ styles: ContentStyle[] }> {
  return apiGet<{ styles: ContentStyle[] }>('/content/styles')
}

export async function fetchPostShapes(): Promise<{ shapes: PostShape[] }> {
  return apiGet<{ shapes: PostShape[] }>('/content/shapes')
}
