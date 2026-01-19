import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { useFlagsStore } from './flagsStore'

export type UserRole = 'owner' | 'admin' | 'user'

export interface User {
  id: string
  email: string
  full_name: string | null
  is_active: boolean
  is_superuser: boolean
  role: UserRole
}

// Helper to get display name
export function getUserDisplayName(user: User | null): string {
  return user?.full_name || user?.email || 'User'
}

export interface AuthTokens {
  access_token: string
  refresh_token: string
  token_type: string
}

interface AuthState {
  user: User | null
  tokens: AuthTokens | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
  viewAsUser: boolean  // Owner can toggle to view app as regular user

  // Actions
  setUser: (user: User | null) => void
  setTokens: (tokens: AuthTokens | null) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  toggleViewAsUser: () => void  // Toggle owner/user view mode
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, name?: string) => Promise<void>
  logout: () => Promise<void>
  refresh: () => Promise<boolean>
  fetchMe: () => Promise<void>
  clear: () => void
}

const API_BASE = '/api/v1'

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      tokens: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
      viewAsUser: false,

      setUser: (user) => set({ user, isAuthenticated: !!user }),
      setTokens: (tokens) => set({ tokens }),
      setLoading: (isLoading) => set({ isLoading }),
      setError: (error) => set({ error }),
      toggleViewAsUser: () => set((state) => ({ viewAsUser: !state.viewAsUser })),

      login: async (email, password) => {
        set({ isLoading: true, error: null })
        try {
          const response = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password }),
          })

          if (!response.ok) {
            const error = await response.json().catch(() => ({}))
            throw new Error(error.detail || 'Login failed')
          }

          const data = await response.json()
          set({
            tokens: {
              access_token: data.access_token,
              refresh_token: data.refresh_token,
              token_type: data.token_type,
            },
            isAuthenticated: true,
            isLoading: false,
          })
          // Fetch user profile after login
          await get().fetchMe()
        } catch (error) {
          set({
            isLoading: false,
            error: error instanceof Error ? error.message : 'Login failed',
          })
          throw error
        }
      },

      register: async (email, password, name) => {
        set({ isLoading: true, error: null })
        try {
          const response = await fetch(`${API_BASE}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password, full_name: name || 'User' }),
          })

          if (!response.ok) {
            const error = await response.json().catch(() => ({}))
            throw new Error(error.detail || 'Registration failed')
          }

          const data = await response.json()
          set({
            tokens: {
              access_token: data.access_token,
              refresh_token: data.refresh_token,
              token_type: data.token_type,
            },
            isAuthenticated: true,
            isLoading: false,
          })
          // Fetch user profile after registration
          await get().fetchMe()
        } catch (error) {
          set({
            isLoading: false,
            error: error instanceof Error ? error.message : 'Registration failed',
          })
          throw error
        }
      },

      logout: async () => {
        const { tokens } = get()
        try {
          if (tokens?.access_token) {
            await fetch(`${API_BASE}/auth/logout`, {
              method: 'POST',
              headers: {
                'Authorization': `Bearer ${tokens.access_token}`,
              },
            })
          }
        } finally {
          set({
            user: null,
            tokens: null,
            isAuthenticated: false,
            error: null,
            viewAsUser: false,
          })
          // Clear feature flags on logout
          useFlagsStore.getState().clearFlags()
        }
      },

      refresh: async () => {
        const { tokens } = get()
        if (!tokens?.refresh_token) return false

        try {
          const response = await fetch(`${API_BASE}/auth/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: tokens.refresh_token }),
          })

          if (!response.ok) {
            get().clear()
            return false
          }

          const data = await response.json()
          set({
            tokens: {
              access_token: data.access_token,
              refresh_token: data.refresh_token,
              token_type: data.token_type,
            },
          })
          return true
        } catch {
          get().clear()
          return false
        }
      },

      fetchMe: async () => {
        const { tokens } = get()
        if (!tokens?.access_token) return

        try {
          const response = await fetch(`${API_BASE}/auth/me`, {
            headers: {
              'Authorization': `Bearer ${tokens.access_token}`,
            },
          })

          if (!response.ok) {
            if (response.status === 401) {
              const refreshed = await get().refresh()
              if (refreshed) {
                return get().fetchMe()
              }
            }
            throw new Error('Failed to fetch user')
          }

          const user = await response.json()
          set({ user, isAuthenticated: true })
          // Fetch feature flags after user is loaded
          await useFlagsStore.getState().fetchFlags()
        } catch {
          get().clear()
        }
      },

      clear: () => set({
        user: null,
        tokens: null,
        isAuthenticated: false,
        error: null,
      }),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        tokens: state.tokens,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
        viewAsUser: state.viewAsUser,
      }),
    }
  )
)

// Helper to get access token for API requests
export function getAccessToken(): string | null {
  return useAuthStore.getState().tokens?.access_token ?? null
}
