/**
 * API client for voice learning
 *
 * v1 workspace-scoped routes for multi-tenant voice features.
 * Legacy user-scoped routes are deprecated and will be removed.
 */

import { apiGet, apiPost } from './client'

// =============================================================================
// Types
// =============================================================================

export interface VoicePrompt {
  id: string
  prompt: string
  reveals: string
}

export interface WritingSample {
  id: number
  source_type: 'prompt' | 'upload'
  prompt_id: string | null
  prompt_text: string | null
  title: string | null
  content: string
  word_count: number
  created_at: string
}

export interface SamplesResponse {
  samples: WritingSample[]
  total_word_count: number
  can_analyze: boolean
}

export interface SampleStatus {
  sample_count: number
  total_word_count: number
  min_words_required: number
  can_analyze: boolean
  words_needed: number
}

export interface VoiceAnalysis {
  profile_id: number
  tone: string
  sentence_patterns: {
    average_length?: string
    variation?: string
    common_structures?: string[]
  }
  vocabulary_level: string
  signature_phrases: string[]
  storytelling_style: string
  emotional_register: string
  summary: string
}

export interface VoiceProfile {
  id: number
  tone: string | null
  sentence_patterns: {
    average_length?: string
    variation?: string
    common_structures?: string[]
  }
  vocabulary_level: string | null
  signature_phrases: string[]
  storytelling_style: string | null
  emotional_register: string | null
}

// =============================================================================
// Prompts
// =============================================================================

export async function fetchVoicePrompts(): Promise<{ prompts: VoicePrompt[] }> {
  return apiGet<{ prompts: VoicePrompt[] }>('/voice/prompts')
}

export async function fetchVoicePrompt(promptId: string): Promise<VoicePrompt> {
  return apiGet<VoicePrompt>(`/voice/prompts/${promptId}`)
}

// =============================================================================
// Samples
// =============================================================================

export interface SaveSampleRequest {
  user_id: number
  source_type: 'prompt' | 'upload'
  content: string
  prompt_id?: string
  title?: string
}

export async function saveSample(
  request: SaveSampleRequest
): Promise<{ id: number; word_count: number }> {
  return apiPost<{ id: number; word_count: number }>('/voice/samples', request)
}

export async function fetchSamples(userId: number): Promise<SamplesResponse> {
  return apiGet<SamplesResponse>(`/voice/users/${userId}/samples`)
}

export async function fetchSampleStatus(userId: number): Promise<SampleStatus> {
  return apiGet<SampleStatus>(`/voice/users/${userId}/samples/status`)
}

// =============================================================================
// Analysis
// =============================================================================

export async function analyzeVoice(userId: number): Promise<VoiceAnalysis> {
  return apiPost<VoiceAnalysis>('/voice/analyze', { user_id: userId })
}

// =============================================================================
// Profile
// =============================================================================

export async function fetchVoiceUserProfile(userId: number): Promise<VoiceProfile> {
  return apiGet<VoiceProfile>(`/voice/users/${userId}/profile`)
}

// =============================================================================
// v1 Workspace-Scoped API (preferred)
// =============================================================================

export interface V1WritingSample {
  id: string
  source_type: 'prompt' | 'upload'
  prompt_id: string | null
  prompt_text: string | null
  title: string | null
  content: string
  word_count: number
  created_at: string | null
}

export interface V1SamplesResponse {
  samples: V1WritingSample[]
  total_word_count: number
  can_analyze: boolean
}

export interface V1SaveSampleRequest {
  source_type: 'prompt' | 'upload'
  content: string
  prompt_id?: string
  prompt_text?: string
  title?: string
}

export interface V1AnalysisResult {
  profile_id: string
  analysis: {
    tone: string
    sentence_patterns: Record<string, unknown>
    vocabulary_level: string
    signature_phrases: string[]
    storytelling_style: string
    emotional_register: string
    summary: string
  }
}

/**
 * Get voice prompts (not workspace-scoped).
 */
export async function fetchVoicePromptsV1(): Promise<{ prompts: VoicePrompt[] }> {
  return apiGet<{ prompts: VoicePrompt[] }>('/v1/w/voice/prompts')
}

/**
 * Save a writing sample for a workspace.
 */
export async function saveSampleV1(
  workspaceId: string,
  request: V1SaveSampleRequest
): Promise<{ id: string; word_count: number }> {
  return apiPost<{ id: string; word_count: number }>(
    `/v1/w/${workspaceId}/voice/samples`,
    request
  )
}

/**
 * Get all writing samples for a workspace.
 */
export async function fetchSamplesV1(workspaceId: string): Promise<V1SamplesResponse> {
  return apiGet<V1SamplesResponse>(`/v1/w/${workspaceId}/voice/samples`)
}

/**
 * Get sample status for a workspace.
 */
export async function fetchSampleStatusV1(workspaceId: string): Promise<SampleStatus> {
  return apiGet<SampleStatus>(`/v1/w/${workspaceId}/voice/samples/status`)
}

/**
 * Analyze voice and create profile for a workspace.
 */
export async function analyzeVoiceV1(workspaceId: string): Promise<V1AnalysisResult> {
  return apiPost<V1AnalysisResult>(`/v1/w/${workspaceId}/voice/analyze`, {})
}

/**
 * Get voice profile for a workspace.
 */
export async function fetchVoiceProfileV1(workspaceId: string): Promise<VoiceProfile | null> {
  return apiGet<VoiceProfile | null>(`/v1/w/${workspaceId}/voice/profile`)
}
