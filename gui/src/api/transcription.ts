/**
 * API client for transcription endpoints.
 */

import { getAccessToken, useAuthStore } from '../stores/authStore'
import { apiGet } from './client'

const API_BASE = '/api'

export interface CreditsInfo {
  used: number
  limit: number
  remaining: number
}

export interface FeaturesInfo {
  premium_workflow: boolean
  voice_transcription: boolean
  youtube_transcription: boolean
  priority_support: boolean
  api_access: boolean
  team_workspaces: boolean
  text_limit: number
}

export interface TierInfo {
  name: string
  slug: string
}

export interface UsageSummary {
  period_start: string
  period_end: string
  credits: CreditsInfo
  features: FeaturesInfo
  tier: TierInfo
  // Legacy fields
  posts: {
    used: number
    limit: number
    overage: number
    unlimited: boolean
  }
  storage: {
    used_bytes: number
    limit_bytes: number
    used_gb: number
    limit_gb: number
    unlimited: boolean
  }
  api_calls: {
    used: number
    limit: number
    unlimited: boolean
  }
  subscription: {
    tier_name: string
    tier_slug: string
    status: string
    overage_enabled: boolean
  }
}

/**
 * Get workspace usage summary including tier info.
 */
export async function getUsageSummary(workspaceId: string): Promise<UsageSummary> {
  return apiGet<UsageSummary>(`/v1/w/${workspaceId}/usage`)
}

/**
 * Check if workspace has premium tier (voice/youtube transcription enabled).
 * Updated for new tier structure: starter, pro, business are premium.
 */
export function isPremiumTier(tierSlug: string): boolean {
  const premiumTiers = ['starter', 'pro', 'business', 'individual', 'team', 'agency']
  return premiumTiers.includes(tierSlug)
}

/**
 * Check if a specific feature is enabled based on usage summary.
 */
export function hasFeature(usage: UsageSummary, feature: keyof FeaturesInfo): boolean {
  if (feature === 'text_limit') {
    return true // text_limit is always a number, not a boolean
  }
  return usage.features?.[feature] ?? false
}

export interface CreditEstimate {
  text_length: number
  estimated_credits: number
  credits_remaining: number
  can_proceed: boolean
}

/**
 * Estimate credits needed for a workflow run.
 */
export async function estimateCredits(
  workspaceId: string,
  textLength: number
): Promise<CreditEstimate> {
  const token = getAccessToken()

  const response = await fetch(
    `${API_BASE}/v1/w/${workspaceId}/usage/estimate`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ text_length: textLength }),
    }
  )

  if (!response.ok) {
    throw new Error('Failed to estimate credits')
  }

  return response.json()
}

export interface TranscriptionResult {
  text: string
  language: string | null
  duration_seconds: number
  tokens_used: number
  source_type: 'upload' | 'youtube'
  source_info: Record<string, unknown>
}

/**
 * Transcribe an uploaded audio file.
 */
export async function transcribeAudio(
  workspaceId: string,
  file: File,
  language?: string
): Promise<TranscriptionResult> {
  const token = getAccessToken()

  const formData = new FormData()
  formData.append('audio', file)
  if (language) {
    formData.append('language', language)
  }

  const response = await fetch(
    `${API_BASE}/v1/w/${workspaceId}/transcribe/upload`,
    {
      method: 'POST',
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: formData,
    }
  )

  // Handle 401 - try refresh token
  if (response.status === 401 && token) {
    const refreshed = await useAuthStore.getState().refresh()
    if (refreshed) {
      const newToken = getAccessToken()
      const retryResponse = await fetch(
        `${API_BASE}/v1/w/${workspaceId}/transcribe/upload`,
        {
          method: 'POST',
          headers: {
            ...(newToken ? { Authorization: `Bearer ${newToken}` } : {}),
          },
          body: formData,
        }
      )
      if (retryResponse.ok) {
        return retryResponse.json()
      }
    }
    useAuthStore.getState().clear()
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || `Transcription failed: HTTP ${response.status}`)
  }

  return response.json()
}

/**
 * Transcribe audio from a YouTube video.
 */
export async function transcribeYouTube(
  workspaceId: string,
  url: string,
  language?: string
): Promise<TranscriptionResult> {
  const token = getAccessToken()

  const response = await fetch(
    `${API_BASE}/v1/w/${workspaceId}/transcribe/youtube`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ url, language }),
    }
  )

  // Handle 401 - try refresh token
  if (response.status === 401 && token) {
    const refreshed = await useAuthStore.getState().refresh()
    if (refreshed) {
      const newToken = getAccessToken()
      const retryResponse = await fetch(
        `${API_BASE}/v1/w/${workspaceId}/transcribe/youtube`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(newToken ? { Authorization: `Bearer ${newToken}` } : {}),
          },
          body: JSON.stringify({ url, language }),
        }
      )
      if (retryResponse.ok) {
        return retryResponse.json()
      }
    }
    useAuthStore.getState().clear()
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || `YouTube transcription failed: HTTP ${response.status}`)
  }

  return response.json()
}
