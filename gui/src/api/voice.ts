/**
 * API client for voice learning
 *
 * Workspace-scoped routes for multi-tenant voice features.
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
  id: string
  source_type: 'prompt' | 'upload'
  prompt_id: string | null
  prompt_text: string | null
  title: string | null
  content: string
  word_count: number
  created_at: string | null
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

export interface SaveSampleRequest {
  source_type: 'prompt' | 'upload'
  content: string
  prompt_id?: string
  prompt_text?: string
  title?: string
}

export interface AnalysisResult {
  profile_id: string
  analysis: {
    tone: string
    sentence_patterns: Record<string, unknown>
    vocabulary_level: string
    punctuation_style?: {
      em_dashes: string
      semicolons: string
      exclamations: string
      ellipses: string
      parentheticals: string
    }
    transition_style?: string
    paragraph_rhythm?: {
      length: string
      opening_style: string
    }
    reader_address?: {
      point_of_view: string
      relationship: string
    }
    signature_phrases: string[]
    storytelling_style: string
    emotional_register: string
    summary: string
  }
}

export interface VoiceProfile {
  id: string
  workspace_id: string | null
  name: string
  slug: string
  description: string | null
  is_preset: boolean
  tone_description: string | null
  signature_phrases: string | null
  word_choices: string | null
  example_excerpts: string | null
  avoid_patterns: string | null
}

// =============================================================================
// Prompts
// =============================================================================

/**
 * Get voice prompts for workspace.
 */
export async function fetchVoicePrompts(workspaceId: string): Promise<{ prompts: VoicePrompt[] }> {
  return apiGet<{ prompts: VoicePrompt[] }>(`/v1/w/${workspaceId}/voice/prompts`)
}

// =============================================================================
// Samples
// =============================================================================

/**
 * Save a writing sample for a workspace.
 */
export async function saveSample(
  workspaceId: string,
  request: SaveSampleRequest
): Promise<{ id: string; word_count: number }> {
  return apiPost<{ id: string; word_count: number }>(
    `/v1/w/${workspaceId}/voice/samples`,
    request
  )
}

/**
 * Get all writing samples for a workspace.
 */
export async function fetchSamples(workspaceId: string): Promise<SamplesResponse> {
  return apiGet<SamplesResponse>(`/v1/w/${workspaceId}/voice/samples`)
}

/**
 * Get sample status for a workspace.
 */
export async function fetchSampleStatus(workspaceId: string): Promise<SampleStatus> {
  return apiGet<SampleStatus>(`/v1/w/${workspaceId}/voice/samples/status`)
}

// =============================================================================
// Analysis
// =============================================================================

/**
 * Analyze voice and create profile for a workspace.
 */
export async function analyzeVoice(workspaceId: string): Promise<AnalysisResult> {
  return apiPost<AnalysisResult>(`/v1/w/${workspaceId}/voice/analyze`, {})
}

// =============================================================================
// Profiles
// =============================================================================

/**
 * Get all voice profiles for a workspace (includes library presets).
 */
export async function fetchVoiceProfiles(workspaceId: string): Promise<VoiceProfile[]> {
  return apiGet<VoiceProfile[]>(`/v1/w/${workspaceId}/voice-profiles`)
}

/**
 * Get the workspace's own voice profile (not system presets).
 * Returns null if no custom profile exists.
 */
export async function fetchWorkspaceVoiceProfile(workspaceId: string): Promise<VoiceProfile | null> {
  const profiles = await fetchVoiceProfiles(workspaceId)
  // Find first profile that belongs to this workspace (not a system preset)
  return profiles.find(p => p.workspace_id === workspaceId && !p.is_preset) ?? null
}
