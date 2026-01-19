import { apiGet, apiPost, apiPut, apiDelete } from './client'

export interface Platform {
  id: number
  user_id: number
  name: string
  description: string | null
  post_format: string | null
  default_word_count: number | null
  uses_enemies: boolean
  is_active: boolean
  created_at: string | null
}

export interface CreatePlatformRequest {
  user_id: number
  name: string
  description?: string
  post_format?: string
  default_word_count?: number
  uses_enemies?: boolean
}

export interface UpdatePlatformRequest {
  name?: string
  description?: string
  post_format?: string
  default_word_count?: number
  uses_enemies?: boolean
  is_active?: boolean
}

export async function fetchPlatforms(userId: number): Promise<Platform[]> {
  return apiGet<Platform[]>(`/platforms/user/${userId}`)
}

export async function fetchPlatform(platformId: number): Promise<Platform> {
  return apiGet<Platform>(`/platforms/${platformId}`)
}

export async function createPlatform(data: CreatePlatformRequest): Promise<{ id: number }> {
  return apiPost<{ id: number }>('/platforms', data)
}

export async function updatePlatform(platformId: number, data: UpdatePlatformRequest): Promise<void> {
  await apiPut(`/platforms/${platformId}`, data)
}

export async function deletePlatform(platformId: number): Promise<void> {
  await apiDelete(`/platforms/${platformId}`)
}
