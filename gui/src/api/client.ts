import { getAccessToken, useAuthStore } from '../stores/authStore'

const API_BASE = '/api'

export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getAccessToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  })

  // Handle 401 - try refresh token
  if (response.status === 401 && token) {
    const refreshed = await useAuthStore.getState().refresh()
    if (refreshed) {
      // Retry with new token
      const newToken = getAccessToken()
      if (newToken) {
        headers['Authorization'] = `Bearer ${newToken}`
        const retryResponse = await fetch(`${API_BASE}${endpoint}`, {
          ...options,
          headers,
        })
        if (retryResponse.ok) {
          return retryResponse.json()
        }
      }
    }
    // Refresh failed, clear auth state
    useAuthStore.getState().clear()
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || `HTTP ${response.status}`)
  }

  return response.json()
}

export function apiGet<T>(endpoint: string): Promise<T> {
  return apiRequest<T>(endpoint)
}

export function apiPost<T>(endpoint: string, data?: unknown): Promise<T> {
  return apiRequest<T>(endpoint, {
    method: 'POST',
    body: data ? JSON.stringify(data) : undefined,
  })
}

export function apiPut<T>(endpoint: string, data: unknown): Promise<T> {
  return apiRequest<T>(endpoint, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export function apiDelete<T>(endpoint: string): Promise<T> {
  return apiRequest<T>(endpoint, {
    method: 'DELETE',
  })
}

export function apiPatch<T>(endpoint: string, data: unknown): Promise<T> {
  return apiRequest<T>(endpoint, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}
