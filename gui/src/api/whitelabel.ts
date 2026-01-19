/**
 * API client for white-labeling/theme customization
 */

import { apiGet, apiPut, apiRequest } from './client'
import { getAccessToken } from '../stores/authStore'

// =============================================================================
// Types
// =============================================================================

export interface WhitelabelConfig {
  id: string
  workspace_id: string
  company_name: string | null
  logo_url: string | null
  favicon_url: string | null
  primary_color: string | null
  secondary_color: string | null
  accent_color: string | null
  portal_welcome_text: string | null
  portal_footer_text: string | null
  support_email: string | null
  created_at: string
  updated_at: string
}

export interface WhitelabelConfigUpdate {
  company_name?: string | null
  primary_color?: string | null
  secondary_color?: string | null
  accent_color?: string | null
  portal_welcome_text?: string | null
  portal_footer_text?: string | null
  support_email?: string | null
}

export interface AssetUploadResponse {
  url: string
  asset_type: 'logo' | 'favicon'
}

// =============================================================================
// API Functions
// =============================================================================

/**
 * Get the current whitelabel config for a workspace
 */
export async function getWhitelabelConfig(workspaceId: string): Promise<WhitelabelConfig> {
  return apiGet<WhitelabelConfig>(`/v1/w/${workspaceId}/whitelabel`)
}

/**
 * Update the whitelabel config for a workspace
 */
export async function updateWhitelabelConfig(
  workspaceId: string,
  config: WhitelabelConfigUpdate
): Promise<WhitelabelConfig> {
  return apiPut<WhitelabelConfig>(`/v1/w/${workspaceId}/whitelabel`, config)
}

/**
 * Upload a logo or favicon asset
 * Uses multipart/form-data for file upload
 */
export async function uploadAsset(
  workspaceId: string,
  type: 'logo' | 'favicon',
  file: File
): Promise<AssetUploadResponse> {
  const token = getAccessToken()
  const formData = new FormData()
  formData.append('file', file)
  formData.append('asset_type', type)

  const response = await fetch(`/api/v1/w/${workspaceId}/whitelabel/assets`, {
    method: 'POST',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: formData,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || `HTTP ${response.status}`)
  }

  return response.json()
}

/**
 * Delete a logo or favicon asset
 */
export async function deleteAsset(
  workspaceId: string,
  type: 'logo' | 'favicon'
): Promise<void> {
  await apiRequest<void>(`/v1/w/${workspaceId}/whitelabel/assets/${type}`, {
    method: 'DELETE',
  })
}
