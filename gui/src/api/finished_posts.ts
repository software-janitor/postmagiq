/**
 * API client for finished posts
 *
 * v1 workspace-scoped routes for multi-tenant finished posts.
 * Legacy routes are deprecated and will be removed.
 */

import { apiGet, apiPost, apiDelete } from './client'

// =============================================================================
// Types
// =============================================================================

export interface PublishInfo {
  platform: string
  published_at: string
  url: string | null
}

export interface FinishedPost {
  post_id: string
  post_number: number
  chapter: number
  title: string
  content: string
  image_prompt: string | null
  file_path: string
  publish_status: PublishInfo[]
}

export interface FinishedPostsResponse {
  posts: FinishedPost[]
}

// =============================================================================
// Legacy API (deprecated)
// =============================================================================

/**
 * @deprecated Use fetchFinishedPostsV1 instead
 */
export async function fetchFinishedPosts(): Promise<FinishedPost[]> {
  return apiGet<FinishedPost[]>('/finished-posts')
}

/**
 * @deprecated Use fetchFinishedPostV1 instead
 */
export async function fetchFinishedPost(postId: string): Promise<FinishedPost> {
  return apiGet<FinishedPost>(`/finished-posts/${postId}`)
}

/**
 * @deprecated Will be removed - publish endpoints removed for security
 */
export async function publishPost(
  postId: string,
  platform: string,
  url?: string
): Promise<{ success: boolean }> {
  return apiPost<{ success: boolean }>(`/finished-posts/${postId}/publish`, {
    platform,
    url,
  })
}

/**
 * @deprecated Will be removed - publish endpoints removed for security
 */
export async function unpublishPost(
  postId: string,
  platform: string
): Promise<{ success: boolean }> {
  return apiDelete(`/finished-posts/${postId}/publish/${platform}`)
}

// =============================================================================
// v1 Workspace-Scoped API (preferred)
// =============================================================================

/**
 * Get all finished posts for a workspace.
 */
export async function fetchFinishedPostsV1(
  workspaceId: string
): Promise<FinishedPostsResponse> {
  return apiGet<FinishedPostsResponse>(
    `/v1/w/${workspaceId}/finished-posts`
  )
}

/**
 * Get a specific finished post by ID.
 */
export async function fetchFinishedPostV1(
  workspaceId: string,
  postId: string
): Promise<FinishedPost> {
  return apiGet<FinishedPost>(
    `/v1/w/${workspaceId}/finished-posts/${postId}`
  )
}

/**
 * Get available platforms.
 */
export async function fetchPlatformsV1(
  workspaceId: string
): Promise<{ platforms: string[] }> {
  return apiGet<{ platforms: string[] }>(
    `/v1/w/${workspaceId}/finished-posts/platforms`
  )
}
