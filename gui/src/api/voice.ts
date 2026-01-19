/**
 * API client for voice learning
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
